/** Certainty and provenance are independent: a verified fixture is never live data. */
export type Datum<T> =
  | { readonly state: 'verified'; readonly value: T }
  | { readonly state: 'incomplete'; readonly value: T; readonly reason: string }
  | { readonly state: 'unknown'; readonly reason: string }
  | { readonly state: 'unsupported'; readonly reason: string };

export type Provenance =
  | { readonly kind: 'synthetic'; readonly label: string }
  | { readonly kind: 'provider'; readonly name: string; readonly observedAt: string };
export type PositionGroup = 'all' | 'forwards' | 'defense' | 'goalies' | 'injured';
export type InjuryDesignation = 'Healthy' | 'DTD' | 'Out' | 'IR' | 'IR+';
export type InspectorTab = 'Overview' | 'Stats' | 'Schedule' | 'Game log';
export interface Game {
  readonly id: string;
  readonly away: string;
  readonly home: string;
  readonly time: string;
  readonly state?: string;
  readonly startTimeUtc?: string;
  readonly upcomingEligible?: boolean;
  readonly observationConflict?: boolean;
}
export interface DaySchedule {
  readonly date: string;
  readonly games: readonly Game[];
  readonly count: Datum<number>;
}
export interface Player {
  readonly id: string;
  readonly name: string;
  readonly number?: number;
  readonly team: string;
  readonly position: string;
  readonly group: Exclude<PositionGroup, 'all' | 'injured'> | 'unknown';
  readonly nhlId?: number;
  readonly identitySource?: 'yahoo';
  readonly scheduleJoin?: 'matched' | 'unverified';
  readonly rosterSlot: Datum<string>;
  readonly nextGame: string;
  readonly nextGameNote?: string;
  readonly weeklyPoints: Datum<number>;
  readonly average: Datum<number>;
  readonly injury: Datum<InjuryDesignation>;
  readonly stats: readonly { readonly label: string; readonly datum: Datum<number> }[];
}
export interface OverviewModel {
  readonly provenance: Provenance;
  readonly weekStart: string;
  readonly weekLabel: string;
  readonly season: string;
  readonly days: readonly DaySchedule[];
  readonly players: readonly Player[];
}
export function describeDatum<T>(datum: Datum<T>, format: (value: T) => string = String) {
  switch (datum.state) {
    case 'verified':
      return { text: format(datum.value), note: undefined };
    case 'incomplete':
      return { text: `${format(datum.value)} observed`, note: datum.reason };
    case 'unknown':
      return { text: 'Unknown', note: datum.reason };
    case 'unsupported':
      return { text: 'Unavailable', note: datum.reason };
  }
}
export function shiftWeek(start: string, direction: number): string {
  const date = new Date(`${start}T12:00:00Z`);
  date.setUTCDate(date.getUTCDate() + direction * 7);
  return date.toISOString().slice(0, 10);
}
/** Only a reported designation counts; an IR roster slot is not an injury report. */
export function isInjured<T extends { readonly injury?: Datum<InjuryDesignation> }>(
  player: T,
): boolean {
  const injury = player.injury;
  return (
    !!injury &&
    (injury.state === 'verified' || injury.state === 'incomplete') &&
    ['DTD', 'Out', 'IR', 'IR+'].includes(injury.value)
  );
}

export function filterPlayers<
  T extends Pick<Player, 'name' | 'team' | 'group'> & Partial<Pick<Player, 'injury'>>,
>(players: readonly T[], query: string, group: PositionGroup): T[] {
  const normalized = query.trim().toLocaleLowerCase('en-US');
  return players.filter(
    (player) =>
      (group === 'all' || (group === 'injured' ? isInjured(player) : player.group === group)) &&
      `${player.name} ${player.team}`.toLocaleLowerCase('en-US').includes(normalized),
  );
}
export function dateLabel(date: string, options: Intl.DateTimeFormatOptions): string {
  return new Intl.DateTimeFormat('en-US', { ...options, timeZone: 'UTC' }).format(
    new Date(`${date}T12:00:00Z`),
  );
}
