"""Manual local authorization and current-season hockey discovery, in memory only."""

import getpass
import logging
import sys
import warnings
from collections.abc import Callable
from datetime import UTC, datetime

import httpx
from pydantic import SecretStr, ValidationError

from fantasy_gm.config.yahoo import YahooOAuthConfig
from fantasy_gm.providers.yahoo.diagnostics import diagnose_fantasy_access
from fantasy_gm.providers.yahoo.fantasy import YahooFantasyClient, YahooFantasyError
from fantasy_gm.providers.yahoo.oauth import YahooOAuthClient, YahooOAuthError
from fantasy_gm.providers.yahoo.session import (
    YahooAuthorizationSession,
    YahooAuthorizationSessionError,
)


def _read_hidden_input(prompt: str) -> str:
    """Reprompt on empty input, including a Windows CRLF paste's leftover LF."""
    while True:
        value = getpass.getpass(prompt)
        if value:
            return value
        print(
            "Empty input received; paste a single line or press Ctrl+C to cancel.",
            file=sys.stderr,
        )


def run_authorization(
    config: YahooOAuthConfig,
    http_client: httpx.Client,
    *,
    read_secret: Callable[[str], str] | None = None,
    display: Callable[[str], None] = print,
    diagnose_state: bool = False,
    diagnose_api: bool = False,
) -> None:
    """Human-operated flow; injection is for synthetic tests, not persistence."""
    oauth = YahooOAuthClient(config, http_client=http_client)
    session = YahooAuthorizationSession()
    read_secret = read_secret or _read_hidden_input
    display("Use only the developer's own approved Yahoo account. Open this URL:")
    display(oauth.authorization_url(session))
    display("Use the callback page, then return here. Inputs below are hidden.")
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        code = SecretStr(read_secret("Authorization code: "))
        returned_state = read_secret("Returned state: ")
    if diagnose_state:
        # Only booleans; never reveal values, hashes, or numeric lengths.
        expected_length = len(session.authorization_parameters()["state"])
        length_matches = len(returned_state) == expected_length
        display(f"State received: {'yes' if returned_state else 'no'}")
        display(f"State length matches: {'yes' if length_matches else 'no'}")
    tokens = oauth.exchange_code(code, session=session, returned_state=returned_state)
    if tokens.token_type.casefold() != "bearer":
        raise YahooOAuthError("Unsupported Yahoo OAuth token type")
    if diagnose_api:
        display(f"UTC attempt time: {datetime.now(UTC).isoformat(timespec='seconds')}")
        for result in diagnose_fantasy_access(
            tokens.access_token, http_client=http_client
        ):
            display(result.summary())
        return
    leagues = YahooFantasyClient(http_client=http_client).list_my_hockey_leagues(
        tokens.access_token
    )
    display("Yahoo Fantasy Sports — data provided by Yahoo. Personal use, read-only.")
    if not leagues:
        display("No hockey leagues found for the current Yahoo game/season.")
    for league in leagues:
        # Escape terminal controls; emit only identifying metadata.
        display(
            f"{league.provider_league_id!r} | {league.name!r} | "
            f"sport={league.sport!r} | season={league.season!r}"
        )


def main() -> int:
    diagnose_state = sys.argv[1:] == ["--diagnose-state"]
    diagnose_api = sys.argv[1:] == ["--diagnose-api"]
    if sys.argv[1:] and not (diagnose_state or diagnose_api):
        if sys.argv[1:] == ["--help"]:
            print(
                "Usage: python -m fantasy_gm.auth [--diagnose-state | --diagnose-api] "
                "(interactive terminal only)"
            )
            return 0
        print(
            "Authorization inputs must be interactive, not command-line arguments.",
            file=sys.stderr,
        )
        return 2
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print(
            "Use an interactive terminal; redirected input/output is not allowed.",
            file=sys.stderr,
        )
        return 2
    # Avoid library request/body logging in this manual process.
    previous_log_level = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        config = YahooOAuthConfig.from_environment()
        with httpx.Client(trust_env=False) as http_client:
            if diagnose_api:
                run_authorization(config, http_client, diagnose_api=True)
            elif diagnose_state:
                run_authorization(config, http_client, diagnose_state=True)
            else:
                run_authorization(config, http_client)
    except ValidationError:
        print("Set a non-empty YAHOO_CLIENT_ID in the environment.", file=sys.stderr)
        return 2
    except (
        YahooOAuthError,
        YahooAuthorizationSessionError,
        YahooFantasyError,
    ) as error:
        print(str(error), file=sys.stderr)
        if diagnose_api:
            print(
                f"UTC failure time: {datetime.now(UTC).isoformat(timespec='seconds')}",
                file=sys.stderr,
            )
        return 1
    except (getpass.GetPassWarning, EOFError, KeyboardInterrupt):
        print(
            "Authorization cancelled or hidden input unavailable; nothing was saved.",
            file=sys.stderr,
        )
        return 1
    finally:
        logging.disable(previous_log_level)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
