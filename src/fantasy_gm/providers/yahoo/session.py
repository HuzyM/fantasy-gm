"""A one-attempt Yahoo authorization session with no persistence."""

import secrets
from dataclasses import dataclass, field

from pydantic import SecretStr

from fantasy_gm.providers.yahoo.pkce import PKCEPair


class YahooAuthorizationSessionError(Exception):
    """Invalid state or a session that has already been consumed."""


@dataclass
class YahooAuthorizationSession:
    """State and verifier stay local. Every submission consumes the session."""

    _state: SecretStr = field(
        default_factory=lambda: SecretStr(secrets.token_urlsafe(32)), repr=False
    )
    _pkce: PKCEPair = field(default_factory=PKCEPair.generate, repr=False)
    _consumed: bool = field(default=False, init=False)

    def authorization_parameters(self) -> dict[str, str]:
        if self._consumed:
            raise YahooAuthorizationSessionError("Authorization session already used")
        return {
            "state": self._state.get_secret_value(),
            "code_challenge": self._pkce.challenge,
            "code_challenge_method": "S256",
        }

    def consume(self, returned_state: str) -> SecretStr:
        """Validate state before releasing the verifier for one token request."""
        if self._consumed:
            raise YahooAuthorizationSessionError("Authorization session already used")
        self._consumed = True
        try:
            valid = secrets.compare_digest(
                self._state.get_secret_value().encode("utf-8"),
                returned_state.encode("utf-8"),
            )
        except UnicodeEncodeError:
            # Windows getwch can return a lone surrogate; reject without a traceback.
            valid = False
        if not returned_state or not valid:
            raise YahooAuthorizationSessionError("Yahoo OAuth state validation failed")
        return self._pkce.verifier
