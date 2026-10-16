"""Invented player identities/metadata; no recorded Yahoo response data."""

import pytest

from fantasy_gm.domain.roster import Roster
from fantasy_gm.domain.team import Team
from fantasy_gm.providers.yahoo.fantasy import parse_roster
from tests.test_yahoo_contract_verifier import ROSTER


def roster_with(metadata: bytes) -> Roster:
    return parse_roster(
        ROSTER.replace(b"</name>", b"</name>" + metadata, 1),
        team=Team(
            provider="yahoo",
            provider_league_id="999.l.1001",
            provider_team_id="999.l.1001.t.1",
            name="Invented team",
        ),
    )


@pytest.mark.parametrize(
    "value,expected",
    [("Tor", "TOR"), ("CHI", "CHI"), ("Was", "WSH"), ("Ari", "ARI"), ("SJ", "SJ")],
)
def test_reported_team_metadata_is_retained_without_guessing(
    value: str, expected: str
) -> None:
    roster = roster_with(f"<editorial_team_abbr>{value}</editorial_team_abbr>".encode())
    assert roster.entries[0].professional_team_code == expected
    assert not roster.entries[0].professional_team_unverified
    assert roster.entries[1].professional_team_code is None


@pytest.mark.parametrize(
    "metadata",
    [
        b"<editorial_team_abbr/>",
        b"<editorial_team_abbr>TOR</editorial_team_abbr><editorial_team_abbr>BOS</editorial_team_abbr>",
        b'<editorial_team_abbr xmlns="urn:wrong">TOR</editorial_team_abbr>',
        b"<editorial_team_abbr><value>TOR</value></editorial_team_abbr>",
        b'<editorial_team_abbr invalid="yes">TOR</editorial_team_abbr>',
        b"<editorial_team_abbr>TOR</editorial_team_abbr><editorial_team_key>nba.t.1</editorial_team_key>",
        b"<editorial_team_abbr>LONG-CODE</editorial_team_abbr>",
    ],
)
def test_bad_or_conflicting_optional_affiliation_does_not_erase_roster(
    metadata: bytes,
) -> None:
    roster = roster_with(metadata)
    assert len(roster.entries) == 2
    assert roster.entries[0].professional_team_code is None
    assert roster.entries[0].professional_team_unverified
    assert roster.context_unverified


def test_missing_affiliation_stays_missing() -> None:
    roster = roster_with(b"")
    assert roster.entries[0].professional_team_code is None
    assert not roster.entries[0].professional_team_unverified


@pytest.mark.parametrize(
    "second_code,second_key", [("BOS", "nhl.t.1"), ("TOR", "nhl.t.2")]
)
def test_conflicting_cross_player_affiliation_identities_stay_unverified(
    second_code: str, second_key: str
) -> None:
    payload = ROSTER.replace(
        b"</name>",
        b"</name><editorial_team_abbr>TOR</editorial_team_abbr><editorial_team_key>nhl.t.1</editorial_team_key>",
        1,
    )
    payload = payload.replace(
        b"<name><full>Invented Reserve</full></name>",
        (
            "<name><full>Invented Reserve</full></name>"
            f"<editorial_team_abbr>{second_code}</editorial_team_abbr>"
            f"<editorial_team_key>{second_key}</editorial_team_key>"
        ).encode(),
    )
    roster = parse_roster(
        payload,
        team=Team(
            provider="yahoo",
            provider_league_id="999.l.1001",
            provider_team_id="999.l.1001.t.1",
            name="Invented team",
        ),
    )
    assert all(
        p.professional_team_code is None and p.professional_team_unverified
        for p in roster.entries
    )
    assert roster.context_unverified
