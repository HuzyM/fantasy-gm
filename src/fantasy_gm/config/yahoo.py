"""Explicit environment configuration for Yahoo OAuth."""

import os
from typing import Annotated, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    SecretStr,
    StringConstraints,
    ValidationError,
    field_validator,
)

_ENVIRONMENT_KEYS = (
    "YAHOO_CLIENT_ID",
    "YAHOO_CLIENT_SECRET",
    "YAHOO_REDIRECT_URI",
)


class YahooOAuthConfig(BaseModel):
    """Required settings; loading never falls back to files or embedded values."""

    model_config = ConfigDict(
        frozen=True, populate_by_name=True, hide_input_in_errors=True
    )

    client_id: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1)
    ] = Field(validation_alias="YAHOO_CLIENT_ID")
    client_secret: SecretStr = Field(validation_alias="YAHOO_CLIENT_SECRET")
    redirect_uri: str = Field(validation_alias="YAHOO_REDIRECT_URI")

    @field_validator("client_secret")
    @classmethod
    def validate_secret(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().strip():
            raise ValueError("YAHOO_CLIENT_SECRET must not be blank")
        return value

    @field_validator("redirect_uri")
    @classmethod
    def validate_redirect_uri(cls, value: str) -> str:
        # Preserve the exact registered URI rather than normalizing its spelling.
        if value == "oob":
            return value
        try:
            url = HttpUrl(value)
        except ValidationError:
            raise ValueError(
                "YAHOO_REDIRECT_URI must be an absolute HTTP(S) URL or 'oob'"
            ) from None
        if (
            any(character.isspace() for character in value)
            or "#" in value
            or url.username is not None
            or url.password is not None
        ):
            raise ValueError(
                "YAHOO_REDIRECT_URI must not contain whitespace, "
                "user info, or a fragment"
            )
        return value

    @classmethod
    def from_environment(cls) -> Self:
        """Validate only the three named environment variables; no .env loading."""
        return cls.model_validate(
            {key: os.environ[key] for key in _ENVIRONMENT_KEYS if key in os.environ}
        )
