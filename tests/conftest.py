"""Block network during test execution; imports/subprocesses need separate guards."""

import asyncio
import socket
from typing import Never

import httpx
import pytest

_WAKEUP_CONNECT = socket.socket.connect


def _wakeup_socketpair() -> tuple[socket.socket, socket.socket]:
    """Create only asyncio's private pair without unpatching global connect."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.settimeout(5.0)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            client.settimeout(5.0)
            # The exception is this specific socket and freshly bound listener.
            _WAKEUP_CONNECT(client, listener.getsockname())
            server, _ = listener.accept()
            try:
                # Match the stdlib fallback's check against an unrelated peer.
                if (
                    server.getsockname() != client.getpeername()
                    or client.getsockname() != server.getpeername()
                ):
                    raise ConnectionError("Unexpected wakeup socket peer")
                server.settimeout(None)
                client.settimeout(None)
            except BaseException:
                server.close()
                raise
        except BaseException:
            client.close()
            raise
    return server, client


@pytest.fixture(autouse=True)
def isolate_yahoo_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "YAHOO_CLIENT_ID",
        "YAHOO_CLIENT_SECRET",
        "YAHOO_REDIRECT_URI",
        "YAHOO_AI_TOOLS_ENABLED",
        "PUCKAPI_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)


@pytest.fixture(autouse=True)
def block_live_http(monkeypatch: pytest.MonkeyPatch) -> None:
    def deny_sync(self: httpx.HTTPTransport, request: httpx.Request) -> httpx.Response:
        raise AssertionError("Live HTTP is forbidden in tests; use httpx.MockTransport")

    async def deny_async(
        self: httpx.AsyncHTTPTransport, request: httpx.Request
    ) -> httpx.Response:
        raise AssertionError("Live HTTP is forbidden in tests; use httpx.MockTransport")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", deny_sync)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", deny_async)


@pytest.fixture(autouse=True)
def block_network_connections(monkeypatch: pytest.MonkeyPatch) -> None:
    def deny(*args: object, **kwargs: object) -> Never:
        raise AssertionError("Live network connections and DNS are forbidden in tests")

    async def deny_async(*args: object, **kwargs: object) -> Never:
        deny()

    monkeypatch.setattr(socket, "socketpair", _wakeup_socketpair)
    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket.socket, "connect_ex", deny)
    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(socket, "getaddrinfo", deny)
    monkeypatch.setattr(asyncio.BaseEventLoop, "create_connection", deny_async)
    monkeypatch.setattr(asyncio.BaseEventLoop, "create_datagram_endpoint", deny_async)
