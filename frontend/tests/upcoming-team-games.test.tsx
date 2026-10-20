import { render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { parseView, providerPlayers, upcomingObservedGames } from '../src/api';
import MyRoster from '../src/screens/MyRoster';
import PlayerProfile from '../src/screens/PlayerProfile';

const now = Date.parse('2026-11-01T05:00:00Z');
const game = (id: string, time: string | null, changes = {}) => ({
  id,
  time,
  away: 'BOS',
  home: 'TOR',
  state: 'SCHEDULED',
  upcomingEligible: true,
  ...changes,
});
function observation(
  games = [game('later', '2026-11-01T06:30:00Z'), game('first', '2026-11-01T05:30:00Z')],
) {
  return {
    mode: 'private',
    source: 'yahoo',
    provenance: ['Synthetic test only'],
    league: { name: 'Synthetic league', season: 2026 },
    roster: {
      teamName: 'Synthetic team',
      returnedCount: 2,
      contextUnverified: true,
      coverage: { kind: null, date: null, week: null },
      entries: ['one', 'two'].map((id) => ({
        id,
        name: `Invented ${id}`,
        positions: ['D'],
        slot: 'D',
        team: 'TOR',
        affiliationUnverified: false,
        scheduleStatus: 'MATCHED',
      })),
    },
    schedule: {
      start: '2026-11-01',
      end: '2026-11-07',
      timezone: 'America/Toronto',
      observedAt: '2026-11-01T04:00:00Z',
      issues: ['COVERAGE_UNVERIFIED'],
      teams: [],
      days: [
        { date: '2026-11-01', count: { state: 'unknown', reason: 'Partial observation' }, games },
      ],
    },
  };
}
afterEach(() => vi.useRealTimers());
describe('upcoming observed team games', () => {
  it('orders DST repeated local hours by UTC, deduplicates and shares team results without verifying identity', () => {
    const raw = observation();
    raw.schedule.days[0]!.games.push(raw.schedule.days[0]!.games[1]!);
    const view = parseView(raw);
    expect(upcomingObservedGames(view, now).map((g) => g.id)).toEqual(['first', 'later']);
    const players = providerPlayers(view, now);
    expect(players.map((p) => p.nextGame)).toEqual([
      'vs BOS · Nov 1, 1:30 AM ET',
      'vs BOS · Nov 1, 1:30 AM ET',
    ]);
    expect(players.every((p) => p.nhlId === undefined && p.injury.state === 'unknown')).toBe(true);
    expect(players[0]!.nextGameNote).toContain('incomplete or stale');
    expect(
      upcomingObservedGames(view, Date.parse('2026-11-01T05:45:00Z')).map((g) => g.id),
    ).toEqual(['later']);
  });
  it('supports away games and includes starts exactly at the cutoff', () => {
    const view = parseView(
      observation([game('away', '2026-11-01T05:00:00Z', { away: 'TOR', home: 'BOS' })]),
    );
    expect(providerPlayers(view, now)[0]!.nextGame).toBe('@ BOS · Nov 1, 1:00 AM ET');
  });
  it.each(['COMPLETED', 'IN_PROGRESS', 'POSTPONED', 'CANCELLED', 'RESCHEDULED', 'UNKNOWN'])(
    'excludes %s even with a future timestamp',
    (state) => {
      const view = parseView(observation([game('uncertain', '2026-11-01T06:00:00Z', { state })]));
      expect(providerPlayers(view, now)[0]!.nextGame).toBe('Unknown');
    },
  );
  it('excludes stale, missing-time and unqualified observations without claiming no games', () => {
    const raw = observation([
      game('past', '2026-11-01T04:00:00Z'),
      game('unplaced', null),
      game('abnormal', '2026-11-01T06:00:00Z', { upcomingEligible: false }),
    ]);
    const player = providerPlayers(parseView(raw), now)[0]!;
    expect(player.nextGame).toBe('Unknown');
    expect(player.nextGameNote).toContain('does not establish an off-day');
    expect(upcomingObservedGames(parseView(raw), NaN)).toEqual([]);
  });
  it.each([
    'MISSING_AFFILIATION',
    'AFFILIATION_UNVERIFIED',
    'UNSUPPORTED_TEAM',
    'COHORT_UNVERIFIED',
    'SEASON_MISMATCH',
    'UNAVAILABLE',
  ])('blocks %s without guessing from names or teams', (status) => {
    const raw = observation();
    raw.roster.entries[0]!.scheduleStatus = status;
    expect(providerPlayers(parseView(raw), now)[0]!.nextGame).toBe('Unknown');
  });
  it('blocks conflicting affiliation metadata, missing schedules and unobserved windows', () => {
    const raw = observation();
    raw.roster.entries[0]!.affiliationUnverified = true;
    expect(providerPlayers(parseView(raw), now)[0]!.nextGame).toBe('Unknown');
    expect(providerPlayers(parseView({ ...raw, schedule: null }), now)[0]!.nextGame).toBe(
      'Unavailable',
    );
    raw.schedule.start = '2026-11-02';
    expect(providerPlayers(parseView(raw), now)[1]!.nextGame).toBe('Unknown');
  });
  it('rejects naive/non-UTC instants and never treats a legacy game as eligible', () => {
    expect(() => parseView(observation([game('naive', '2026-11-01T01:30:00')]))).toThrow();
    const raw = observation();
    const legacy = {
      ...raw,
      schedule: {
        ...raw.schedule,
        days: raw.schedule.days.map((d) => ({
          ...d,
          games: d.games.map(({ upcomingEligible: _, ...g }) => g),
        })),
      },
    };
    expect(providerPlayers(parseView(legacy), now)[0]!.nextGame).toBe('Unknown');
  });
  it('shows the observed selection in My Roster and only upcoming fixtures in Profile', () => {
    vi.useFakeTimers();
    vi.setSystemTime(now);
    const raw = observation();
    raw.schedule.days[0]!.games.push(
      game('completed', '2026-11-01T08:00:00Z', { state: 'COMPLETED' }),
    );
    const view = parseView(raw);
    const props = {
      players: providerPlayers(view),
      search: '',
      onNavigate: vi.fn(),
      onNotice: vi.fn(),
      local: { view, state: 'private' as const, disconnect: async () => {} },
    };
    const { unmount } = render(<MyRoster {...props} />);
    expect(screen.getByRole('columnheader', { name: 'NEXT OBSERVED TEAM GAME' })).toBeVisible();
    expect(screen.getAllByText('vs BOS · Nov 1, 1:30 AM ET')).toHaveLength(2);
    expect(screen.getByText(/Observed team-game window/)).toHaveTextContent(
      '2026-11-01 – 2026-11-07',
    );
    unmount();
    render(<PlayerProfile {...props} selectedId="one" />);
    expect(screen.getByRole('heading', { name: 'Upcoming Observed Team Games' })).toBeVisible();
    expect(screen.getAllByText('Nov 1')).toHaveLength(2);
    expect(screen.queryByText('3:00 AM ET')).not.toBeInTheDocument();
  });
});
