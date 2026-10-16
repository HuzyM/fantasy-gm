"""Invented NHL contracts only. These fixtures are not captured Yahoo responses."""

import builtins
import io
import logging
import os
from pathlib import Path

import httpx
import pytest
from pydantic import SecretStr

NS = "http://fantasysports.yahooapis.com/fantasy/v2/base.rng"


def xml(body: str) -> bytes:
    return f'<fantasy_content xmlns="{NS}">{body}</fantasy_content>'.encode()


DISCOVERY = xml("""<users count="1"><user><games count="1"><game>
<game_key>999</game_key><code>nhl</code><season>2099</season><leagues count="1">
<league><league_key>999.l.1001</league_key><name>Invented Ice League</name>
<game_code>nhl</game_code><season>2099</season></league>
</leagues></game></games></user></users>""")
SETTINGS = xml("""<league><league_key>999.l.1001</league_key><game_code>nhl</game_code>
<num_teams>1</num_teams><scoring_type>invented-points</scoring_type><settings>
<scoring_type>invented-points</scoring_type><uses_fractional_points>1</uses_fractional_points>
<uses_negative_points>1</uses_negative_points><roster_positions>
<roster_position><position>C</position><position_type>P</position_type><count>1</count>
</roster_position><roster_position><position>BN</position><count>2</count></roster_position>
<roster_position><position>IR+</position><count>1</count></roster_position>
</roster_positions><stat_categories><stats>
<stat><stat_id>901</stat_id><enabled>1</enabled><name>Invented Goals</name>
<position_type>P</position_type><stat_position_types><stat_position_type>
<position_type>P</position_type></stat_position_type><stat_position_type>
<position_type>G</position_type><is_only_display_stat>1</is_only_display_stat>
</stat_position_type></stat_position_types></stat>
<stat><stat_id>902</stat_id><enabled>1</enabled><name>Invented Penalties</name></stat>
<stat><stat_id>903</stat_id><enabled>1</enabled><name>Invented Shutouts</name></stat>
<stat><stat_id>904</stat_id><enabled>1</enabled><name>Invented Display</name>
<is_only_display_stat>1</is_only_display_stat></stat>
</stats></stat_categories><stat_modifiers><stats>
<stat><stat_id>901</stat_id><value>0.12345678901234567890123456789</value></stat>
<stat><stat_id>902</stat_id><value>-2.50</value></stat>
<stat><stat_id>903</stat_id><value>0</value></stat>
</stats></stat_modifiers></settings></league>""")
TEAM = """<team><team_key>999.l.1001.t.1</team_key><team_id>1</team_id>
<name>Invented Ice Team</name></team>"""
OWNED = xml(f"""<users count="1"><user><games count="1"><game>
<game_key>999</game_key><teams count="1">{TEAM}</teams>
</game></games></user></users>""")
TEAMS = xml(f"""<league><league_key>999.l.1001</league_key>
<teams count="1">{TEAM}</teams></league>""")
ROSTER = xml("""<team><team_key>999.l.1001.t.1</team_key><roster>
<coverage_type>date</coverage_type><date>2099-10-15</date><is_editable>1</is_editable>
<players count="2"><player><player_key>999.p.801</player_key><player_id>801</player_id>
<name><full>Invented Skater</full></name><eligible_positions><position>C</position>
<position>LW</position></eligible_positions><selected_position><coverage_type>date</coverage_type>
<date>2099-10-15</date><position>C</position></selected_position></player>
<player><player_key>999.p.802</player_key><player_id>802</player_id>
<name><full>Invented Reserve</full></name><eligible_positions><position>G</position>
</eligible_positions><selected_position><coverage_type>date</coverage_type>
<date>2099-10-15</date><position>IR+</position></selected_position></player>
</players></roster></team>""")
PAYLOADS = [DISCOVERY, SETTINGS, OWNED, TEAMS, ROSTER]


def run_fake(
    payloads: list[bytes],
    *,
    human: str = "PASS",
    choices: int | None = 0,
) -> tuple[object, list[httpx.Request], list[str]]:
    # Import inside the test call so the initial absent implementation fails a test.
    from fantasy_gm.providers.yahoo.contract_verifier import (
        Report,
        Status,
        verify_contracts,
    )

    calls: list[httpx.Request] = []
    private: list[str] = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, stream=httpx.ByteStream(payloads[len(calls) - 1]))

    def choose(title: str, options: tuple[str, ...]) -> int | None:
        private.extend(options)
        return choices

    def confirm(check: object, details: tuple[str, ...]) -> Status:
        private.extend(details)
        return Status(human)

    report = Report()
    with httpx.Client(transport=httpx.MockTransport(handle), trust_env=False) as client:
        verify_contracts(
            SecretStr("fake-contract-access-token"),
            http_client=client,
            report=report,
            choose=choose,
            confirm=confirm,
        )
    return report, calls, private


def lines(report: object) -> tuple[str, ...]:
    from fantasy_gm.providers.yahoo.contract_verifier import Report

    assert isinstance(report, Report)
    return report.lines()


def test_valid_structures_preserve_exact_values_and_separate_human_evidence() -> None:
    report, calls, private = run_fake(PAYLOADS)
    assert len(calls) == 5
    assert [request.url.path for request in calls] == [
        "/fantasy/v2/users;use_login=1/games;game_keys=nhl/leagues",
        "/fantasy/v2/league/999.l.1001/settings",
        "/fantasy/v2/users;use_login=1/games;game_keys=999/teams",
        "/fantasy/v2/league/999.l.1001/teams",
        "/fantasy/v2/team/999.l.1001.t.1/roster",
    ]
    for request in calls:
        assert request.method == "GET" and not request.content
        assert request.url.scheme == "https"
        assert request.url.host == "fantasysports.yahooapis.com"
        assert request.headers["authorization"] == "Bearer fake-contract-access-token"
        assert request.headers["accept-encoding"] == "identity"
        assert request.headers["cache-control"] == "no-store"
        assert request.extensions["timeout"] == dict.fromkeys(
            ("connect", "read", "write", "pool"), 10.0
        )
    view = "\n".join(private)
    assert "0.12345678901234567890123456789" in view
    assert "-2.50" in view and "weight=0" in view
    assert "weight=MISSING" in view and "IR+" in view
    assert "scope='G'" in view and "display_only='1'" in view
    output = "\n".join(lines(report))
    assert "SCORING_STRUCTURE PASS" in output
    assert "HUMAN_SCORING_COMPLETE PASS" in output
    assert "ROSTER_COVERAGE PASS" in output
    assert "HUMAN_ROSTER_COMPLETE PASS" in output
    assert not any(
        s in output + repr(vars(report))
        for s in ("Invented", "999", "801", "2099", "fake-contract", "0.123456")
    )


@pytest.mark.parametrize("human", ["FAIL", "UNVERIFIED"])
def test_human_comparison_never_automatically_passes(human: str) -> None:
    report, calls, _ = run_fake(PAYLOADS, human=human)
    assert len(calls) == (4 if human == "UNVERIFIED" else 2)
    assert f"HUMAN_POINTS_FORMAT {human}" in lines(report)
    assert (
        f"OWNED_TEAM_MEMBERSHIP {'PASS' if human == 'UNVERIFIED' else 'UNVERIFIED'}"
        in lines(report)
    )


@pytest.mark.parametrize(
    ("index", "old", "new", "check", "status"),
    [
        (1, b"<settings>", b"<settings><settings/>", "SETTINGS_STRUCTURE", "FAIL"),
        (1, b"<value>-2.50</value>", b"", "MODIFIER_VALUES", "FAIL"),
        (1, b"<value>-2.50</value>", b"<value>NaN</value>", "MODIFIER_VALUES", "FAIL"),
        (
            1,
            b"<value>-2.50</value>",
            b"<value>Infinity</value>",
            "MODIFIER_VALUES",
            "FAIL",
        ),
        (
            1,
            b"<value>-2.50</value>",
            b"<value>1e2</value>",
            "MODIFIER_VALUES",
            "UNVERIFIED",
        ),
        (
            1,
            b"<stat_id>902</stat_id><value>",
            b"<stat_id>909</stat_id><value>",
            "SCORING_STRUCTURE",
            "FAIL",
        ),
        (
            1,
            b"</stat_modifiers>",
            b"<bonuses/></stat_modifiers>",
            "SCORING_STRUCTURE",
            "UNVERIFIED",
        ),
        (1, b"<count>2</count>", b"<count>-1</count>", "ROSTER_SLOTS", "FAIL"),
        (2, b"999.l.1001.t.1", b"999.l.9999.t.1", "OWNED_TEAM_MEMBERSHIP", "FAIL"),
        (3, b'teams count="1"', b'teams count="2"', "LEAGUE_TEAMS_STRUCTURE", "FAIL"),
        (4, b'players count="2"', b'players count="1"', "ROSTER_STRUCTURE", "FAIL"),
        (
            4,
            b"<position>IR+</position>",
            b"<position>UNKNOWN-X</position>",
            "PLAYER_POSITIONS",
            "UNVERIFIED",
        ),
        (4, b"<player_id>802</player_id>", b"", "ROSTER_NORMALIZATION", "FAIL"),
        (4, b"2099-10-15", b"2099-99-99", "ROSTER_NORMALIZATION", "FAIL"),
        (
            1,
            b"</settings>",
            b"<scoring_bonus>2</scoring_bonus></settings>",
            "SCORING_STRUCTURE",
            "UNVERIFIED",
        ),
        (
            1,
            b"<name>Invented Goals</name>",
            b"<name>Invented Goals</name><threshold>2</threshold>",
            "SCORING_STRUCTURE",
            "UNVERIFIED",
        ),
        (
            1,
            b"<stat_categories>",
            b"<stat_categories><unknown/>",
            "SCORING_STRUCTURE",
            "UNVERIFIED",
        ),
    ],
)
def test_rejects_bad_or_unsupported_contract_and_stops(
    index: int, old: bytes, new: bytes, check: str, status: str
) -> None:
    payloads = PAYLOADS.copy()
    assert old in payloads[index]
    payloads[index] = payloads[index].replace(old, new)
    report, calls, _ = run_fake(payloads)
    independent = index == 1 and check in {
        "SCORING_STRUCTURE",
        "MODIFIER_VALUES",
        "STAT_APPLICABILITY",
    }
    assert len(calls) == (5 if independent or check == "ROSTER_SLOTS" else index + 1)
    assert f"{check} {status}" in lines(report)
    assert f"HUMAN_ROSTER_COMPLETE {'PASS' if independent else 'UNVERIFIED'}" in lines(
        report
    )


def test_missing_date_is_not_invented_and_reserve_completeness_is_human() -> None:
    payloads = PAYLOADS.copy()
    payloads[4] = ROSTER.replace(b"<date>2099-10-15</date>", b"")
    report, _, private = run_fake(payloads)
    assert "ROSTER_COVERAGE UNVERIFIED" in lines(report)
    assert "HUMAN_ROSTER_COVERAGE UNVERIFIED" in lines(report)
    assert "HUMAN_ROSTER_COMPLETE PASS" in lines(report)
    assert "reported_date=MISSING" in "\n".join(private)


def test_count_is_evidence_not_proof_of_complete_roster() -> None:
    report, _, _ = run_fake(PAYLOADS)
    assert "ROSTER_RETURNED_COUNT PASS" in lines(report)
    assert "HUMAN_ROSTER_COMPLETE PASS" in lines(report)


def test_selection_cancel_stops_before_requesting_settings() -> None:
    report, calls, _ = run_fake(PAYLOADS, choices=None)
    assert len(calls) == 1
    assert "SETTINGS_STRUCTURE UNVERIFIED" in lines(report)


def test_no_file_writes_or_private_logging_or_shareable_payload(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    def deny(*args: object, **kwargs: object) -> None:
        raise AssertionError("Verifier attempted filesystem access")

    monkeypatch.chdir(tmp_path)
    with caplog.at_level(logging.DEBUG), monkeypatch.context() as guard:
        guard.setattr(builtins, "open", deny)
        guard.setattr(io, "open", deny)
        guard.setattr(os, "open", deny)
        report, _, _ = run_fake(PAYLOADS)
    assert not caplog.records
    assert not capsys.readouterr().out
    assert list(tmp_path.iterdir()) == []
    assert all(
        line.split()[1] in {"PASS", "FAIL", "UNVERIFIED"} for line in lines(report)
    )


def test_terminal_controls_in_private_fields_are_escaped() -> None:
    payloads = PAYLOADS.copy()
    payloads[0] = DISCOVERY.replace(b"Invented Ice League", b"Invented&#10;FAKE STATUS")
    _, _, private = run_fake(payloads)
    assert not any("\nFAKE STATUS" in row for row in private)


@pytest.mark.parametrize("bad", [b"<!DOCTYPE x><x/>", b"<broken", b"\xff"])
def test_malformed_xml_is_status_only(bad: bytes) -> None:
    report, calls, _ = run_fake([bad])
    assert len(calls) == 1
    assert "LEAGUE_DISCOVERY FAIL" in lines(report)


def test_human_can_reject_missing_coverage_without_being_ignored() -> None:
    from fantasy_gm.providers.yahoo.contract_verifier import (
        Check,
        Report,
        Status,
        verify_contracts,
    )

    payloads = PAYLOADS.copy()
    payloads[4] = ROSTER.replace(b"<date>2099-10-15</date>", b"")
    calls: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, stream=httpx.ByteStream(payloads[len(calls) - 1]))

    report = Report()
    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        verify_contracts(
            SecretStr("fake-token"),
            http_client=client,
            report=report,
            choose=lambda title, choices: 0,
            confirm=lambda check, details: (
                Status.FAIL if check is Check.HUMAN_ROSTER_COVERAGE else Status.PASS
            ),
        )
    assert "HUMAN_ROSTER_COVERAGE FAIL" in report.lines()
    assert "HUMAN_ROSTER_COMPLETE UNVERIFIED" in report.lines()


@pytest.mark.parametrize(
    "kind", ["redirect", "rejected", "compressed", "oversized", "transport"]
)
def test_transport_rejection_stops_without_private_errors_or_retries(kind: str) -> None:
    from fantasy_gm.providers.yahoo.contract_verifier import (
        Report,
        Status,
        verify_contracts,
    )
    from fantasy_gm.providers.yahoo.fantasy import MAX_LEAGUE_RESPONSE_BYTES

    calls: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if kind == "transport":
            raise httpx.ConnectError("fake-sensitive-body-and-key", request=request)
        status = {"redirect": 302, "rejected": 403}.get(kind, 200)
        return httpx.Response(
            status,
            headers={
                "Location": "https://example.test/fake-secret",
                "Content-Encoding": "gzip" if kind == "compressed" else "identity",
            },
            stream=httpx.ByteStream(
                b"x" * (MAX_LEAGUE_RESPONSE_BYTES + 1)
                if kind == "oversized"
                else b"fake-sensitive-body"
            ),
        )

    report = Report()
    with httpx.Client(
        transport=httpx.MockTransport(handle), follow_redirects=True
    ) as client:
        verify_contracts(
            SecretStr("fake-token"),
            http_client=client,
            report=report,
            choose=lambda title, choices: 0,
            confirm=lambda check, details: Status.PASS,
        )
    assert len(calls) == 1
    assert "LEAGUE_DISCOVERY FAIL" in report.lines()
    assert "fake-sensitive" not in repr(report) + "\n".join(report.lines())


@pytest.mark.parametrize(
    "path",
    [
        "https://example.test/",
        "league/999.l.1001/transactions",
        "league/../settings",
        "league/999.l.1001/settings?secret=x",
        "team/999.l.1001.t.1/roster;date=2099-10-15",
    ],
)
def test_only_fixed_verified_read_paths_can_reach_transport(path: str) -> None:
    from fantasy_gm.providers.yahoo.fantasy import YahooFantasyError, _fetch_xml

    with httpx.Client() as client:
        with pytest.raises(YahooFantasyError, match="Unsupported"):
            _fetch_xml(client, SecretStr("fake-token"), path)


def test_unhandled_modifier_attribute_cannot_be_silently_ignored() -> None:
    payloads = PAYLOADS.copy()
    payloads[1] = SETTINGS.replace(
        b"<value>-2.50</value>", b'<value scale="100">-2.50</value>'
    )
    report, calls, _ = run_fake(payloads)
    assert len(calls) == 5
    assert "SCORING_STRUCTURE UNVERIFIED" in lines(report)


@pytest.mark.parametrize("encoding", ["utf-16-le", "utf-16-be", "utf-32-le"])
def test_alternate_xml_encoding_cannot_bypass_dtd_rejection(encoding: str) -> None:
    from fantasy_gm.providers.yahoo.fantasy import YahooFantasyError, parse_leagues

    text = (
        '<!DOCTYPE fantasy_content [<!ENTITY x "Invented entity">]>'
        + DISCOVERY.decode().replace("Invented Ice League", "&x;")
    )
    with pytest.raises(YahooFantasyError, match="Malformed"):
        parse_leagues(text.encode(encoding))


def test_validated_scoring_collection_counts_are_supported() -> None:
    payloads = PAYLOADS.copy()
    payloads[1] = (
        SETTINGS.replace(
            b"<stat_categories><stats>", b'<stat_categories><stats count="4">'
        )
        .replace(b"<stat_modifiers><stats>", b'<stat_modifiers><stats count="3">')
        .replace(b"<stat_position_types>", b'<stat_position_types count="2">')
    )
    report, calls, _ = run_fake(payloads)
    assert len(calls) == 5
    assert "SCORING_STRUCTURE PASS" in lines(report)
    assert "STAT_APPLICABILITY PASS" in lines(report)


def test_modifier_values_cannot_pass_after_partial_collection_validation() -> None:
    payloads = PAYLOADS.copy()
    payloads[1] = SETTINGS.replace(
        b"<value>0</value>", b'<value scale="100">NaN</value>'
    )
    report, _, _ = run_fake(payloads)
    assert "SCORING_STRUCTURE UNVERIFIED" in lines(report)
    assert "MODIFIER_VALUES UNVERIFIED" in lines(report)


def test_coverage_cannot_pass_before_every_player_is_validated() -> None:
    payloads = PAYLOADS.copy()
    payloads[4] = ROSTER.replace(b"<player_id>802</player_id>", b"")
    report, _, _ = run_fake(payloads)
    assert "ROSTER_NORMALIZATION FAIL" in lines(report)
    assert "ROSTER_COVERAGE UNVERIFIED" in lines(report)


@pytest.mark.parametrize("kind", ["slot", "assignment", "pagination"])
def test_unhandled_critical_roster_extensions_do_not_pass(kind: str) -> None:
    payloads = PAYLOADS.copy()
    if kind == "slot":
        payloads[1] = SETTINGS.replace(
            b"<count>1</count>", b"<count>1</count><slot_weight>0.5</slot_weight>", 1
        )
        expected = "ROSTER_SLOTS UNVERIFIED"
    elif kind == "assignment":
        payloads[4] = ROSTER.replace(
            b"<selected_position>",
            b'<selected_position assignment_mode="future">'
            b"<assignment_weight>0.5</assignment_weight>",
            1,
        )
        expected = "ROSTER_NORMALIZATION UNVERIFIED"
    else:
        payloads[4] = ROSTER.replace(
            b'<players count="2">', b'<players count="2" start="25">'
        )
        expected = "ROSTER_STRUCTURE UNVERIFIED"
    report, calls, _ = run_fake(payloads)
    assert expected in lines(report)
    assert len(calls) == 5
    assert "HUMAN_ROSTER_COMPLETE UNVERIFIED" in lines(report)


@pytest.mark.parametrize("selected", [False, True])
def test_mixed_week_and_date_coverage_is_preserved_but_unverified(
    selected: bool,
) -> None:
    payloads = PAYLOADS.copy()
    marker = b"<selected_position>" if selected else b"<roster>"
    payloads[4] = ROSTER.replace(marker, marker + b"<week>88</week>", 1)
    report, _, private = run_fake(payloads)
    assert "ROSTER_COVERAGE UNVERIFIED" in lines(report)
    assert "HUMAN_ROSTER_COVERAGE UNVERIFIED" in lines(report)
    assert "week='88'" in "\n".join(private)
