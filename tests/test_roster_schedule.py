"""Private joins use only fabricated roster entries and public mock schedules."""

from datetime import date
from zoneinfo import ZoneInfo

import pytest

from fantasy_gm.domain.roster import RosterEntry
from tests.test_puckapi_schedule import collect, game
from tests.test_roster_affiliation import roster_with


@pytest.mark.parametrize(
    "metadata,status",
    [
        (b"", "MISSING_AFFILIATION"),
        (b"<editorial_team_key>nhl.t.1</editorial_team_key>", "AFFILIATION_UNVERIFIED"),
        (b"<editorial_team_key>nba.t.1</editorial_team_key>", "AFFILIATION_UNVERIFIED"),
    ],
)
def test_orphaned_metadata_is_distinct_from_missing_affiliation(
    monkeypatch: pytest.MonkeyPatch, metadata: bytes, status: str
) -> None:
    import fantasy_gm.providers.puckapi as puck
    from fantasy_gm.sports.nhl.roster_schedule import roster_schedule_rows

    monkeypatch.setattr(puck, "sleep", lambda _: None)
    roster = roster_with(metadata)
    snapshot, _ = collect([game()])
    rows = roster_schedule_rows(
        roster,
        snapshot,
        roster_season=2026,
        start=date(2026, 10, 20),
        end=date(2026, 10, 22),
        timezone=ZoneInfo("America/Toronto"),
    )
    assert rows[0].status == status and rows[0].summary is None
    assert rows[1].status == "MISSING_AFFILIATION" and rows[1].summary is None


def test_players_on_same_team_share_one_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import fantasy_gm.providers.puckapi as puck
    from fantasy_gm.sports.nhl.roster_schedule import roster_schedule_rows

    monkeypatch.setattr(puck, "sleep", lambda _: None)
    roster = roster_with(b"<editorial_team_abbr>Tor</editorial_team_abbr>")
    roster = roster.model_copy(
        update={
            "coverage": roster.coverage.model_copy(update={"date": date(2026, 10, 15)})
        }
    )
    roster = roster.model_copy(
        update={
            "entries": (
                roster.entries[0],
                RosterEntry(
                    provider_player_id="999.p.803",
                    name="Invented second",
                    professional_team_code="TOR",
                ),
                RosterEntry(provider_player_id="999.p.804", name="Unknown affiliation"),
            )
        }
    )
    snapshot, _ = collect([game()])
    rows = roster_schedule_rows(
        roster,
        snapshot,
        roster_season=2026,
        start=date(2026, 10, 20),
        end=date(2026, 10, 22),
        timezone=ZoneInfo("America/Toronto"),
    )
    assert rows[0].status == rows[1].status == "MATCHED"
    assert rows[0].summary is rows[1].summary
    assert rows[0].summary is not None and rows[0].summary.total == 1
    assert rows[2].status == "MISSING_AFFILIATION" and rows[2].summary is None


@pytest.mark.parametrize(
    "code,uncertain,year,cohort,expected",
    [
        ("ARI", False, 2026, True, "UNSUPPORTED_TEAM"),
        ("SJ", False, 2026, True, "UNSUPPORTED_TEAM"),
        ("TOR", True, 2026, True, "AFFILIATION_UNVERIFIED"),
        ("TOR", False, 2025, True, "SEASON_MISMATCH"),
        ("TOR", False, None, True, "SEASON_MISMATCH"),
        ("TOR", False, 2026, False, "COHORT_UNVERIFIED"),
    ],
)
def test_unsupported_or_mismatched_affiliations_are_not_guessed(
    monkeypatch: pytest.MonkeyPatch,
    code: str,
    uncertain: bool,
    year: int | None,
    cohort: bool,
    expected: str,
) -> None:
    import fantasy_gm.providers.puckapi as puck
    from fantasy_gm.sports.nhl.roster_schedule import roster_schedule_rows

    monkeypatch.setattr(puck, "sleep", lambda _: None)
    roster = roster_with(b"")
    roster = roster.model_copy(
        update={
            "coverage": roster.coverage.model_copy(update={"date": date(2026, 10, 15)})
        }
    )
    roster = roster.model_copy(
        update={
            "entries": (
                RosterEntry(
                    provider_player_id="999.p.800",
                    name="Invented",
                    professional_team_code=code,
                    professional_team_unverified=uncertain,
                ),
            )
        }
    )
    snapshot, _ = collect([game()])
    snapshot = snapshot.model_copy(update={"cohort_verified": cohort})
    row = roster_schedule_rows(
        roster,
        snapshot,
        roster_season=year,
        start=date(2026, 10, 20),
        end=date(2026, 10, 22),
        timezone=ZoneInfo("America/Toronto"),
    )[0]
    assert row.status == expected and row.summary is None


def test_roster_reported_in_another_year_does_not_join_current_schedule(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import fantasy_gm.providers.puckapi as puck
    from fantasy_gm.sports.nhl.roster_schedule import roster_schedule_rows

    monkeypatch.setattr(puck, "sleep", lambda _: None)
    roster = roster_with(b"<editorial_team_abbr>TOR</editorial_team_abbr>")
    snapshot, _ = collect([game()])
    row = roster_schedule_rows(
        roster,
        snapshot,
        roster_season=2026,
        start=date(2026, 10, 20),
        end=date(2026, 10, 22),
        timezone=ZoneInfo("America/Toronto"),
    )[0]
    assert row.status == "SEASON_MISMATCH" and row.summary is None
