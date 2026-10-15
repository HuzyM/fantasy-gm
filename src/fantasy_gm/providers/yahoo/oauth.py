"""Yahoo OAuth transport and token models, isolated from the core domain."""

import json
import re
from enum import StrEnum
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
from fantasy_gm.providers.yahoo.session import YahooAuthorizationSession

AUTHORIZATION_ENDPOINT = "https://api.login.yahoo.com/oauth2/request_auth"
TOKEN_ENDPOINT = "https://api.login.yahoo.com/oauth2/get_token"
MAX_TOKEN_RESPONSE_BYTES = 64 * 1024


class YahooOAuthError(Exception):
    """Base for errors in the Yahoo OAuth boundary."""


class YahooOAuthErrorCategory(StrEnum):
    """Allowlisted protocol codes, never Yahoo's free-form error description."""

    UNKNOWN = "unknown"
    INVALID_REQUEST = "invalid_request"
    INVALID_CLIENT = "invalid_client"
    INVALID_GRANT = "invalid_grant"
    UNAUTHORIZED_CLIENT = "unauthorized_client"
    UNSUPPORTED_GRANT_TYPE = "unsupported_grant_type"
    INVALID_SCOPE = "invalid_scope"
    INVALID_AUTHORIZATION_CODE = "invalid_authorization_code"
    INVALID_INPUT = "invalid_input"
    SESSION_VERIFICATION_FAIL = "session_verification_fail"
    ERROR_HANDLING_REQUEST = "error_handling_request"
    SERVER_ERROR = "server_error"


def _error_category(content: bytearray) -> YahooOAuthErrorCategory:
    # A small JSON error is sufficient. Ignore oversized or malformed responses.
    if len(content) > 8192:
        return YahooOAuthErrorCategory.UNKNOWN
    try:
        payload = json.loads(content)
        value = payload.get("error") if isinstance(payload, dict) else None
        if isinstance(value, str):
            return YahooOAuthErrorCategory(value.lower())
    except (ValueError, UnicodeDecodeError, RecursionError):
        pass
    return YahooOAuthErrorCategory.UNKNOWN


class YahooOAuthRequestError(YahooOAuthError):
    """A token request failed in transport or was rejected by Yahoo."""

    def __init__(
        self,
        status_code: int | None = None,
        *,
        error_category: YahooOAuthErrorCategory = YahooOAuthErrorCategory.UNKNOWN,
    ) -> None:
        self.status_code = status_code
        self.error_category = error_category
        message = "Yahoo OAuth token request failed"
        if status_code is not None:
            message = (
                f"Yahoo OAuth token request rejected (HTTP {status_code}); "
                f"category={error_category.value}"
            )
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

    @field_validator("access_token")
    @classmethod
    def validate_bearer_token(cls, value: SecretStr) -> SecretStr:
        if re.fullmatch(r"[-A-Za-z0-9._~+/]+=*", value.get_secret_value()) is None:
            raise ValueError("Access token must use Bearer token syntax")
        return value


class YahooOAuthClient:
    """Small synchronous OAuth client; the caller owns the injected HTTP client."""

    def __init__(self, config: YahooOAuthConfig, *, http_client: httpx.Client) -> None:
        self._config = config
        self._http_client = http_client

    def authorization_url(self, session: YahooAuthorizationSession) -> str:
        """Build a Public Client PKCE URL without OIDC or write scopes."""
        query = urlencode(
            {
                "client_id": self._config.client_id,
                "redirect_uri": self._config.redirect_uri,
                "response_type": "code",
                **session.authorization_parameters(),
            }
        )
        return f"{AUTHORIZATION_ENDPOINT}?{query}"

    def exchange_code(
        self,
        code: SecretStr,
        *,
        session: YahooAuthorizationSession,
        returned_state: str,
    ) -> YahooOAuthTokens:
        """Validate and consume local state before any Public Client token request."""
        verifier = session.consume(returned_state)
        if not code.get_secret_value().strip():
            raise YahooOAuthError("Authorization code must not be blank")
        return self._request_tokens(
            {
                "grant_type": "authorization_code",
                "code": code.get_secret_value(),
                "code_verifier": verifier.get_secret_value(),
            }
        )

    def refresh_tokens(self, previous: YahooOAuthTokens) -> YahooOAuthTokens:
        """Preserve a rotated token, or retain the previous token when omitted."""
        refresh_token = previous.refresh_token
        if refresh_token is None or not refresh_token.get_secret_value().strip():
            raise MissingYahooRefreshTokenError("A refresh token is required")
        refreshed = self._request_tokens(
            {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token.get_secret_value(),
            }
        )
        if refreshed.refresh_token is None:
            refreshed = refreshed.model_copy(update={"refresh_token": refresh_token})
        return refreshed

    def _request_tokens(self, data: dict[str, str]) -> YahooOAuthTokens:
        try:
            request = self._http_client.build_request(
                "POST",
                TOKEN_ENDPOINT,
                data={
                    **data,
                    "client_id": self._config.client_id,
                    "redirect_uri": self._config.redirect_uri,
                },
                headers={"Accept": "application/json", "Accept-Encoding": "identity"},
                timeout=10.0,
            )
            # Suppress inherited client auth, including default header values.
            request.headers.pop("Authorization", None)
            response = self._http_client.send(
                request, auth=None, follow_redirects=False, stream=True
            )
            try:
                if response.headers.get(
                    "Content-Encoding", "identity"
                ).strip().lower() not in ("", "identity"):
                    raise YahooOAuthResponseError(
                        "Unsupported Yahoo OAuth token content encoding"
                    )
                content = bytearray()
                # Compression is rejected before iteration, so these are identity
                # bytes. Count received bytes rather than trusting Content-Length.
                for chunk in response.iter_bytes():
                    if len(chunk) > MAX_TOKEN_RESPONSE_BYTES - len(content):
                        raise YahooOAuthResponseError(
                            "Yahoo OAuth token response exceeds size limit"
                        )
                    content.extend(chunk)
            finally:
                response.close()
        except httpx.RequestError:
            # Do not expose request bodies, auth headers, or underlying messages.
            raise YahooOAuthRequestError() from None
        if not response.is_success:
            # Retain only status and an exact allowlisted code, never descriptions.
            raise YahooOAuthRequestError(
                response.status_code, error_category=_error_category(content)
            )
        try:
            return YahooOAuthTokens.model_validate_json(content)
        except ValidationError:
            raise YahooOAuthResponseError(
                "Malformed Yahoo OAuth token response"
            ) from None
