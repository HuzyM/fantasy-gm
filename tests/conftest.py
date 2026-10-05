"""Keep the entire test suite independent of credentials and live HTTP."""

import httpx
import pytest


@pytest.fixture(autouse=True)
def isolate_yahoo_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("YAHOO_CLIENT_ID", "YAHOO_CLIENT_SECRET", "YAHOO_REDIRECT_URI"):
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
