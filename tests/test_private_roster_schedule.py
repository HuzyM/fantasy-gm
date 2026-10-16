"""Human private workflow with fake authorization and separate mock providers."""

import builtins
import io
import logging
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from zoneinfo import ZoneInfo

import httpx
import pytest
from pydantic import SecretStr

from tests.test_puckapi_schedule import KEY, clubs, game
from tests.test_yahoo_contract_verifier import DISCOVERY, OWNED, ROSTER, TEAMS


@pytest.mark.parametrize(
    "mistakes,cancel", [(False, False), (True, False), (False, True)]
)
def test_private_session_reuses_schedule_for_player_and_team_views(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    mistakes: bool,
    cancel: bool,
) -> None:
    import fantasy_gm.providers.puckapi as puck
    import fantasy_gm.schedule_service as schedule_service
    from fantasy_gm import roster_schedule as cli
    from fantasy_gm import verify_nhl

    monkeypatch.setattr(puck, "sleep", lambda _: None)
    monkeypatch.setattr(schedule_service, "sleep", lambda _: None)
    real_client = httpx.Client
    yahoo_calls: list[httpx.Request] = []
    puck_calls: list[httpx.Request] = []
    roster = ROSTER.replace(b"2099", b"2026").replace(
        b"</name>", b"</name><editorial_team_abbr>Tor</editorial_team_abbr>"
    )
    payloads = [DISCOVERY.replace(b"2099", b"2026"), OWNED, TEAMS, roster]

    def yahoo(request: httpx.Request) -> httpx.Response:
        yahoo_calls.append(request)
        return httpx.Response(
            200, stream=httpx.ByteStream(payloads[len(yahoo_calls) - 1])
        )

    def serve(request: httpx.Request) -> httpx.Response:
        puck_calls.append(request)
        assert "999.p." not in request.content.decode()
        assert "Invented" not in request.content.decode()
        data = (
            {"teams": clubs()}
            if request.url.path.endswith("list_teams")
            else {"games": [game()]}
        )
        return httpx.Response(200, json={"data": data})

    def client(
        *,
        transport: httpx.BaseTransport | None = None,
        trust_env: bool = False,
        **kwargs: object,
    ) -> httpx.Client:
        if type(transport) is httpx.MockTransport:
            return real_client(
                transport=transport, trust_env=False, follow_redirects=False
            )
        if transport is not None:
            transport.close()
        return real_client(transport=httpx.MockTransport(yahoo), trust_env=False)

    def puck_factory(
        cls: type[puck.PuckApiScheduleClient],
    ) -> puck.PuckApiScheduleClient:
        return cls(api_key=KEY, transport=httpx.MockTransport(serve))

    @contextmanager
    def modes() -> Iterator[None]:
        yield

    menu = iter(
        ["typo", "BACK", "2", "2", "3", "3", "4", "4", "5", "5", "6"]
        if mistakes
        else ["2"]
        if cancel
        else ["2", "3", "5", "6"]
    )
    approvals = iter(["APPROV", "APPROVE PRIVATE READ-ONLY"])
    starts = iter(["invalid", "2026-10-20", "BACK", "2026-10-20", "BACK"])
    ends = iter(["invalid", "2026-10-19", "2026-10-22", "BACK"])
    selections = iter(
        [
            "typo",
            "0",
            "1",
            "999",
            "BACK",
            "1",
            "BACK",
            "typo",
            "1",
            "BACK",
            "1",
        ]
    )
    refreshes = iter(["BACK", "REFRES", "REFRESH"])
    continuations = iter(["NEX", "NEXT"])
    cancel_selections = iter(["1", "1", "CANCEL"])
    authorizations: list[None] = []
    team_pages: Iterator[str] = iter(())

    def answer(prompt: str) -> str:
        nonlocal team_pages
        if "attest and approve" in prompt:
            return next(approvals) if mistakes else "APPROVE PRIVATE READ-ONLY"
        if "Start date" in prompt:
            return next(starts) if mistakes else "2026-10-20"
        if "End date" in prompt:
            return next(ends) if mistakes else "2026-10-22"
        if "session command" in prompt:
            command = next(menu)
            if mistakes and command == "3":
                # The 32-team selector has three pages. Revisit its final page.
                team_pages = iter(["NEXT", "NEXT", "BACK", "NEXT", "NEXT"])
            return command
        if prompt == "Type NEXT, BACK, or CANCEL: " and mistakes:
            action = next(team_pages, None)
            if action is not None:
                return action
        if "Selection number" in prompt:
            if cancel:
                return next(cancel_selections)
            return next(selections) if mistakes else "1"
        if "REFRESH to" in prompt:
            return next(refreshes) if mistakes else "REFRESH"
        if mistakes:
            return next(continuations, "NEXT")
        return "NEXT"

    def authorize(client: httpx.Client) -> SecretStr:
        authorizations.append(None)
        return SecretStr("dummy-yahoo-token")

    for stream in (sys.stdin, sys.stdout, sys.stderr):
        monkeypatch.setattr(stream, "isatty", lambda: True)
    monkeypatch.setattr(verify_nhl, "_terminal_modes", modes)
    monkeypatch.setattr(builtins, "input", answer)
    monkeypatch.setattr(cli, "_authorize", authorize)
    monkeypatch.setattr(
        puck.PuckApiScheduleClient, "from_env", classmethod(puck_factory)
    )
    monkeypatch.setattr(httpx, "Client", client)
    previous = logging.root.manager.disable
    # Load public timezone rules before denying application filesystem access.
    ZoneInfo("America/Toronto")

    def deny(*args: object, **kwargs: object) -> None:
        raise AssertionError("Unexpected persistent data access")

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "open", deny)
        patch.setattr(io, "open", deny)
        result = cli.main(["--interactive"])
    output = capsys.readouterr().out
    private, public = output.split(verify_nhl._LEAVE_PRIVATE)
    assert result == (1 if cancel else 0)
    assert public == (
        "PRIVATE_SESSION CANCELLED\n" if cancel else "PRIVATE_SESSION FINISHED\n"
    )
    assert len(yahoo_calls) == 4 and all(r.method == "GET" for r in yahoo_calls)
    assert len(puck_calls) == (2 if cancel else 4)
    assert len(authorizations) == 1
    if mistakes:
        assert "Invalid" in private
    if not cancel:
        assert private.count("CACHE_HIT") >= 2 and "CACHE_REFRESH" in private
    assert "Invented Skater" in private and "COVERAGE_UNVERIFIED" in private
    assert "not guaranteed player appearances" in " ".join(private.split())
    assert KEY not in output and "dummy-yahoo-token" not in output
    assert logging.root.manager.disable == previous


def test_help_and_nonprivate_execution_never_authorize(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from fantasy_gm import roster_schedule as cli

    def deny(*args: object, **kwargs: object) -> None:
        pytest.fail("Authorization must not be reached")

    monkeypatch.setattr(cli, "_authorize", deny)
    assert cli.main(["--help"]) == 0
    assert "--interactive" in capsys.readouterr().out
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    assert cli.main(["--interactive"]) == 1
    assert capsys.readouterr().out == "PRIVATE_SESSION FAILED\n"


@pytest.mark.parametrize("flag", ["true", "TRUE", "1", ""])
def test_yahoo_ai_policy_still_blocks_private_schedule_session(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    flag: str,
) -> None:
    from fantasy_gm import roster_schedule as cli
    from fantasy_gm import verify_nhl

    @contextmanager
    def modes() -> Iterator[None]:
        yield

    for stream in (sys.stdin, sys.stdout, sys.stderr):
        monkeypatch.setattr(stream, "isatty", lambda: True)
    monkeypatch.setattr(verify_nhl, "_terminal_modes", modes)
    monkeypatch.setattr(builtins, "input", lambda _: "APPROVE PRIVATE READ-ONLY")
    monkeypatch.setenv("YAHOO_AI_TOOLS_ENABLED", flag)

    def deny(*args: object, **kwargs: object) -> None:
        pytest.fail("Yahoo authorization must not occur with AI policy enabled")

    monkeypatch.setattr(cli, "_authorize", deny)
    assert cli.main(["--interactive"]) == 1
    assert (
        capsys.readouterr().out.split(verify_nhl._LEAVE_PRIVATE)[1]
        == "PRIVATE_SESSION FAILED\n"
    )


def test_date_prompt_honors_cancellation(monkeypatch: pytest.MonkeyPatch) -> None:
    from fantasy_gm import roster_schedule as cli
    from fantasy_gm.providers.yahoo.contract_verifier import SelectionCancelled

    monkeypatch.setattr(builtins, "input", lambda _: "CANCEL")
    with pytest.raises(SelectionCancelled):
        cli._window(2026)
