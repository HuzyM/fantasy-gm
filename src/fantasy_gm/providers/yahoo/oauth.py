"""Yahoo OAuth transport and token models, isolated from the core domain."""

from typing import Annotated
from urllib.parse import urlencode

import httpx
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    StringConstraints,
    ValidationError,
    field_validator,
)

from fantasy_gm.config.yahoo import YahooOAuthConfig

AUTHORIZATION_ENDPOINT = "https://api.login.yahoo.com/oauth2/request_auth"
TOKEN_ENDPOINT = "https://api.login.yahoo.com/oauth2/get_token"


class YahooOAuthError(Exception):
    """Base for errors in the Yahoo OAuth boundary."""


class YahooOAuthRequestError(YahooOAuthError):
    """A token request failed in transport or was rejected by Yahoo."""

    def __init__(self, status_code: int | None = None) -> None:
        self.status_code = status_code
        message = "Yahoo OAuth token request failed"
        if status_code is not None:
            message = f"Yahoo OAuth token request rejected (HTTP {status_code})"
        super().__init__(message)


class YahooOAuthResponseError(YahooOAuthError):
    """Yahoo returned an invalid token response."""


class MissingYahooRefreshTokenError(YahooOAuthError):
    """Refresh was attempted without a usable refresh token."""


class YahooOAuthTokens(BaseModel):
    """In-memory tokens; expires_in is the lifetime in seconds, not a timestamp."""

    model_config = ConfigDict(frozen=True, strict=True, hide_input_in_errors=True)

    access_token: SecretStr
    refresh_token: SecretStr | None = None
    expires_in: Annotated[int, Field(gt=0)]
    token_type: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

    @field_validator("access_token", "refresh_token")
    @classmethod
    def validate_token(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None and not value.get_secret_value().strip():
            raise ValueError("Token must not be blank")
        return value


class YahooOAuthClient:
    """Small synchronous OAuth client; the caller owns the injected HTTP client."""

    def __init__(self, config: YahooOAuthConfig, *, http_client: httpx.Client) -> None:
        self._config = config
        self._http_client = http_client

    def authorization_url(self, *, state: str) -> str:
        """Build a URL; the caller must generate and later validate random state."""
        if not state.strip():
            raise ValueError("OAuth state must not be blank")
        query = urlencode(
            {
                "client_id": self._config.client_id,
                "redirect_uri": self._config.redirect_uri,
                "response_type": "code",
                "state": state,
            }
        )
        return f"{AUTHORIZATION_ENDPOINT}?{query}"

    def exchange_code(self, code: str) -> YahooOAuthTokens:
        """Exchange a code without persisting it or the resulting tokens."""
        if not code.strip():
            raise ValueError("Authorization code must not be blank")
        return self._request_tokens({"grant_type": "authorization_code", "code": code})

    def refresh_tokens(self, refresh_token: SecretStr | None) -> YahooOAuthTokens:
        """Return Yahoo's response, including a rotated refresh token if supplied."""
        if refresh_token is None or not refresh_token.get_secret_value().strip():
            raise MissingYahooRefreshTokenError("A refresh token is required")
        return self._request_tokens(
            {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token.get_secret_value(),
            }
        )

    def _request_tokens(self, data: dict[str, str]) -> YahooOAuthTokens:
        try:
            response = self._http_client.post(
                TOKEN_ENDPOINT,
                data={**data, "redirect_uri": self._config.redirect_uri},
                auth=httpx.BasicAuth(
                    self._config.client_id,
                    self._config.client_secret.get_secret_value(),
                ),
                headers={"Accept": "application/json"},
                timeout=10.0,
                follow_redirects=False,
            )
        except httpx.RequestError:
            # Do not expose request bodies, auth headers, or underlying messages.
            raise YahooOAuthRequestError() from None
        if not response.is_success:
            # Provider error bodies may echo secrets; only retain the HTTP status.
            raise YahooOAuthRequestError(response.status_code)
        try:
            return YahooOAuthTokens.model_validate_json(response.content)
        except ValidationError:
            raise YahooOAuthResponseError(
                "Malformed Yahoo OAuth token response"
            ) from None
