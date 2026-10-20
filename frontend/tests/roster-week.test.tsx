import { describe, expect, it } from 'vitest';
import { selectRosterWeek } from '../src/roster-week';
import type { DaySchedule, Game, Player } from '../src/view-model';
import { players } from '../src/fixtures/overview';
import { upcomingObservedGames, scheduleDays, type LocalView } from '../src/api';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import SchedulePlanner from '../src/screens/SchedulePlanner';

const player = (id = 'one', changes: Partial<Player> = {}): Player => ({
  ...players[0]!,
  id,
  name: `Invented ${id}`,
  team: 'TOR',
  scheduleJoin: 'matched',
  ...changes,
});

it('opens a labelled demo roster week, filters multi-position eligibility separately from slots, and navigates profiles', async () => {
  const user = userEvent.setup();
  const onNavigate = vi.fn();
  render(
    <SchedulePlanner
      players={[
        player('one', { position: 'C/LW', rosterSlot: { state: 'verified', value: 'BN' } }),
        player('two', { position: 'D', rosterSlot: { state: 'unknown', reason: 'Not supplied' } }),
      ]}
      search=""
      onNavigate={onNavigate}
      onNotice={vi.fn()}
    />,
  );
  await user.click(screen.getByRole('tab', { name: 'Roster week' }));
  expect(screen.getByRole('table', { name: 'Weekly roster schedule' })).toBeVisible();
  expect(screen.getByText(/Synthetic fixture counts/)).toBeVisible();
  await user.selectOptions(screen.getByLabelText('Position eligibility'), 'LW');
  const table = screen.getByRole('table', { name: 'Weekly roster schedule' });
  expect(within(table).getByText('Invented one')).toBeVisible();
  expect(within(table).queryByText('Invented two')).not.toBeInTheDocument();
  await user.selectOptions(screen.getByLabelText('Reported roster slot'), 'BN');
  await user.click(screen.getByRole('button', { name: 'View Invented one profile' }));
  expect(onNavigate).toHaveBeenCalledWith('profile', 'one');
  await user.selectOptions(screen.getByLabelText('Reported roster slot'), 'Unknown');
  expect(screen.getByText('No roster players match these filters.')).toBeVisible();
});

it('keeps missing date coverage and unsupported joins explicit, with keyboard view navigation', async () => {
  const user = userEvent.setup();
  const view = {
    mode: 'private',
    source: 'yahoo',
    schedule: {
      start: '2026-10-19',
      end: '2026-10-25',
      observedAt: '2026-10-20T12:00:00Z',
      days: [day('2026-10-19', [game('observed', '2026-10-19T23:00:00Z')])],
      teams: [],
      issues: [],
    },
  } as unknown as LocalView;
  render(
    <SchedulePlanner
      players={[player(), player('unknown', { scheduleJoin: 'unverified' })]}
      search=""
      onNavigate={vi.fn()}
      onNotice={vi.fn()}
      local={{ view, state: 'private', disconnect: async () => {} }}
    />,
  );
  await user.click(screen.getByRole('tab', { name: 'Daily matchups' }));
  await user.keyboard('{ArrowRight}');
  expect(screen.getByRole('tab', { name: 'Roster week' })).toHaveFocus();
  expect(screen.getAllByText(/Source observed at 2026-10-20T12:00:00Z/)[0]).toBeVisible();
  expect(screen.getAllByText('Coverage unknown')).toHaveLength(6);
  expect(screen.getByText(/Reported affiliation unavailable or unverified/)).toBeVisible();
  const row = screen.getByRole('row', { name: /Invented unknown/ });
  expect(within(row).getAllByRole('cell', { name: 'Unknown' })).toHaveLength(2);
});

it('does not report daily roster coverage for conflicting fixtures', () => {
  const days = [
    day('2026-10-19', [
      game('conflict', '2026-10-19T23:00:00Z'),
      game('conflict', '2026-10-19T23:00:00Z', { state: 'CANCELLED', upcomingEligible: false }),
    ]),
  ];
  const view = {
    mode: 'private',
    source: 'yahoo',
    schedule: { start: '2026-10-19', end: '2026-10-25', days, teams: [], issues: [] },
  } as unknown as LocalView;
  render(
    <SchedulePlanner
      players={[player()]}
      search=""
      onNavigate={vi.fn()}
      onNotice={vi.fn()}
      local={{ view, state: 'private', disconnect: async () => {} }}
    />,
  );
  expect(screen.getByRole('button', { name: /Select Monday, October 19/ })).toHaveAccessibleName(
    /0.*roster team matches/,
  );
});

it.each([
  { label: 'opponent', changes: { away: 'MTL' }, detail: /MTL @ TOR/ },
  {
    label: 'time',
    changes: { startTimeUtc: '2026-10-20T00:00:00Z', time: '8:00 PM' },
    detail: /8:00 PM/,
  },
  { label: 'state', changes: { state: 'CANCELLED' }, detail: /CANCELLED/ },
  {
    label: 'eligibility',
    changes: { upcomingEligible: false },
    detail: /source scheduled qualification excluded/,
  },
])(
  'selects one conflicting $label variant without presenting arbitrary matchup details',
  async ({ changes, detail }) => {
    const user = userEvent.setup();
    const days = [
      day('2026-10-19', [
        game('conflict', '2026-10-19T23:00:00Z'),
        game('conflict', '2026-10-19T23:00:00Z', changes),
      ]),
    ];
    const view = {
      mode: 'private',
      source: 'yahoo',
      schedule: { start: '2026-10-19', end: '2026-10-25', days, teams: [], issues: [] },
    } as unknown as LocalView;
    render(
      <SchedulePlanner
        players={[player()]}
        search=""
        onNavigate={vi.fn()}
        onNotice={vi.fn()}
        local={{ view, state: 'private', disconnect: async () => {} }}
      />,
    );
    const table = screen.getByRole('table', { name: 'Daily matchups' });
    const choices = within(table).getAllByRole('button', { name: /^Select/ });
    await user.click(choices[1]!);
    expect(choices.map((choice) => choice.getAttribute('aria-pressed'))).toEqual(['false', 'true']);
    const rows = within(table).getAllByRole('row').slice(1);
    expect(rows[0]).not.toHaveClass('planner-row-selected');
    expect(rows[1]).toHaveClass('planner-row-selected');
    const selected = screen.getByRole('complementary', { name: 'Selected matchup' });
    expect(
      within(selected).getByRole('heading', { name: 'Conflicting fixture observations' }),
    ).toBeVisible();
    expect(within(selected).getByText(detail)).toBeVisible();
    expect(within(selected).getByText(/player appearances remain unconfirmed/)).toBeVisible();
    expect(
      within(selected).queryByRole('tablist', { name: 'Matchup detail' }),
    ).not.toBeInTheDocument();
    expect(
      within(selected).queryByRole('button', { name: /View Invented one profile/ }),
    ).not.toBeInTheDocument();
  },
);
const game = (id: string, startTimeUtc: string, changes: Partial<Game> = {}): Game => ({
  id,
  startTimeUtc,
  time: '7:00 PM',
  away: 'BOS',
  home: 'TOR',
  state: 'SCHEDULED',
  upcomingEligible: true,
  ...changes,
});
const day = (date: string, games: Game[]): DaySchedule => ({
  date,
  games,
  count: { state: 'incomplete', value: games.length, reason: 'Partial test observation' },
});

describe('roster weekly observations', () => {
  it('retains excluded and undated evidence while blocking unverified affiliations', () => {
    const days = [
      day('2026-10-19', [
        game('scheduled', '2026-10-19T23:00:00Z'),
        ...['COMPLETED', 'IN_PROGRESS', 'CANCELLED', 'POSTPONED', 'RESCHEDULED', 'UNKNOWN'].map(
          (state) => game(state, '2026-10-19T23:00:00Z', { state, upcomingEligible: false }),
        ),
        game('missing-time', '2026-10-19T23:00:00Z', { startTimeUtc: undefined }),
        game('unsupported', '2026-10-19T23:00:00Z', { upcomingEligible: false }),
      ]),
    ];
    const week = selectRosterWeek('2026-10-19', days, [
      player(),
      player('unverified', { scheduleJoin: 'unverified' }),
    ]);
    expect(week.rows[0]!.scheduledCount).toBe(1);
    expect(week.rows[0]!.cells[0]!.fixtures).toHaveLength(9);
    expect(
      week.rows[0]!.cells[0]!.fixtures.find(({ game }) => game.id === 'missing-time')!.status,
    ).toContain('Date/time unverified');
    expect(week.rows[1]!.cells.every((cell) => !cell.fixtures.length)).toBe(true);
  });
  it('shares distinct team fixtures and counts loaded scheduled observations independent of elapsed time', () => {
    const first = game('one', '2026-10-19T23:00:00Z');
    const week = selectRosterWeek(
      '2026-10-19',
      [day('2026-10-19', [first, first]), day('2026-10-20', [game('two', '2026-10-21T00:00:00Z')])],
      [player(), player('two')],
    );
    expect(week.dates).toEqual([
      '2026-10-19',
      '2026-10-20',
      '2026-10-21',
      '2026-10-22',
      '2026-10-23',
      '2026-10-24',
      '2026-10-25',
    ]);
    expect(week.rows.map((row) => [row.scheduledCount, row.backToBackPairs])).toEqual([
      [2, 1],
      [2, 1],
    ]);
    expect(week.rows[0]!.cells[0]!.fixtures.map((fixture) => fixture.game.id)).toEqual(['one']);
    expect(week.rows[0]!.cells[0]!.backToBack).toBe(true);
  });
  it('fails closed on conflicting IDs across dates and states, including the next-game selector', () => {
    const first = game('conflict', '2026-10-19T23:00:00Z');
    const days = [
      day('2026-10-19', [first]),
      day('2026-10-20', [
        game('conflict', '2026-10-21T00:00:00Z'),
        game('state-conflict', '2026-10-21T01:00:00Z'),
        game('state-conflict', '2026-10-21T01:00:00Z', {
          state: 'CANCELLED',
          upcomingEligible: false,
        }),
      ]),
    ];
    const week = selectRosterWeek('2026-10-19', days, [player()]);
    expect(week.rows[0]!.scheduledCount).toBe(0);
    expect(week.rows[0]!.cells[0]!.fixtures[0]!.status).toBe('Conflicting observation');
    const view = {
      schedule: { start: '2026-10-19', end: '2026-10-25', days },
    } as unknown as LocalView;
    expect(upcomingObservedGames(view, Date.parse('2026-10-19T00:00:00Z'))).toEqual([]);
    expect(scheduleDays('2026-10-19', view)[0]!.games[0]!.observationConflict).toBe(true);
  });
  it('uses Toronto dates and UTC order across both DST changes without inventing same-day back-to-backs', () => {
    const fall = selectRosterWeek(
      '2026-10-26',
      [
        day('2026-11-01', [
          game('late', '2026-11-01T06:30:00Z'),
          game('early', '2026-11-01T05:30:00Z'),
          game('outside', '2026-11-02T05:30:00Z'),
        ]),
      ],
      [player()],
    );
    expect(fall.rows[0]!.cells[6]!.fixtures.map(({ game }) => game.id)).toEqual(['early', 'late']);
    expect([fall.rows[0]!.scheduledCount, fall.rows[0]!.backToBackPairs]).toEqual([2, 0]);
    const spring = selectRosterWeek(
      '2026-03-02',
      [
        day('2026-03-08', [
          game('before-midnight', '2026-03-08T04:30:00Z'),
          game('after-jump', '2026-03-08T07:30:00Z'),
        ]),
      ],
      [player()],
    );
    expect(spring.rows[0]!.cells[5]!.fixtures[0]!.game.id).toBe('before-midnight');
    expect(spring.rows[0]!.cells[6]!.fixtures[0]!.game.id).toBe('after-jump');
    expect(spring.rows[0]!.backToBackPairs).toBe(1);
  });
  it('keeps week boundaries and year changes calendar-based and sees conflicts outside the selected week', () => {
    const days = [
      day('2026-12-27', [game('edge', '2026-12-28T00:00:00Z')]),
      day('2026-12-28', [game('in-week', '2026-12-29T00:00:00Z')]),
      day('2027-01-03', [game('last', '2027-01-04T00:00:00Z')]),
      day('2027-01-04', [game('outside', '2027-01-05T00:00:00Z')]),
    ];
    const week = selectRosterWeek('2026-12-28', days, [player()]);
    expect(week.dates[6]).toBe('2027-01-03');
    expect([week.rows[0]!.scheduledCount, week.rows[0]!.backToBackPairs]).toEqual([2, 0]);
    days[3] = { ...days[3]!, games: [...days[3]!.games, game('in-week', '2027-01-05T01:00:00Z')] };
    expect(selectRosterWeek('2026-12-28', days, [player()]).rows[0]!.scheduledCount).toBe(1);
  });
  it('does not promote stray fixtures outside the declared loaded window', () => {
    const week = selectRosterWeek(
      '2026-10-19',
      [day('2026-10-19', [game('outside', '2026-10-19T23:00:00Z')])],
      [player()],
      true,
      { start: '2026-10-20', end: '2026-10-25' },
    );
    expect(week.rows[0]!.scheduledCount).toBe(0);
    expect(week.rows[0]!.cells[0]!.coverage).toBe('unknown');
  });
});
