"""Configuration tests use only explicitly fake credentials."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from fantasy_gm.config.yahoo import YahooOAuthConfig

ENVIRONMENT = {
    "YAHOO_CLIENT_ID": "fake-client-id-for-tests",
    "YAHOO_CLIENT_SECRET": "fake-client-secret-for-tests",
    "YAHOO_REDIRECT_URI": "http://localhost:8080/callback",
}


def set_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in ENVIRONMENT.items():
        monkeypatch.setenv(key, value)


def test_configuration_loads_explicit_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    set_environment(monkeypatch)
    config = YahooOAuthConfig.from_environment()
    assert config.client_id == ENVIRONMENT["YAHOO_CLIENT_ID"]
    assert config.client_secret.get_secret_value() == ENVIRONMENT["YAHOO_CLIENT_SECRET"]
    assert config.redirect_uri == ENVIRONMENT["YAHOO_REDIRECT_URI"]
    assert ENVIRONMENT["YAHOO_CLIENT_SECRET"] not in repr(config)
    assert ENVIRONMENT["YAHOO_CLIENT_SECRET"] not in config.model_dump_json()


@pytest.mark.parametrize("key", ENVIRONMENT)
def test_missing_configuration_is_clear(
    monkeypatch: pytest.MonkeyPatch, key: str
) -> None:
    set_environment(monkeypatch)
    monkeypatch.delenv(key)
    with pytest.raises(ValidationError, match=key):
        YahooOAuthConfig.from_environment()


@pytest.mark.parametrize("key", ENVIRONMENT)
@pytest.mark.parametrize("value", ["", "   "])
def test_blank_configuration_is_rejected(
    monkeypatch: pytest.MonkeyPatch, key: str, value: str
) -> None:
    set_environment(monkeypatch)
    monkeypatch.setenv(key, value)
    with pytest.raises(ValidationError, match=key) as error:
        YahooOAuthConfig.from_environment()
    assert ENVIRONMENT["YAHOO_CLIENT_SECRET"] not in str(error.value)


@pytest.mark.parametrize(
    "uri",
    [
        "not-a-url",
        "ftp://example.test/callback",
        "https://example.test/#fragment",
        "https://user:fake-password@example.test/callback",
        "https://:fake-password@example.test/callback",
        "https://example.test/call\nback",
    ],
)
def test_invalid_redirect_uri_is_rejected(
    monkeypatch: pytest.MonkeyPatch, uri: str
) -> None:
    set_environment(monkeypatch)
    monkeypatch.setenv("YAHOO_REDIRECT_URI", uri)
    with pytest.raises(ValidationError, match="YAHOO_REDIRECT_URI"):
        YahooOAuthConfig.from_environment()


@pytest.mark.parametrize("uri", ["https://example.test", "oob"])
def test_redirect_uri_is_preserved_exactly(
    monkeypatch: pytest.MonkeyPatch, uri: str
) -> None:
    set_environment(monkeypatch)
    monkeypatch.setenv("YAHOO_REDIRECT_URI", uri)
    assert YahooOAuthConfig.from_environment().redirect_uri == uri


def test_configuration_does_not_read_dotenv(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "\n".join(f"{key}={value}" for key, value in ENVIRONMENT.items()),
        encoding="utf-8",
    )
    with pytest.raises(ValidationError, match="YAHOO_CLIENT_ID"):
        YahooOAuthConfig.from_environment()
