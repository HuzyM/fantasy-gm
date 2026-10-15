"""Configuration for the confirmed Yahoo Public Client application."""

import os
from typing import Annotated, Final, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

YAHOO_REDIRECT_URI: Final = "https://huzym.github.io/fantasy-gm/oauth/callback/"


class YahooOAuthConfig(BaseModel):
    """Only the client ID is configurable; no client secret or fallback files."""

    model_config = ConfigDict(
        frozen=True, populate_by_name=True, extra="forbid", hide_input_in_errors=True
    )
    client_id: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1)
    ] = Field(validation_alias="YAHOO_CLIENT_ID")
    redirect_uri: Literal["https://huzym.github.io/fantasy-gm/oauth/callback/"] = (
        YAHOO_REDIRECT_URI
    )

    @classmethod
    def from_environment(cls) -> Self:
        """Read the client ID only; ignore legacy secret/redirect environment values."""
        values = {}
        if "YAHOO_CLIENT_ID" in os.environ:
            values["YAHOO_CLIENT_ID"] = os.environ["YAHOO_CLIENT_ID"]
        return cls.model_validate(values)
