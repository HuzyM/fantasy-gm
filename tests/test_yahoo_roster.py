"""Wholly invented roster envelopes; no live provider responses."""

import httpx
import pytest
from pydantic import SecretStr

from fantasy_gm.providers.yahoo.fantasy import YahooFantasyClient, YahooFantasyError
from tests.test_yahoo_contract_verifier import OWNED, ROSTER, TEAMS


def parse(body: bytes) -> object:
    from fantasy_gm.domain.team import Team
    from fantasy_gm.providers.yahoo.fantasy import parse_roster

    return parse_roster(
        body,
        team=Team(
            provider="yahoo",
            provider_league_id="999.l.1001",
            provider_team_id="999.l.1001.t.1",
            name="Invented Ice Team",
        ),
    )


def test_roster_normalizes_only_reported_identity_position_and_coverage() -> None:
    from fantasy_gm.domain.team import Team
    from fantasy_gm.providers.yahoo.fantasy import parse_roster

    team = Team(
        provider="yahoo",
        provider_league_id="999.l.1001",
        provider_team_id="999.l.1001.t.1",
        name="Invented Ice Team",
    )
    roster = parse_roster(ROSTER, team=team)
    assert roster.team == team and roster.requested_date is None
    assert (
        roster.coverage.date is not None
        and roster.coverage.date.isoformat() == "2099-10-15"
    )
    assert roster.returned_count == 2
    assert [entry.provider_player_id for entry in roster.entries] == [
        "999.p.801",
        "999.p.802",
    ]
    assert roster.entries[1].selected_position == "IR+"
    assert roster.entries[0].eligible_positions == ("C", "LW")
    assert not hasattr(roster, "complete") and not hasattr(roster, "capacity_valid")


@pytest.mark.parametrize(
    "key", ["999.l.1001.t.2", "999.l.1002.t.1", "999.l.1001.t.1?fake=x"]
)
def test_roster_selection_must_be_explicitly_owned(key: str) -> None:
    calls: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(
            200, stream=httpx.ByteStream([OWNED, TEAMS][len(calls) - 1])
        )

    with httpx.Client(transport=httpx.MockTransport(handle), trust_env=False) as client:
        with pytest.raises(YahooFantasyError):
            YahooFantasyClient(http_client=client).get_owned_team_roster(
                SecretStr("fake-roster-token"), league_key="999.l.1001", team_key=key
            )
    assert not any("/roster" in request.url.path for request in calls)


def test_owned_roster_read_needs_no_settings_and_uses_one_roster_get() -> None:
    calls: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(
            200, stream=httpx.ByteStream([OWNED, TEAMS, ROSTER][len(calls) - 1])
        )

    with httpx.Client(transport=httpx.MockTransport(handle), trust_env=False) as client:
        result = YahooFantasyClient(http_client=client).get_owned_team_roster(
            SecretStr("fake-roster-token"),
            league_key="999.l.1001",
            team_key="999.l.1001.t.1",
        )
    assert len(result.entries) == 2 and len(calls) == 3
    assert sum("/roster" in request.url.path for request in calls) == 1
    assert not any("settings" in request.url.path for request in calls)


@pytest.mark.parametrize("scoring", ["unknown", "malformed"])
def test_verifier_normalizes_roster_despite_unresolved_scoring_and_slots(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], scoring: str
) -> None:
    from tests.test_verifier_reporting import run_cli
    from tests.test_yahoo_contract_verifier import PAYLOADS, SETTINGS

    payloads = PAYLOADS.copy()
    payloads[1] = SETTINGS.replace(
        b"<count>2</count>", b"<count>2</count><synthetic_slot_extension/>"
    )
    if scoring == "unknown":
        payloads[1] = payloads[1].replace(
            b"</settings>", b"<synthetic_rule/></settings>"
        )
    else:
        payloads[1] = payloads[1].replace(b"<value>-2.50</value>", b"")
    code, calls, _ = run_cli(monkeypatch, payloads)
    output = capsys.readouterr().out
    assert code == 1 and len(calls) == 5
    assert "ROSTER_STRUCTURE PASS" in output and "ROSTER_NORMALIZATION PASS" in output
    assert "ROSTER_SLOT_CAPACITY UNVERIFIED" in output
    assert "HUMAN_ROSTER_COMPLETE UNVERIFIED" in output
    assert f"SESSION {'FAIL' if scoring == 'malformed' else 'UNVERIFIED'}" in output


def test_opaque_position_codes_are_not_trimmed_or_mapped() -> None:
    from fantasy_gm.domain.roster import Roster

    result = parse(
        ROSTER.replace(b"<position>C</position>", b"<position> UNKNOWN-X </position>")
    )
    assert isinstance(result, Roster)
    assert result.entries[0].selected_position == " UNKNOWN-X "
    assert result.entries[0].eligible_positions == (" UNKNOWN-X ", "LW")


@pytest.mark.parametrize(
    "mutation",
    [
        "team",
        "id_missing",
        "id_mismatch",
        "name_missing",
        "duplicate_player",
        "player_game",
        "namespace",
        "field_namespace",
        "field_duplicate",
        "count",
        "missing_collection",
        "absent_collection",
        "team_id_attribute",
        "malformed",
        "dtd",
    ],
)
def test_malformed_roster_identity_and_envelope_reject_without_private_errors(
    mutation: str,
) -> None:
    import re
    import traceback

    body = {
        "team": ROSTER.replace(b"999.l.1001.t.1", b"999.l.1001.t.2"),
        "id_missing": ROSTER.replace(b"<player_id>802</player_id>", b""),
        "id_mismatch": ROSTER.replace(
            b"<player_id>802</player_id>", b"<player_id>803</player_id>"
        ),
        "name_missing": ROSTER.replace(b"<full>Invented Reserve</full>", b""),
        "duplicate_player": ROSTER.replace(b"802", b"801"),
        "player_game": ROSTER.replace(b"999.p.802", b"998.p.802"),
        "namespace": ROSTER.replace(
            b"http://fantasysports.yahooapis.com/fantasy/v2/base.rng", b"urn:synthetic"
        ),
        "field_namespace": ROSTER.replace(
            b"<player_id>", b'<player_id xmlns="urn:synthetic">'
        ),
        "field_duplicate": ROSTER.replace(
            b"<player_id>802</player_id>",
            b"<player_id>802</player_id><player_id>802</player_id>",
        ),
        "count": ROSTER.replace(b'players count="2"', b'players count="3"'),
        "missing_collection": ROSTER.replace(b"<players", b"<unknown").replace(
            b"</players>", b"</unknown>"
        ),
        "absent_collection": re.sub(rb"<players.*?</players>", b"", ROSTER, flags=re.S),
        "team_id_attribute": ROSTER.replace(
            b"</team_key>", b'</team_key><team_id fake="private">1</team_id>'
        ),
        "malformed": b"<fake-invalid-xml",
        "dtd": b'<!DOCTYPE fantasy_content [<!ENTITY x "fake">]>' + ROSTER,
    }[mutation]
    with pytest.raises(YahooFantasyError) as error:
        parse(body)
    output = "".join(traceback.format_exception(error.value))
    assert not any(
        value in output
        for value in ("Invented", "999.l.", "999.p.", "2099", "fake-invalid")
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "roster_extra",
        "roster_attribute",
        "eligible_attribute",
        "eligible_namespace",
        "selected_extra",
        "selected_attribute",
    ],
)
def test_unsupported_optional_structures_preserve_independent_player_information(
    mutation: str,
) -> None:
    from fantasy_gm.domain.roster import Roster

    body = {
        "roster_extra": ROSTER.replace(b"</roster>", b"<synthetic_rule/></roster>"),
        "roster_attribute": ROSTER.replace(b"<roster>", b'<roster fake="private">'),
        "eligible_attribute": ROSTER.replace(
            b"<eligible_positions>", b'<eligible_positions fake="private">'
        ),
        "eligible_namespace": ROSTER.replace(
            b"<eligible_positions>", b'<eligible_positions xmlns="urn:synthetic">'
        ),
        "selected_extra": ROSTER.replace(
            b"</selected_position>", b"<synthetic_rule/></selected_position>"
        ),
        "selected_attribute": ROSTER.replace(
            b"<selected_position>", b'<selected_position fake="private">'
        ),
    }[mutation]
    result = parse(body)
    assert isinstance(result, Roster) and result.context_unverified
    assert len(result.entries) == 2
    assert result.entries[0].provider_player_id == "999.p.801"
    assert result.entries[0].selected_position == "C"
    if mutation.startswith("eligible"):
        assert result.entries[0].eligible_positions is None
    else:
        assert result.entries[0].eligible_positions == ("C", "LW")


@pytest.mark.parametrize("kind", ["missing", "empty", "unknown"])
def test_optional_positions_distinguish_absence_empty_and_opaque_values(
    kind: str,
) -> None:
    import re

    from fantasy_gm.domain.roster import Roster

    body = ROSTER
    if kind == "missing":
        body = re.sub(
            rb"<eligible_positions>.*?</eligible_positions>", b"", body, flags=re.S
        )
        body = re.sub(
            rb"<selected_position>.*?</selected_position>", b"", body, flags=re.S
        )
    elif kind == "empty":
        body = re.sub(
            rb"<eligible_positions>.*?</eligible_positions>",
            b"<eligible_positions/>",
            body,
            flags=re.S,
        )
        body = re.sub(
            rb"<selected_position>.*?</selected_position>",
            b"<selected_position/>",
            body,
            flags=re.S,
        )
    else:
        body = body.replace(
            b"<position>C</position>", b"<position>UNMAPPED-X</position>"
        )
    result = parse(body)
    assert isinstance(result, Roster)
    entry = result.entries[0]
    if kind == "missing":
        assert entry.eligible_positions is None and entry.selected_position is None
        assert entry.selected_coverage is None
    elif kind == "empty":
        assert entry.eligible_positions == () and entry.selected_position is None
    else:
        assert entry.selected_position == "UNMAPPED-X"


@pytest.mark.parametrize(
    "kind",
    [
        "missing_dates",
        "missing_coverage",
        "opaque_coverage",
        "missing_count",
        "empty_players",
    ],
)
def test_unknown_coverage_and_counts_do_not_infer_dates_or_completeness(
    kind: str,
) -> None:
    import re

    from fantasy_gm.domain.roster import Roster

    body = ROSTER
    if kind == "missing_dates":
        body = body.replace(b"<date>2099-10-15</date>", b"")
    elif kind == "missing_coverage":
        body = re.sub(
            rb"<coverage_type>.*?</coverage_type>|<date>.*?</date>", b"", body
        )
    elif kind == "opaque_coverage":
        body = body.replace(
            b"<coverage_type>date</coverage_type>",
            b"<coverage_type>synthetic-period</coverage_type><week>opaque-week</week>",
        )
    elif kind == "missing_count":
        body = body.replace(b'players count="2"', b"players")
    else:
        body = re.sub(
            rb'<players count="2">.*?</players>',
            b'<players count="0"/>',
            body,
            flags=re.S,
        )
    result = parse(body)
    assert isinstance(result, Roster) and result.requested_date is None
    if kind in ("missing_dates", "missing_coverage"):
        assert result.coverage.date is None
    if kind == "opaque_coverage":
        assert (
            result.coverage.kind == "synthetic-period"
            and result.coverage.week == "opaque-week"
        )
    if kind == "missing_count":
        assert result.returned_count is None
    if kind == "empty_players":
        assert not result.entries and result.returned_count == 0
    assert not hasattr(result, "complete")


@pytest.mark.parametrize(
    "kind", ["unauthorized", "gzip", "oversized", "redirect", "transport"]
)
def test_roster_get_reuses_fixed_transport_and_sanitizes_failures(kind: str) -> None:
    from fantasy_gm.providers.yahoo.fantasy import MAX_LEAGUE_RESPONSE_BYTES

    calls: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        assert request.method == "GET" and request.url.scheme == "https"
        assert request.url.host == "fantasysports.yahooapis.com"
        assert request.headers["cache-control"] == "no-store"
        assert request.headers["accept-encoding"] == "identity"
        if len(calls) < 3:
            return httpx.Response(
                200, stream=httpx.ByteStream([OWNED, TEAMS][len(calls) - 1])
            )
        if kind == "transport":
            raise httpx.ReadTimeout("fake-private-value", request=request)
        return httpx.Response(
            {"unauthorized": 401, "redirect": 302}.get(kind, 200),
            headers={
                "Location": "https://example.test/private",
                "Content-Encoding": "gzip" if kind == "gzip" else "identity",
            },
            stream=httpx.ByteStream(
                b"x" * (MAX_LEAGUE_RESPONSE_BYTES + 1)
                if kind == "oversized"
                else b"fake-private-value"
            ),
        )

    with httpx.Client(
        transport=httpx.MockTransport(handle), trust_env=False, follow_redirects=True
    ) as client:
        with pytest.raises(YahooFantasyError) as error:
            YahooFantasyClient(http_client=client).get_owned_team_roster(
                SecretStr("fake-roster-token"),
                league_key="999.l.1001",
                team_key="999.l.1001.t.1",
            )
    assert len(calls) == 3 and "fake-private-value" not in str(error.value)


def test_roster_read_does_not_write_log_or_retain_private_data(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    import builtins
    import logging

    calls: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        logging.critical("fake-private-body-and-token")
        return httpx.Response(
            200, stream=httpx.ByteStream([OWNED, TEAMS, ROSTER][len(calls) - 1])
        )

    def deny(*args: object, **kwargs: object) -> None:
        raise AssertionError("Unexpected persistence")

    with httpx.Client(transport=httpx.MockTransport(handle), trust_env=False) as client:
        provider = YahooFantasyClient(http_client=client)
        with monkeypatch.context() as patch:
            patch.setattr(builtins, "open", deny)
            provider.get_owned_team_roster(
                SecretStr("fake-roster-token"),
                league_key="999.l.1001",
                team_key="999.l.1001.t.1",
            )
        assert set(vars(provider)) == {"_http_client"}
    assert not caplog.records
