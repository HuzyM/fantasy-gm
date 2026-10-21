import type { DaySchedule, Player } from './view-model';
import { observedFixtures, isEligibleScheduled, joinedTeamGames } from './schedule-observations';

export function selectRosterWeek(
  start: string,
  days: readonly DaySchedule[],
  players: readonly Player[],
  observed = true,
  loadedWindow?: { readonly start: string; readonly end: string },
) {
  const dates = Array.from({ length: 7 }, (_, offset) => {
    const date = new Date(`${start}T12:00:00Z`);
    date.setUTCDate(date.getUTCDate() + offset);
    return date.toISOString().slice(0, 10);
  });
  const insideLoadedWindow = (date: string) =>
    !loadedWindow || (date >= loadedWindow.start && date <= loadedWindow.end);
  const fixtures = observedFixtures(days).filter((fixture) => insideLoadedWindow(fixture.date));
  return {
    dates,
    hasLoadedDates: !observed || (!!loadedWindow && dates.some(insideLoadedWindow)),
    rows: players.map((player) => {
      const cells = dates.map((date) => ({
        date,
        coverage: insideLoadedWindow(date)
          ? (days.find((day) => day.date === date)?.count.state ?? 'unknown')
          : 'unknown',
        fixtures: joinedTeamGames(
          observed ? player : { ...player, scheduleJoin: 'matched' },
          fixtures.filter((game) => game.date === date),
        ).map((game) => ({
          game,
          eligible:
            !game.conflict && (observed ? isEligibleScheduled(game) : game.state === undefined),
          status: game.conflict
            ? 'Conflicting observation'
            : observed && !game.dateVerified
              ? `Date/time unverified · ${game.state ?? 'UNKNOWN'}`
              : (game.state ?? 'UNKNOWN'),
        })),
        sameDayAnomaly: false,
        backToBack: false,
      }));
      let backToBackPairs = 0;
      cells.forEach((cell, index) => {
        cell.sameDayAnomaly =
          observed && cell.fixtures.filter((fixture) => fixture.eligible).length > 1;
        const next = cells[index + 1];
        // A team-date opportunity counts once, not once per fixture combination.
        if (
          cell.fixtures.some((fixture) => fixture.eligible) &&
          next?.fixtures.some((fixture) => fixture.eligible)
        ) {
          cell.backToBack = next.backToBack = true;
          backToBackPairs++;
        }
      });
      return {
        player,
        cells,
        scheduledCount: cells.reduce(
          (total, cell) => total + cell.fixtures.filter((fixture) => fixture.eligible).length,
          0,
        ),
        backToBackPairs,
      };
    }),
  };
}
