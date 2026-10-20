import type { DaySchedule, Game, Player } from './view-model';

export interface ObservedFixture extends Game {
  readonly date: string;
  readonly conflict: boolean;
  readonly dateVerified: boolean;
}

/** Calendar date in the schedule's Toronto timezone, independent of the browser timezone. */
export function torontoDate(instant: string): string {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Toronto',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date(instant));
}

/** Collapse exact repeats; retain all conflicting observations as ineligible evidence. */
export function observedFixtures(days: readonly DaySchedule[]): ObservedFixture[] {
  const groups = new Map<string, Map<string, Omit<ObservedFixture, 'conflict'>>>();
  for (const day of days) {
    for (const game of day.games) {
      const instant =
        game.startTimeUtc && Number.isFinite(Date.parse(game.startTimeUtc))
          ? new Date(game.startTimeUtc).toISOString()
          : undefined;
      const date = instant ? torontoDate(instant) : day.date;
      const signature = JSON.stringify([
        date,
        game.away,
        game.home,
        instant,
        game.state,
        game.upcomingEligible,
      ]);
      const variants = groups.get(game.id) ?? new Map();
      variants.set(signature, { ...game, date, dateVerified: instant !== undefined });
      groups.set(game.id, variants);
    }
  }
  return [...groups.values()]
    .flatMap((variants) =>
      [...variants.values()].map((game) => ({ ...game, conflict: variants.size > 1 })),
    )
    .sort(
      (a, b) =>
        a.date.localeCompare(b.date) ||
        (Date.parse(a.startTimeUtc ?? '') || 0) - (Date.parse(b.startTimeUtc ?? '') || 0) ||
        a.id.localeCompare(b.id),
    );
}

export function isEligibleScheduled(game: Game): boolean {
  return (
    game.upcomingEligible === true &&
    game.state === 'SCHEDULED' &&
    game.startTimeUtc !== undefined &&
    Number.isFinite(Date.parse(game.startTimeUtc))
  );
}

export function joinedTeamGames<T extends Game>(player: Player, games: readonly T[]): T[] {
  if (player.scheduleJoin !== 'matched') return [];
  return games.filter((game) => game.away === player.team || game.home === player.team);
}
