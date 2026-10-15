"""RFC 7636 S256 PKCE values, held only in memory."""

import base64
import hashlib
import re
import secrets
from collections.abc import Callable

from pydantic import BaseModel, ConfigDict, SecretStr


def s256_challenge(verifier: SecretStr) -> str:
    """Validate an RFC 7636 verifier and derive its unpadded base64url challenge."""
    value = verifier.get_secret_value()
    if re.fullmatch(r"[A-Za-z0-9._~-]{43,128}", value) is None:
        raise ValueError("PKCE verifier must contain 43–128 RFC 7636 characters")
    digest = hashlib.sha256(value.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


class PKCEPair(BaseModel):
    """The verifier is masked; only the derived challenge is public."""

    model_config = ConfigDict(frozen=True, hide_input_in_errors=True)
    verifier: SecretStr
    challenge: str

    @classmethod
    def generate(
        cls, random_bytes: Callable[[int], bytes] = secrets.token_bytes
    ) -> "PKCEPair":
        entropy = random_bytes(32)
        if len(entropy) != 32:
            raise ValueError("PKCE generation requires exactly 32 random bytes")
        verifier = SecretStr(
            base64.urlsafe_b64encode(entropy).rstrip(b"=").decode("ascii")
        )
        return cls(verifier=verifier, challenge=s256_challenge(verifier))
