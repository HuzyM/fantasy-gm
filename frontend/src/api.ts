import type { DaySchedule, Player } from './view-model';
import { dateLabel } from './view-model';
import { daysForWeek } from './fixtures/overview';
import { observedFixtures, isEligibleScheduled, joinedTeamGames } from './schedule-observations';
export { joinedTeamGames } from './schedule-observations';

export interface LocalView {
  mode: 'synthetic' | 'private';
  source: 'synthetic' | 'yahoo' | 'puckapi';
  provenance: string[];
  planningWindow?: { start: string; end: string; timezone: string };
  league: { name: string; season: number | null } | null;
  roster: {
    teamName: string;
    returnedCount: number | null;
    contextUnverified: boolean;
    coverage: { kind: string | null; date: string | null; week: string | null };
    entries: {
      id: string;
      name: string;
      positions: string[] | null;
      slot: string | null;
      team: string | null;
      affiliationUnverified: boolean;
      scheduleStatus: string;
    }[];
  } | null;
  schedule: {
    start: string;
    end: string;
    timezone: string;
    observedAt: string;
    issues: string[];
    days: readonly DaySchedule[];
    teams: {
      code: string;
      observedGames: number;
      countComplete: boolean;
      backToBackComplete: boolean;
      uncertainDated: number;
      unplaced: number;
    }[];
  } | null;
}
function fail(): never {
  throw new Error('Local service response unavailable');
}
function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return fail();
  return value as Record<string, unknown>;
}
function string(value: unknown): string {
  if (typeof value !== 'string' || value.length > 1000) return fail();
  return value;
}
function nullableString(value: unknown): string | null {
  return value === null ? null : string(value);
}
function bool(value: unknown): boolean {
  if (typeof value !== 'boolean') return fail();
  return value;
}
function number(value: unknown): number {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < 0) return fail();
  return value;
}
function array(value: unknown, max = 500): unknown[] {
  if (!Array.isArray(value) || value.length > max) return fail();
  return value;
}
function strings(value: unknown): string[] {
  return array(value).map(string);
}
function date(value: unknown): string {
  const result = string(value);
  if (
    !/^\d{4}-\d{2}-\d{2}$/.test(result) ||
    !Number.isFinite(Date.parse(result)) ||
    new Date(result).toISOString().slice(0, 10) !== result
  )
    return fail();
  return result;
}
function time(value: unknown, timezone: string): string {
  if (value === null) return 'Time unknown';
  const result = string(value);
  if (!/(Z|\+00:00)$/.test(result) || !Number.isFinite(Date.parse(result))) return fail();
  return new Intl.DateTimeFormat('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    timeZone: timezone,
  }).format(new Date(result));
}
/** Copy an explicit display whitelist. Never log provider bodies or infer missing fields. */
export function parseView(value: unknown): LocalView {
  const raw = record(value);
  if (raw.mode !== 'synthetic' && raw.mode !== 'private') return fail();
  if (!['synthetic', 'yahoo', 'puckapi'].includes(string(raw.source))) return fail();
  if (raw.mode === 'private' && raw.source !== 'yahoo') return fail();
  if (raw.mode === 'synthetic' && raw.source === 'yahoo') return fail();
  if (raw.mode === 'private' && (raw.league === null || raw.roster === null)) return fail();
  const league = raw.league === null ? null : record(raw.league);
  const roster = raw.roster === null ? null : record(raw.roster);
  const coverage = roster ? record(roster.coverage) : null;
  if (roster) {
    const ids = array(roster.entries, 200).map((entry) => string(record(entry).id));
    if (ids.some((id) => !id) || new Set(ids).size !== ids.length) return fail();
  }
  const schedule = raw.schedule === null ? null : record(raw.schedule);
  const timezone = schedule ? string(schedule.timezone) : 'America/Toronto';
  if (timezone !== 'America/Toronto') return fail();
  const window = raw.planningWindow === undefined ? schedule : record(raw.planningWindow);
  if (!window && raw.source !== 'synthetic') return fail();
  const planningWindow = window
    ? { start: date(window.start), end: date(window.end), timezone: string(window.timezone) }
    : undefined;
  if (planningWindow) {
    const expectedEnd = new Date(`${planningWindow.start}T12:00:00Z`);
    expectedEnd.setUTCDate(expectedEnd.getUTCDate() + 6);
    if (
      planningWindow.timezone !== 'America/Toronto' ||
      planningWindow.end !== expectedEnd.toISOString().slice(0, 10) ||
      (schedule && (schedule.start !== planningWindow.start || schedule.end !== planningWindow.end))
    )
      return fail();
  }
  return {
    mode: raw.mode,
    source: raw.source as LocalView['source'],
    provenance: strings(raw.provenance),
    planningWindow,
    league: league
      ? { name: string(league.name), season: league.season === null ? null : number(league.season) }
      : null,
    roster:
      roster && coverage
        ? {
            teamName: string(roster.teamName),
            returnedCount: roster.returnedCount === null ? null : number(roster.returnedCount),
            contextUnverified: bool(roster.contextUnverified),
            coverage: {
              kind: nullableString(coverage.kind),
              date: coverage.date === null ? null : date(coverage.date),
              week: nullableString(coverage.week),
            },
            entries: array(roster.entries, 200).map((value) => {
              const entry = record(value);
              return {
                id: string(entry.id),
                name: string(entry.name),
                positions: entry.positions === null ? null : strings(entry.positions),
                slot: nullableString(entry.slot),
                team: nullableString(entry.team),
                affiliationUnverified: bool(entry.affiliationUnverified),
                scheduleStatus: string(entry.scheduleStatus),
              };
            }),
          }
        : null,
    schedule: schedule
      ? {
          start: date(schedule.start),
          end: date(schedule.end),
          timezone,
          observedAt: string(schedule.observedAt),
          issues: strings(schedule.issues),
          days: array(schedule.days, 31).map((value) => {
            const day = record(value),
              count = record(day.count);
            if (!['verified', 'incomplete', 'unknown'].includes(string(count.state))) return fail();
            const datum =
              count.state === 'unknown'
                ? { state: 'unknown' as const, reason: string(count.reason) }
                : count.state === 'incomplete'
                  ? {
                      state: 'incomplete' as const,
                      value: number(count.value),
                      reason: string(count.reason),
                    }
                  : { state: 'verified' as const, value: number(count.value) };
            return {
              date: date(day.date),
              count: datum,
              games: array(day.games).map((value) => {
                const game = record(value);
                return {
                  id: string(game.id),
                  away: string(game.away),
                  home: string(game.home),
                  time: time(game.time, timezone),
                  state: string(game.state),
                  startTimeUtc: game.time === null ? undefined : string(game.time),
                  upcomingEligible:
                    game.upcomingEligible === undefined ? undefined : bool(game.upcomingEligible),
                };
              }),
            };
          }),
          teams: array(schedule.teams, 32).map((value) => {
            const team = record(value);
            return {
              code: string(team.code),
              observedGames: number(team.observedGames),
              countComplete: bool(team.countComplete),
              backToBackComplete: bool(team.backToBackComplete),
              uncertainDated: number(team.uncertainDated),
              unplaced: number(team.unplaced),
            };
          }),
        }
      : null,
  };
}
export const isObservation = (view?: LocalView | null) => !!view && view.source !== 'synthetic';
export function scheduleDays(start: string, view?: LocalView | null): readonly DaySchedule[] {
  if (!isObservation(view) && !view) return daysForWeek(start);
  const schedule = view?.schedule;
  const fixtures = observedFixtures(schedule?.days ?? []);
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(`${start}T12:00:00Z`);
    d.setUTCDate(d.getUTCDate() + i);
    const date = d.toISOString().slice(0, 10);
    const supplied =
      schedule && date >= schedule.start && date <= schedule.end
        ? schedule.days.find((day) => day.date === date)
        : undefined;
    return {
      ...(supplied ?? {
        date,
        games: [],
        count: { state: 'unknown' as const, reason: 'No observation is loaded for this date.' },
      }),
      games: fixtures
        .filter(
          (game) =>
            game.date === date && schedule && date >= schedule.start && date <= schedule.end,
        )
        .map((game) => ({ ...game, observationConflict: game.conflict })),
    };
  });
}
/** Earliest usable observations only: never a complete schedule or a player appearance. */
export function upcomingObservedGames(view: LocalView, asOf = Date.now()) {
  const schedule = view.schedule;
  if (!schedule || !Number.isFinite(asOf)) return [];
  return observedFixtures(schedule.days)
    .filter(
      (game) =>
        game.date >= schedule.start &&
        game.date <= schedule.end &&
        !game.conflict &&
        isEligibleScheduled(game) &&
        Date.parse(game.startTimeUtc!) >= asOf,
    )
    .sort(
      (a, b) =>
        Date.parse(a.startTimeUtc!) - Date.parse(b.startTimeUtc!) || a.id.localeCompare(b.id),
    );
}

export function providerPlayers(view: LocalView, asOf = Date.now()): readonly Player[] {
  const upcoming = upcomingObservedGames(view, asOf);
  return (view.roster?.entries ?? []).map((entry) => {
    const positions = entry.positions ?? [];
    const categories = [
      ...(positions.some((p) => ['C', 'LW', 'RW', 'F'].includes(p)) ? ['forwards'] : []),
      ...(positions.includes('D') ? ['defense'] : []),
      ...(positions.includes('G') ? ['goalies'] : []),
    ];
    const player: Player = {
      id: entry.id,
      identitySource: 'yahoo',
      scheduleJoin:
        entry.scheduleStatus === 'MATCHED' && !entry.affiliationUnverified
          ? 'matched'
          : 'unverified',
      name: entry.name,
      team: entry.team ?? 'UNK',
      position: positions.join('/') || 'Unknown',
      group: categories.length === 1 ? (categories[0] as Player['group']) : 'unknown',
      rosterSlot:
        entry.slot === null
          ? { state: 'unknown', reason: 'No slot supplied.' }
          : { state: 'verified', value: entry.slot },
      nextGame: view.schedule ? 'Unknown' : 'Unavailable',
      injury: { state: 'unknown', reason: 'Injury reports are not supplied by this adapter.' },
      weeklyPoints: { state: 'unsupported', reason: 'No performance source connected.' },
      average: { state: 'unsupported', reason: 'No performance source connected.' },
      stats: [],
    };
    const next = joinedTeamGames(player, upcoming)[0];
    return {
      ...player,
      nextGame: next
        ? `${next.home === player.team ? 'vs' : '@'} ${next.home === player.team ? next.away : next.home} · ${dateLabel(next.date, { month: 'short', day: 'numeric' })}, ${next.time} ET`
        : player.nextGame,
      nextGameNote: !view.schedule
        ? 'No schedule observation loaded.'
        : player.scheduleJoin !== 'matched'
          ? `Reported affiliation cannot support a schedule join (${entry.scheduleStatus}).`
          : next
            ? 'Earliest eligible observation in the loaded window; coverage and affiliation may be incomplete or stale. Appearance unconfirmed.'
            : 'No eligible upcoming team game observed in the loaded window. This does not establish an off-day.',
    };
  });
}
