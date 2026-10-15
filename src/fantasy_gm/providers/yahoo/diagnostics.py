"""Local, status-only probes for the human CLI. No domain or MCP integration."""

import logging
from dataclasses import dataclass
from typing import Literal

import httpx
from pydantic import SecretStr

from fantasy_gm.providers.yahoo.fantasy import LEAGUE_DISCOVERY_URL

GAME_DIAGNOSTIC_URL = "https://fantasysports.yahooapis.com/fantasy/v2/game/nhl"
EndpointLabel = Literal["A: basic game", "B: league discovery"]
ErrorCategory = Literal[
    "none",
    "unauthorized",
    "forbidden",
    "redirect",
    "not_found",
    "rate_limited",
    "server_error",
    "http_rejection",
    "transport_failure",
]
_ENDPOINTS: tuple[tuple[EndpointLabel, str], ...] = (
    ("A: basic game", GAME_DIAGNOSTIC_URL),
    ("B: league discovery", LEAGUE_DISCOVERY_URL),
)


@dataclass(frozen=True)
class YahooAPIDiagnosticResult:
    """Only predefined labels and status classifications; no provider payload."""

    endpoint: EndpointLabel
    status_code: int | None
    error_category: ErrorCategory

    def summary(self) -> str:
        """Accepted means HTTP 2xx only, not that response content was validated."""
        accepted = self.status_code is not None and 200 <= self.status_code < 300
        status = (
            str(self.status_code) if self.status_code is not None else "unavailable"
        )
        return (
            f"{self.endpoint} | HTTP {status} | "
            f"{'accepted' if accepted else 'rejected'} | {self.error_category}"
        )


def _category(status: int) -> ErrorCategory:
    if 200 <= status < 300:
        return "none"
    if 300 <= status < 400:
        return "redirect"
    if status == 401:
        return "unauthorized"
    if status == 403:
        return "forbidden"
    if status == 404:
        return "not_found"
    if status == 429:
        return "rate_limited"
    if 500 <= status < 600:
        return "server_error"
    return "http_rejection"


def diagnose_fantasy_access(
    access_token: SecretStr, *, http_client: httpx.Client
) -> tuple[YahooAPIDiagnosticResult, ...]:
    """Probe exactly A and B with one token; never read or retain response bodies.

    The human caller supplies a fresh, validated Bearer token and owns the client.
    No authentication, refresh, retry, arbitrary endpoint, or persistence here.
    Use the manual CLI's clean trust_env=False client with no logging/event hooks.
    """
    if not access_token.get_secret_value().strip():
        raise ValueError("An access token is required")
    results: list[YahooAPIDiagnosticResult] = []
    previous_log_level = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        for label, url in _ENDPOINTS:
            try:
                # Match the existing discovery request, including auth suppression.
                with http_client.stream(
                    "GET",
                    url,
                    headers={
                        "Authorization": f"Bearer {access_token.get_secret_value()}",
                        "Accept": "application/xml",
                        "Cache-Control": "no-store",
                        "Accept-Encoding": "identity",
                    },
                    auth=None,
                    timeout=10.0,
                    follow_redirects=False,
                ) as response:
                    status = response.status_code
                results.append(
                    YahooAPIDiagnosticResult(label, status, _category(status))
                )
            except httpx.RequestError:
                # Underlying messages may contain credentials; retain none of them.
                results.append(
                    YahooAPIDiagnosticResult(label, None, "transport_failure")
                )
    finally:
        logging.disable(previous_log_level)
    return tuple(results)
