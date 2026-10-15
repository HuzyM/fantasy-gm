"""PKCE test vector from RFC 7636, plus synthetic authorization state."""

import asyncio
import re
import socket
import urllib.request

import pytest
from pydantic import SecretStr

from fantasy_gm.providers.yahoo.pkce import PKCEPair, s256_challenge
from fantasy_gm.providers.yahoo.session import (
    YahooAuthorizationSession,
    YahooAuthorizationSessionError,
)


def test_pkce_rfc7636_vector() -> None:
    # Public RFC example, not an actual credential.
    verifier = SecretStr("dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk")
    assert s256_challenge(verifier) == "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"


def test_pkce_injected_entropy_and_masking() -> None:
    def deterministic(size: int) -> bytes:
        assert size == 32
        return bytes(range(32))

    pair = PKCEPair.generate(deterministic)
    verifier = pair.verifier.get_secret_value()
    assert len(verifier) == 43
    assert re.fullmatch(r"[A-Za-z0-9_-]+", verifier)
    assert re.fullmatch(r"[A-Za-z0-9_-]{43}", pair.challenge)
    assert "=" not in verifier + pair.challenge
    assert verifier not in repr(pair) and verifier not in pair.model_dump_json()


def test_pkce_random_values_differ() -> None:
    assert PKCEPair.generate().verifier != PKCEPair.generate().verifier


@pytest.mark.parametrize("value", ["fake-too-short", "a" * 129, "a" * 42 + "!"])
def test_invalid_pkce_is_rejected(value: str) -> None:
    with pytest.raises(ValueError, match="PKCE verifier") as error:
        s256_challenge(SecretStr(value))
    assert value not in str(error.value)


def test_wrong_entropy_size_is_rejected() -> None:
    with pytest.raises(ValueError):
        PKCEPair.generate(lambda size: b"fake")


def test_session_random_state_and_no_sensitive_repr() -> None:
    first, second = YahooAuthorizationSession(), YahooAuthorizationSession()
    params = first.authorization_parameters()
    assert params["state"] != second.authorization_parameters()["state"]
    assert re.fullmatch(r"[A-Za-z0-9_-]{43}", params["state"])
    assert params["code_challenge_method"] == "S256"
    assert params["state"] not in repr(first)
    assert first._pkce.verifier.get_secret_value() not in repr(first)


def test_valid_state_consumes_once() -> None:
    session = YahooAuthorizationSession()
    params = session.authorization_parameters()
    verifier = session.consume(params["state"])
    assert s256_challenge(verifier) == params["code_challenge"]
    with pytest.raises(YahooAuthorizationSessionError, match="already used"):
        session.consume(params["state"])
    with pytest.raises(YahooAuthorizationSessionError):
        session.authorization_parameters()


def test_invalid_state_consumes_session() -> None:
    session = YahooAuthorizationSession()
    original = session.authorization_parameters()["state"]
    with pytest.raises(YahooAuthorizationSessionError, match="validation failed"):
        session.consume("fake-wrong-state")
    with pytest.raises(YahooAuthorizationSessionError, match="already used"):
        session.consume(original)


def test_socket_guard_blocks_non_httpx_connections() -> None:
    with socket.socket() as client:
        with pytest.raises(AssertionError, match="Live network"):
            client.connect(("127.0.0.1", 9))
    with pytest.raises(AssertionError, match="Live network"):
        socket.getaddrinfo("example.test", 443)


def test_async_network_guard_blocks_non_httpx_connections() -> None:
    async def attempt() -> None:
        await asyncio.get_running_loop().create_connection(
            asyncio.Protocol, "127.0.0.1", 9
        )

    with pytest.raises(AssertionError, match="Live network"):
        asyncio.run(attempt())


def test_stdlib_http_is_also_blocked() -> None:
    with pytest.raises(AssertionError, match="Live network"):
        urllib.request.urlopen("https://example.test/never-called", timeout=1)
