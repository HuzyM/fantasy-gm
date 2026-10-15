"""Public Client configuration; no real credentials are used."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from fantasy_gm.config.yahoo import YAHOO_REDIRECT_URI, YahooOAuthConfig


def test_client_id_is_the_only_required_environment_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("YAHOO_CLIENT_ID", "fake-client-id-for-tests")
    config = YahooOAuthConfig.from_environment()
    assert config.client_id == "fake-client-id-for-tests"
    assert config.redirect_uri == YAHOO_REDIRECT_URI
    assert "client_secret" not in YahooOAuthConfig.model_fields


@pytest.mark.parametrize("value", [None, "", "   "])
def test_missing_or_blank_id_is_clear(
    monkeypatch: pytest.MonkeyPatch, value: str | None
) -> None:
    if value is not None:
        monkeypatch.setenv("YAHOO_CLIENT_ID", value)
    with pytest.raises(ValidationError, match="YAHOO_CLIENT_ID"):
        YahooOAuthConfig.from_environment()


def test_legacy_environment_values_are_not_used(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("YAHOO_CLIENT_ID", "fake-client-id-for-tests")
    monkeypatch.setenv("YAHOO_CLIENT_SECRET", "fake-obsolete-secret-for-tests")
    monkeypatch.setenv("YAHOO_REDIRECT_URI", "https://example.test/wrong-callback")
    config = YahooOAuthConfig.from_environment()
    assert config.redirect_uri == YAHOO_REDIRECT_URI
    assert "fake-obsolete-secret" not in repr(config)


def test_unknown_secret_configuration_is_rejected() -> None:
    with pytest.raises(ValidationError, match="client_secret"):
        YahooOAuthConfig.model_validate(
            {"client_id": "fake-id", "client_secret": "fake-secret"}
        )


def test_redirect_override_is_rejected() -> None:
    with pytest.raises(ValidationError, match="redirect_uri"):
        YahooOAuthConfig.model_validate({"client_id": "fake-id", "redirect_uri": "oob"})


def test_dotenv_is_not_read(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "YAHOO_CLIENT_ID=fake-id-for-tests", encoding="utf-8"
    )
    with pytest.raises(ValidationError, match="YAHOO_CLIENT_ID"):
        YahooOAuthConfig.from_environment()
