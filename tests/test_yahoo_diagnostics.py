"""Synthetic status probes; live HTTP and DNS remain blocked by conftest."""

import logging
from collections.abc import Iterator
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from pydantic import SecretStr

from fantasy_gm.config.yahoo import YahooOAuthConfig
from fantasy_gm.providers.yahoo.diagnostics import (
    GAME_DIAGNOSTIC_URL,
    diagnose_fantasy_access,
)
from fantasy_gm.providers.yahoo.fantasy import LEAGUE_DISCOVERY_URL
from fantasy_gm.providers.yahoo.oauth import TOKEN_ENDPOINT, YahooOAuthClient
from fantasy_gm.providers.yahoo.pkce import s256_challenge
from fantasy_gm.providers.yahoo.session import (
    YahooAuthorizationSession,
    YahooAuthorizationSessionError,
)


class UnreadResponse(httpx.SyncByteStream):
    """Fail if the diagnostic attempts to consume any response content."""

    def __init__(self) -> None:
        self.closed = False

    def __iter__(self) -> Iterator[bytes]:
        raise AssertionError("Diagnostic must not read Yahoo response bodies")

    def close(self) -> None:
        self.closed = True


@pytest.mark.parametrize(
    "statuses,categories",
    [
        ((403, 403), ("forbidden", "forbidden")),
        ((200, 403), ("none", "forbidden")),
        ((200, 200), ("none", "none")),
        ((401, 200), ("unauthorized", "none")),
        ((302, 429), ("redirect", "rate_limited")),
        ((404, 500), ("not_found", "server_error")),
        ((400, 204), ("http_rejection", "none")),
    ],
)
def test_status_comparison_same_token_exact_requests_and_no_body_reads(
    statuses: tuple[int, int], categories: tuple[str, str]
) -> None:
    calls: list[httpx.Request] = []
    streams: list[UnreadResponse] = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        stream = UnreadResponse()
        streams.append(stream)
        return httpx.Response(
            statuses[len(calls) - 1],
            stream=stream,
            headers={"Location": "https://example.invalid/fake-sensitive-redirect"},
        )

    with httpx.Client(
        transport=httpx.MockTransport(handle),
        trust_env=False,
        auth=httpx.BasicAuth("fake-inherited-user", "fake-inherited-password"),
        headers={"Authorization": "fake-inherited-header"},
        follow_redirects=True,
    ) as client:
        results = diagnose_fantasy_access(
            SecretStr("fake-access-token"), http_client=client
        )
    assert [str(request.url) for request in calls] == [
        GAME_DIAGNOSTIC_URL,
        LEAGUE_DISCOVERY_URL,
    ]
    assert calls[1].url.raw_path == (
        b"/fantasy/v2/users;use_login=1/games;game_keys=nhl/leagues"
    )
    for request in calls:
        assert request.method == "GET"
        assert request.content == b""
        assert request.headers["Authorization"] == "Bearer fake-access-token"
        assert request.headers["Accept"] == "application/xml"
        assert request.headers["Cache-Control"] == "no-store"
        assert request.headers["Accept-Encoding"] == "identity"
        assert request.extensions["timeout"] == dict.fromkeys(
            ("connect", "read", "write", "pool"), 10.0
        )
    assert all(stream.closed for stream in streams)
    assert tuple(result.status_code for result in results) == statuses
    assert tuple(result.error_category for result in results) == categories
    for result in results:
        summary = result.summary()
        assert summary == (
            f"{result.endpoint} | HTTP {result.status_code} | "
            f"{'accepted' if 200 <= (result.status_code or 0) < 300 else 'rejected'}"
            f" | {result.error_category}"
        )
        assert "fake-" not in summary
        assert "https://" not in summary


@pytest.mark.parametrize("failed_index", [0, 1])
def test_transport_failure_is_sanitized_and_other_endpoint_still_tested(
    failed_index: int,
) -> None:
    calls: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if len(calls) - 1 == failed_index:
            raise httpx.ConnectError("fake-sensitive-header-and-token", request=request)
        return httpx.Response(200, stream=UnreadResponse())

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        results = diagnose_fantasy_access(
            SecretStr("fake-access-token"), http_client=client
        )
    assert len(calls) == 2
    assert results[failed_index].status_code is None
    assert results[failed_index].error_category == "transport_failure"
    assert "HTTP unavailable | rejected | transport_failure" in (
        results[failed_index].summary()
    )
    assert results[1 - failed_index].status_code == 200
    assert "fake-sensitive" not in repr(results)


def test_blank_token_never_reaches_http() -> None:
    with httpx.Client() as client:
        with pytest.raises(ValueError, match="An access token is required"):
            diagnose_fantasy_access(SecretStr(" "), http_client=client)


def test_logging_suppressed_and_restored(
    caplog: pytest.LogCaptureFixture,
) -> None:
    previous = logging.root.manager.disable

    def handle(request: httpx.Request) -> httpx.Response:
        assert logging.root.manager.disable == logging.CRITICAL
        logging.getLogger("fake-transport").critical("fake-sensitive-token")
        return httpx.Response(403, stream=UnreadResponse())

    with caplog.at_level(logging.DEBUG):
        with httpx.Client(transport=httpx.MockTransport(handle)) as client:
            results = diagnose_fantasy_access(
                SecretStr("fake-access-token"), http_client=client
            )
    assert logging.root.manager.disable == previous
    assert not caplog.records
    assert all(result.error_category == "forbidden" for result in results)


def test_unexpected_failure_restores_logging() -> None:
    previous = logging.root.manager.disable

    def handle(request: httpx.Request) -> httpx.Response:
        raise AssertionError("fake-synthetic-unexpected-error")

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(AssertionError, match="synthetic"):
            diagnose_fantasy_access(SecretStr("fake-access-token"), http_client=client)
    assert logging.root.manager.disable == previous


def test_one_simulated_pkce_authorization_then_both_probes() -> None:
    session = YahooAuthorizationSession()
    calls: list[httpx.Request] = []
    config = YahooOAuthConfig(client_id="fake-client-id-for-tests")
    parameters: dict[str, list[str]] = {}

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if len(calls) == 1:
            assert str(request.url) == TOKEN_ENDPOINT
            assert request.method == "POST"
            form = parse_qs(request.content.decode())
            assert form["client_id"] == [config.client_id]
            assert form["redirect_uri"] == [config.redirect_uri]
            assert form["code"] == ["fake-authorization-code"]
            assert (
                s256_challenge(SecretStr(form["code_verifier"][0]))
                == (parameters["code_challenge"][0])
            )
            return httpx.Response(
                200,
                json={
                    "access_token": "fake-newly-exchanged-access-token",
                    "refresh_token": "fake-refresh-token",
                    "token_type": "bearer",
                    "expires_in": 3600,
                },
            )
        assert request.headers["Authorization"] == (
            "Bearer fake-newly-exchanged-access-token"
        )
        return httpx.Response(403, stream=UnreadResponse())

    with httpx.Client(transport=httpx.MockTransport(handle), trust_env=False) as client:
        oauth = YahooOAuthClient(config, http_client=client)
        parameters = parse_qs(urlsplit(oauth.authorization_url(session)).query)
        tokens = oauth.exchange_code(
            SecretStr("fake-authorization-code"),
            session=session,
            returned_state=parameters["state"][0],
        )
        assert tokens.token_type == "bearer"
        results = diagnose_fantasy_access(tokens.access_token, http_client=client)
    assert len(calls) == 3
    assert [str(request.url) for request in calls[1:]] == [
        GAME_DIAGNOSTIC_URL,
        LEAGUE_DISCOVERY_URL,
    ]
    assert [result.summary() for result in results] == [
        "A: basic game | HTTP 403 | rejected | forbidden",
        "B: league discovery | HTTP 403 | rejected | forbidden",
    ]
    with pytest.raises(YahooAuthorizationSessionError, match="already used"):
        session.authorization_parameters()
