"""Verify Yahoo OAuth wire behavior with fake values and MockTransport only."""

import asyncio
import base64
import logging
import traceback
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from pydantic import SecretStr

from fantasy_gm.config.yahoo import YahooOAuthConfig
from fantasy_gm.providers.yahoo.oauth import (
    AUTHORIZATION_ENDPOINT,
    TOKEN_ENDPOINT,
    MissingYahooRefreshTokenError,
    YahooOAuthClient,
    YahooOAuthRequestError,
    YahooOAuthResponseError,
)

FAKE_ACCESS_TOKEN = "fake-access-token-for-tests"
FAKE_REFRESH_TOKEN = "fake-refresh-token-for-tests"
FAKE_SECRET = "fake-client-secret-for-tests"


@pytest.fixture
def config() -> YahooOAuthConfig:
    return YahooOAuthConfig(
        client_id="fake-client-id-for-tests",
        client_secret=SecretStr(FAKE_SECRET),
        redirect_uri="http://localhost:8080/callback?source=fake&next=%2F",
    )


def token_payload() -> dict[str, object]:
    return {
        "access_token": FAKE_ACCESS_TOKEN,
        "refresh_token": FAKE_REFRESH_TOKEN,
        "expires_in": 3600,
        "token_type": "bearer",
        "xoauth_yahoo_guid": "fake-ignored-guid-for-tests",
    }


def test_authorization_url_encodes_parameters(config: YahooOAuthConfig) -> None:
    def no_request(request: httpx.Request) -> httpx.Response:
        pytest.fail("Constructing an authorization URL must not make a request")

    with httpx.Client(transport=httpx.MockTransport(no_request)) as http_client:
        oauth = YahooOAuthClient(config, http_client=http_client)
        url = oauth.authorization_url(state="fake-state-with-&-and-+-for-tests")
    parsed = urlsplit(url)
    assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == AUTHORIZATION_ENDPOINT
    assert parse_qs(parsed.query) == {
        "client_id": [config.client_id],
        "redirect_uri": [config.redirect_uri],
        "response_type": ["code"],
        "state": ["fake-state-with-&-and-+-for-tests"],
    }
    assert FAKE_SECRET not in url


@pytest.mark.parametrize("grant", ["authorization_code", "refresh_token"])
def test_token_exchange_wire_format(config: YahooOAuthConfig, grant: str) -> None:
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert str(request.url) == TOKEN_ENDPOINT
        assert request.method == "POST"
        assert request.headers["content-type"] == "application/x-www-form-urlencoded"
        assert request.headers["accept"] == "application/json"
        expected_auth = base64.b64encode(
            f"{config.client_id}:{FAKE_SECRET}".encode()
        ).decode()
        assert request.headers["authorization"] == f"Basic {expected_auth}"
        credential_field = "code" if grant == "authorization_code" else "refresh_token"
        credential = (
            "fake-code-with-&-and-+-for-tests"
            if grant == "authorization_code"
            else FAKE_REFRESH_TOKEN
        )
        assert parse_qs(request.content.decode()) == {
            "grant_type": [grant],
            "redirect_uri": [config.redirect_uri],
            credential_field: [credential],
        }
        return httpx.Response(200, json=token_payload())

    with httpx.Client(transport=httpx.MockTransport(handle)) as http_client:
        oauth = YahooOAuthClient(config, http_client=http_client)
        tokens = (
            oauth.exchange_code("fake-code-with-&-and-+-for-tests")
            if grant == "authorization_code"
            else oauth.refresh_tokens(SecretStr(FAKE_REFRESH_TOKEN))
        )
    assert len(requests) == 1
    assert tokens.access_token.get_secret_value() == FAKE_ACCESS_TOKEN
    assert tokens.refresh_token is not None
    assert tokens.refresh_token.get_secret_value() == FAKE_REFRESH_TOKEN
    assert tokens.expires_in == 3600
    assert tokens.token_type == "bearer"
    assert not hasattr(tokens, "xoauth_yahoo_guid")
    for secret in (FAKE_ACCESS_TOKEN, FAKE_REFRESH_TOKEN):
        assert secret not in repr(tokens)
        assert secret not in tokens.model_dump_json()


@pytest.mark.parametrize(
    "refresh_value", [None, "fake-rotated-refresh-token-for-tests"]
)
def test_refresh_response_preserves_optional_or_rotated_token(
    config: YahooOAuthConfig, refresh_value: str | None
) -> None:
    payload = token_payload()
    if refresh_value is None:
        del payload["refresh_token"]
    else:
        payload["refresh_token"] = refresh_value
    with httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ) as http_client:
        tokens = YahooOAuthClient(config, http_client=http_client).refresh_tokens(
            SecretStr(FAKE_REFRESH_TOKEN)
        )
    if refresh_value is None:
        assert tokens.refresh_token is None
    else:
        assert tokens.refresh_token is not None
        assert tokens.refresh_token.get_secret_value() == refresh_value


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"access_token": FAKE_ACCESS_TOKEN},
        {**token_payload(), "access_token": " "},
        {**token_payload(), "refresh_token": ""},
        {**token_payload(), "expires_in": 0},
        {**token_payload(), "expires_in": -1},
        {**token_payload(), "expires_in": True},
        {**token_payload(), "expires_in": "3600"},
        {**token_payload(), "token_type": " "},
        {**token_payload(), "access_token": 123},
    ],
)
def test_malformed_token_response(
    config: YahooOAuthConfig, payload: dict[str, object]
) -> None:
    with httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ) as http_client:
        with pytest.raises(YahooOAuthResponseError) as error:
            YahooOAuthClient(config, http_client=http_client).exchange_code("fake-code")
    rendered = "".join(traceback.format_exception(error.value))
    assert FAKE_ACCESS_TOKEN not in rendered
    assert FAKE_REFRESH_TOKEN not in rendered


def test_invalid_json_response(config: YahooOAuthConfig) -> None:
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, text="fake-invalid-json-for-tests")
        )
    ) as http_client:
        with pytest.raises(YahooOAuthResponseError, match="Malformed"):
            YahooOAuthClient(config, http_client=http_client).exchange_code("fake-code")


@pytest.mark.parametrize("status", [302, 400, 401, 429, 500])
def test_rejected_response_never_echoes_body_or_follows_redirects(
    config: YahooOAuthConfig, status: int
) -> None:
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            status,
            json={"error_description": FAKE_SECRET},
            headers={"Location": "https://example.test/should-never-be-called"},
        )

    with httpx.Client(
        transport=httpx.MockTransport(handle), follow_redirects=True
    ) as http_client:
        with pytest.raises(YahooOAuthRequestError) as error:
            YahooOAuthClient(config, http_client=http_client).exchange_code("fake-code")
    assert error.value.status_code == status
    assert FAKE_SECRET not in str(error.value)
    assert len(requests) == 1


def test_transport_failure_is_sanitized(config: YahooOAuthConfig) -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(FAKE_SECRET, request=request)

    with httpx.Client(transport=httpx.MockTransport(handle)) as http_client:
        with pytest.raises(YahooOAuthRequestError) as error:
            YahooOAuthClient(config, http_client=http_client).exchange_code("fake-code")
    assert error.value.status_code is None
    assert FAKE_SECRET not in "".join(traceback.format_exception(error.value))


@pytest.mark.parametrize("token", [None, SecretStr(""), SecretStr(" ")])
def test_missing_refresh_token_does_not_send_request(
    config: YahooOAuthConfig, token: SecretStr | None
) -> None:
    def no_request(request: httpx.Request) -> httpx.Response:
        pytest.fail("Missing refresh token must fail before a request")

    with httpx.Client(transport=httpx.MockTransport(no_request)) as http_client:
        with pytest.raises(MissingYahooRefreshTokenError):
            YahooOAuthClient(config, http_client=http_client).refresh_tokens(token)


@pytest.mark.parametrize("value", ["", " "])
def test_blank_state_and_code_do_not_send_request(
    config: YahooOAuthConfig, value: str
) -> None:
    def no_request(request: httpx.Request) -> httpx.Response:
        pytest.fail("Invalid input must fail before a request")

    with httpx.Client(transport=httpx.MockTransport(no_request)) as http_client:
        oauth = YahooOAuthClient(config, http_client=http_client)
        with pytest.raises(ValueError):
            oauth.exchange_code(value)
        with pytest.raises(ValueError):
            oauth.authorization_url(state=value)


def test_live_http_guard_is_active() -> None:
    with httpx.Client(trust_env=False) as http_client:
        with pytest.raises(AssertionError, match="Live HTTP is forbidden"):
            http_client.get("https://example.test/never-requested")


def test_live_async_http_guard_is_active() -> None:
    async def attempt_request() -> None:
        async with httpx.AsyncClient(trust_env=False) as http_client:
            await http_client.get("https://example.test/never-requested")

    with pytest.raises(AssertionError, match="Live HTTP is forbidden"):
        asyncio.run(attempt_request())


def test_oauth_does_not_log_credentials_or_tokens(
    config: YahooOAuthConfig, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=token_payload())
        )
    ) as http_client:
        YahooOAuthClient(config, http_client=http_client).exchange_code("fake-code")
    for value in (FAKE_SECRET, FAKE_ACCESS_TOKEN, FAKE_REFRESH_TOKEN, "fake-code"):
        assert value not in caplog.text
