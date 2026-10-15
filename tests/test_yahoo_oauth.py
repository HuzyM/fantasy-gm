"""Public Client OAuth requests use synthetic tokens and MockTransport only."""

import asyncio
import gzip
import json
import logging
import traceback
from collections.abc import Iterator
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from pydantic import SecretStr

from fantasy_gm.config.yahoo import YahooOAuthConfig
from fantasy_gm.providers.yahoo.oauth import (
    AUTHORIZATION_ENDPOINT,
    MAX_TOKEN_RESPONSE_BYTES,
    TOKEN_ENDPOINT,
    MissingYahooRefreshTokenError,
    YahooOAuthClient,
    YahooOAuthError,
    YahooOAuthRequestError,
    YahooOAuthResponseError,
    YahooOAuthTokens,
)
from fantasy_gm.providers.yahoo.pkce import s256_challenge
from fantasy_gm.providers.yahoo.session import (
    YahooAuthorizationSession,
    YahooAuthorizationSessionError,
)

FAKE_ACCESS = "fake-access-token-for-tests"
FAKE_REFRESH = "fake-refresh-token-for-tests"


def payload() -> dict[str, object]:
    return {
        "access_token": FAKE_ACCESS,
        "refresh_token": FAKE_REFRESH,
        "expires_in": 3600,
        "token_type": "bearer",
        "xoauth_yahoo_guid": "fake-unused-guid",
    }


def previous_tokens() -> YahooOAuthTokens:
    return YahooOAuthTokens.model_validate(payload())


@pytest.fixture
def config() -> YahooOAuthConfig:
    return YahooOAuthConfig(client_id="fake-client-id-for-tests")


def exchange(oauth: YahooOAuthClient) -> YahooOAuthTokens:
    session = YahooAuthorizationSession()
    state = session.authorization_parameters()["state"]
    return oauth.exchange_code(
        SecretStr("fake-code+&-for-tests"), session=session, returned_state=state
    )


def test_authorization_url_has_pkce_and_no_scopes(config: YahooOAuthConfig) -> None:
    def no_request(request: httpx.Request) -> httpx.Response:
        pytest.fail("URL construction must not make HTTP requests")

    with httpx.Client(transport=httpx.MockTransport(no_request)) as client:
        session = YahooAuthorizationSession()
        url = YahooOAuthClient(config, http_client=client).authorization_url(session)
    parsed = urlsplit(url)
    assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == AUTHORIZATION_ENDPOINT
    query = parse_qs(parsed.query)
    assert query == {
        "client_id": [config.client_id],
        "redirect_uri": [config.redirect_uri],
        "response_type": ["code"],
        **{k: [v] for k, v in session.authorization_parameters().items()},
    }
    assert "scope" not in query and "client_secret" not in query
    assert "code_verifier" not in query


@pytest.mark.parametrize("grant", ["authorization_code", "refresh_token"])
def test_public_client_wire_format(config: YahooOAuthConfig, grant: str) -> None:
    session = YahooAuthorizationSession()
    state = session.authorization_parameters()["state"]
    calls: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        assert request.method == "POST" and str(request.url) == TOKEN_ENDPOINT
        assert "authorization" not in request.headers
        assert request.headers["accept-encoding"] == "identity"
        assert request.headers["content-type"] == "application/x-www-form-urlencoded"
        body = parse_qs(request.content.decode())
        assert body["client_id"] == [config.client_id]
        assert body["redirect_uri"] == [config.redirect_uri]
        assert body["grant_type"] == [grant]
        assert "client_secret" not in body
        if grant == "authorization_code":
            assert set(body) == {
                "client_id",
                "redirect_uri",
                "grant_type",
                "code",
                "code_verifier",
            }
            assert body["code"] == ["fake-code+&-for-tests"]
            assert (
                s256_challenge(SecretStr(body["code_verifier"][0]))
                == session._pkce.challenge
            )
        else:
            assert set(body) == {
                "client_id",
                "redirect_uri",
                "grant_type",
                "refresh_token",
            }
            assert body["refresh_token"] == [FAKE_REFRESH]
        return httpx.Response(200, json=payload())

    # Inherited Basic auth must never leak into a Public Client request.
    with httpx.Client(
        transport=httpx.MockTransport(handle),
        auth=("fake-id", "fake-obsolete-secret"),
        headers={"Authorization": "Basic fake-inherited-header-for-tests"},
    ) as client:
        oauth = YahooOAuthClient(config, http_client=client)
        tokens = (
            oauth.exchange_code(
                SecretStr("fake-code+&-for-tests"),
                session=session,
                returned_state=state,
            )
            if grant == "authorization_code"
            else oauth.refresh_tokens(previous_tokens())
        )
    assert len(calls) == 1
    assert tokens.access_token.get_secret_value() == FAKE_ACCESS
    assert tokens.refresh_token is not None
    assert tokens.refresh_token.get_secret_value() == FAKE_REFRESH
    assert tokens.expires_in == 3600 and tokens.token_type == "bearer"
    assert not hasattr(tokens, "xoauth_yahoo_guid")
    for secret in (FAKE_ACCESS, FAKE_REFRESH):
        assert secret not in repr(tokens) and secret not in tokens.model_dump_json()


@pytest.mark.parametrize("value", [None, "fake-rotated-refresh-token-for-tests"])
def test_refresh_retains_old_or_rotates(
    config: YahooOAuthConfig, value: str | None
) -> None:
    response = payload()
    if value is None:
        del response["refresh_token"]
    else:
        response["refresh_token"] = value
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=response)
        )
    ) as client:
        result = YahooOAuthClient(config, http_client=client).refresh_tokens(
            previous_tokens()
        )
    assert result.refresh_token is not None
    assert result.refresh_token.get_secret_value() == (value or FAKE_REFRESH)


@pytest.mark.parametrize(
    "response",
    [
        {},
        {"access_token": FAKE_ACCESS},
        {**payload(), "access_token": " "},
        {**payload(), "refresh_token": ""},
        {**payload(), "expires_in": 0},
        {**payload(), "expires_in": True},
        {**payload(), "expires_in": "3600"},
        {**payload(), "token_type": " "},
        {**payload(), "access_token": 123},
        {**payload(), "access_token": FAKE_ACCESS + "\u2603"},
        {**payload(), "access_token": FAKE_ACCESS + "\r\n"},
        {**payload(), "access_token": FAKE_ACCESS + "\x00"},
        {**payload(), "access_token": FAKE_ACCESS + "\x7f"},
        {**payload(), "access_token": FAKE_ACCESS + " invalid"},
    ],
)
def test_malformed_token_response(
    config: YahooOAuthConfig, response: dict[str, object]
) -> None:
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=response)
        )
    ) as client:
        with pytest.raises(YahooOAuthResponseError) as error:
            exchange(YahooOAuthClient(config, http_client=client))
    rendered = "".join(traceback.format_exception(error.value))
    assert FAKE_ACCESS not in rendered and FAKE_REFRESH not in rendered


def test_invalid_json(config: YahooOAuthConfig) -> None:
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, text="fake-invalid-json")
        )
    ) as client:
        with pytest.raises(YahooOAuthResponseError):
            exchange(YahooOAuthClient(config, http_client=client))


class TokenStream(httpx.SyncByteStream):
    def __init__(self, chunks: list[bytes]) -> None:
        self.chunks = chunks
        self.read_count = 0
        self.closed = False

    def __iter__(self) -> Iterator[bytes]:
        for chunk in self.chunks:
            self.read_count += 1
            yield chunk

    def close(self) -> None:
        self.closed = True


@pytest.mark.parametrize("status", [200, 400])
@pytest.mark.parametrize("headers", [{}, {"Content-Length": "1"}])
def test_token_stream_limit_stops_reading_and_closes(
    config: YahooOAuthConfig, status: int, headers: dict[str, str]
) -> None:
    stream = TokenStream(
        [
            b"fake-sensitive-" + b"x" * (MAX_TOKEN_RESPONSE_BYTES // 2),
            b"x" * (MAX_TOKEN_RESPONSE_BYTES // 2),
            b"fake-never-read",
        ]
    )
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(status, headers=headers, stream=stream)
        )
    ) as client:
        with pytest.raises(YahooOAuthResponseError, match="size limit") as error:
            exchange(YahooOAuthClient(config, http_client=client))
    assert stream.read_count == 2 and stream.closed
    assert "fake-sensitive" not in "".join(traceback.format_exception(error.value))


def test_token_stream_accepts_exact_limit_and_closes(config: YahooOAuthConfig) -> None:
    content = json.dumps(payload()).encode()
    content += b" " * (MAX_TOKEN_RESPONSE_BYTES - len(content))
    stream = TokenStream([content[:1024], content[1024:]])
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, stream=stream)
        )
    ) as client:
        tokens = exchange(YahooOAuthClient(config, http_client=client))
    assert tokens.access_token.get_secret_value() == FAKE_ACCESS
    assert stream.read_count == 2 and stream.closed


@pytest.mark.parametrize("status", [200, 400])
def test_compressed_token_stream_is_closed_without_reading(
    config: YahooOAuthConfig, status: int
) -> None:
    compressed = gzip.compress(b"fake-sensitive-" * MAX_TOKEN_RESPONSE_BYTES)
    stream = TokenStream([compressed])
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                status, headers={"Content-Encoding": "gzip"}, stream=stream
            )
        )
    ) as client:
        with pytest.raises(YahooOAuthResponseError, match="content encoding"):
            exchange(YahooOAuthClient(config, http_client=client))
    assert stream.read_count == 0 and stream.closed


def test_token_stream_read_failure_is_sanitized_and_closed(
    config: YahooOAuthConfig,
) -> None:
    class FailingStream(TokenStream):
        def __iter__(self) -> Iterator[bytes]:
            yield b"fake-sensitive-partial-response"
            raise httpx.ReadError("fake-sensitive-transport-message")

    stream = FailingStream([])
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, stream=stream)
        )
    ) as client:
        with pytest.raises(YahooOAuthRequestError) as error:
            exchange(YahooOAuthClient(config, http_client=client))
    assert stream.closed
    assert "fake-sensitive" not in "".join(traceback.format_exception(error.value))


@pytest.mark.parametrize(
    "provider_error,expected",
    [
        ("invalid_request", "invalid_request"),
        ("invalid_client", "invalid_client"),
        ("invalid_grant", "invalid_grant"),
        ("unauthorized_client", "unauthorized_client"),
        ("unsupported_grant_type", "unsupported_grant_type"),
        ("invalid_scope", "invalid_scope"),
        ("INVALID_AUTHORIZATION_CODE", "invalid_authorization_code"),
        ("INVALID_INPUT", "invalid_input"),
        ("SESSION_VERIFICATION_FAIL", "session_verification_fail"),
        ("ERROR_HANDLING_REQUEST", "error_handling_request"),
        ("SERVER_ERROR", "server_error"),
    ],
)
def test_rejection_preserves_only_allowlisted_category(
    config: YahooOAuthConfig, provider_error: str, expected: str
) -> None:
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                400,
                json={
                    "error": provider_error,
                    "error_description": "fake-sensitive-code-and-verifier",
                    "access_token": FAKE_ACCESS,
                },
            )
        )
    ) as client:
        with pytest.raises(YahooOAuthRequestError) as error:
            exchange(YahooOAuthClient(config, http_client=client))
    assert error.value.status_code == 400
    assert error.value.error_category == expected
    assert f"category={expected}" in str(error.value)
    rendered = "".join(traceback.format_exception(error.value))
    assert "fake-sensitive" not in rendered and FAKE_ACCESS not in rendered


@pytest.mark.parametrize(
    "content",
    [
        b'{"error":"fake-sensitive-unknown"}',
        b'{"error":"invalid_grant fake-sensitive-suffix"}',
        b'{"error_description":"invalid_grant fake-sensitive-description"}',
        b'{"error":{"invalid_grant":"fake-sensitive-value"}}',
        b'{"error":["invalid_grant"]}',
        b'{"error":null}',
        b'["invalid_grant"]',
        b'"invalid_grant"',
        b"fake-sensitive-invalid-json",
        b'\xff{"error":"invalid_grant"}',
        b'{"error":"invalid_grant","padding":"' + b"x" * 8192 + b'"}',
        b"[" * 2000 + b"0" + b"]" * 2000,
    ],
    ids=[
        "unknown",
        "unknown-suffix",
        "description-only",
        "object",
        "array",
        "null",
        "root-array",
        "root-string",
        "invalid-json",
        "invalid-utf8",
        "oversized",
        "excessive-depth",
    ],
)
def test_unknown_or_malformed_rejection_never_echoes_provider_text(
    config: YahooOAuthConfig, content: bytes
) -> None:
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(400, content=content)
        )
    ) as client:
        with pytest.raises(YahooOAuthRequestError) as error:
            exchange(YahooOAuthClient(config, http_client=client))
    assert error.value.error_category == "unknown"
    assert "category=unknown" in str(error.value)
    assert "fake-sensitive" not in "".join(traceback.format_exception(error.value))


@pytest.mark.parametrize("status", [302, 400, 401, 429, 500])
def test_rejected_response_is_sanitized_and_not_redirected(
    config: YahooOAuthConfig, status: int
) -> None:
    calls: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(
            status,
            json={"error_description": FAKE_REFRESH},
            headers={"Location": "https://example.test/never-called"},
        )

    with httpx.Client(
        transport=httpx.MockTransport(handle), follow_redirects=True
    ) as client:
        with pytest.raises(YahooOAuthRequestError) as error:
            exchange(YahooOAuthClient(config, http_client=client))
    assert error.value.status_code == status
    assert FAKE_REFRESH not in str(error.value) and len(calls) == 1


def test_transport_failure_is_sanitized(config: YahooOAuthConfig) -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(FAKE_ACCESS, request=request)

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(YahooOAuthRequestError) as error:
            exchange(YahooOAuthClient(config, http_client=client))
    assert FAKE_ACCESS not in "".join(traceback.format_exception(error.value))


@pytest.mark.parametrize("state", ["", "fake-wrong-state", "fake-unicode-☃"])
def test_invalid_state_blocks_http(config: YahooOAuthConfig, state: str) -> None:
    def no_request(request: httpx.Request) -> httpx.Response:
        pytest.fail("Invalid state must not send a token request")

    with httpx.Client(transport=httpx.MockTransport(no_request)) as client:
        with pytest.raises(YahooAuthorizationSessionError):
            YahooOAuthClient(config, http_client=client).exchange_code(
                SecretStr("fake-code"),
                session=YahooAuthorizationSession(),
                returned_state=state,
            )


def test_exchange_is_one_attempt_even_on_failure(config: YahooOAuthConfig) -> None:
    session = YahooAuthorizationSession()
    state = session.authorization_parameters()["state"]
    calls: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(400)

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        oauth = YahooOAuthClient(config, http_client=client)
        with pytest.raises(YahooOAuthRequestError):
            oauth.exchange_code(
                SecretStr("fake-code"), session=session, returned_state=state
            )
        with pytest.raises(YahooAuthorizationSessionError):
            oauth.exchange_code(
                SecretStr("fake-code"), session=session, returned_state=state
            )
    assert len(calls) == 1


def test_missing_refresh_fails_before_http(config: YahooOAuthConfig) -> None:
    previous = previous_tokens().model_copy(update={"refresh_token": None})
    with httpx.Client() as client:
        with pytest.raises(MissingYahooRefreshTokenError):
            YahooOAuthClient(config, http_client=client).refresh_tokens(previous)


def test_blank_code_fails_before_http(config: YahooOAuthConfig) -> None:
    session = YahooAuthorizationSession()
    state = session.authorization_parameters()["state"]
    with httpx.Client() as client:
        with pytest.raises(YahooOAuthError, match="blank"):
            YahooOAuthClient(config, http_client=client).exchange_code(
                SecretStr(" "), session=session, returned_state=state
            )


def test_no_token_logging(
    config: YahooOAuthConfig, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=payload())
        )
    ) as client:
        exchange(YahooOAuthClient(config, http_client=client))
    for secret in (FAKE_ACCESS, FAKE_REFRESH, "fake-code+&-for-tests"):
        assert secret not in caplog.text


def test_live_http_guards() -> None:
    with httpx.Client(trust_env=False) as client:
        with pytest.raises(AssertionError, match="Live HTTP"):
            client.get("https://example.test/never-called")

    async def attempt() -> None:
        async with httpx.AsyncClient(trust_env=False) as client:
            await client.get("https://example.test/never-called")

    with pytest.raises(AssertionError, match="Live HTTP"):
        asyncio.run(attempt())
