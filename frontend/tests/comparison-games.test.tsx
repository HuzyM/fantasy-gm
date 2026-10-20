import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import PlayerComparison from '../src/screens/PlayerComparison';
import { players } from '../src/fixtures/overview';
import type { DaySchedule, Game, Player } from '../src/view-model';
import type { LocalView } from '../src/api';

const player = (id: string, team: string, changes: Partial<Player> = {}): Player => ({
  ...players[0]!,
  id,
  name: `Invented ${id}`,
  nhlId: undefined,
  team,
  scheduleJoin: 'matched',
  ...changes,
});
const game = (id: string, startTimeUtc: string | undefined, changes: Partial<Game> = {}): Game => ({
  id,
  startTimeUtc,
  time: 'Untrusted display time',
  away: 'BOS',
  home: 'TOR',
  state: 'SCHEDULED',
  upcomingEligible: true,
  ...changes,
});
const day = (date: string, games: Game[]): DaySchedule => ({
  date,
  games,
  count: { state: 'incomplete', value: games.length, reason: 'Synthetic partial coverage' },
});
function observed(
  days: DaySchedule[],
  pair = [player('one', 'TOR'), player('two', 'MTL')],
  start = '2026-10-19',
  end = '2026-10-25',
) {
  const view = {
    mode: 'private',
    source: 'yahoo',
    schedule: { start, end, days, observedAt: '2026-10-26T12:00:00Z', teams: [], issues: [] },
  } as unknown as LocalView;
  return render(
    <PlayerComparison
      players={pair}
      search=""
      onNavigate={vi.fn()}
      onNotice={vi.fn()}
      local={{ view, state: 'private', disconnect: async () => {} }}
    />,
  );
}

it('compares seven inclusive demo dates and keeps the pair while advancing into unknown coverage', async () => {
  const user = userEvent.setup();
  render(<PlayerComparison players={players} search="" onNavigate={vi.fn()} onNotice={vi.fn()} />);
  expect(screen.queryByRole('heading', { name: 'Upcoming Schedule' })).not.toBeInTheDocument();
  await user.click(screen.getByRole('tab', { name: 'Schedule' }));
  const week = screen.getByRole('region', { name: 'Weekly game comparison' });
  expect(within(week).getAllByRole('heading', { level: 3 })).toHaveLength(7);
  expect(within(week).getByText('Dec 7 – Dec 13, 2026')).toBeVisible();
  expect(within(week).getByText(/Synthetic games/)).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Next comparison week' }));
  expect(within(week).getByText('Dec 14 – Dec 20, 2026')).toBeVisible();
  expect(within(week).getAllByText('Coverage unknown')).toHaveLength(14);
  expect(within(week).getAllByText('No qualifying game observed')).toHaveLength(14);
  expect(screen.getByLabelText('First player')).toHaveValue('matthews');
  expect(screen.getByLabelText('Second player')).toHaveValue('mackinnon');
});

it('keeps source exclusions visible with exact reasons and counts qualifying recorded games after their starts', async () => {
  const user = userEvent.setup();
  observed([
    day('2026-10-19', [
      game('qualified', '2026-10-19T23:00:00Z'),
      ...['COMPLETED', 'IN_PROGRESS', 'POSTPONED', 'CANCELLED', 'UNKNOWN'].map((state, i) =>
        game(`excluded-${i}`, '2026-10-20T00:00:00Z', { state }),
      ),
      game('missing', '2026-10-20T01:00:00Z', { upcomingEligible: undefined }),
      game('false', '2026-10-20T02:00:00Z', { upcomingEligible: false }),
      game('invalid', 'invalid'),
      game('missing-time', undefined),
    ]),
  ]);
  await user.click(screen.getByRole('tab', { name: 'Schedule' }));
  const summary = screen.getByRole('region', { name: 'Invented one game summary' });
  expect(within(summary).getByText('1', { selector: 'dd' })).toBeVisible();
  const games = screen.getByRole('group', { name: 'Invented one games on 2026-10-19' });
  for (const status of ['COMPLETED', 'IN PROGRESS', 'POSTPONED', 'CANCELLED', 'UNKNOWN'])
    expect(within(games).getByText(status)).toBeVisible();
  expect(within(games).getByText('Scheduled · source eligibility unavailable')).toBeVisible();
  expect(within(games).getByText('Scheduled · source eligibility excluded')).toBeVisible();
  expect(within(games).getAllByText('Time unavailable / unverified')).toHaveLength(2);
  expect(within(games).getByText('7:00 PM EDT')).toBeVisible();
  expect(screen.getByText(/Source observed at 2026-10-26T12:00:00Z/)).toBeVisible();
});

it('retains scheduled observations when the clock moves beyond their recorded start', async () => {
  vi.useFakeTimers({ toFake: ['Date'] });
  try {
    vi.setSystemTime(new Date('2026-10-19T12:00:00Z'));
    const user = userEvent.setup();
    observed([day('2026-10-19', [game('scheduled', '2026-10-19T23:00:00Z')])]);
    await user.click(screen.getByRole('tab', { name: 'Schedule' }));
    const summary = screen.getByRole('region', { name: 'Invented one game summary' });
    expect(within(summary).getByText('1', { selector: 'dd' })).toBeVisible();
    vi.setSystemTime(new Date('2026-10-26T12:00:00Z'));
    await user.click(screen.getByRole('tab', { name: 'Statistics' }));
    await user.click(screen.getByRole('tab', { name: 'Schedule' }));
    expect(
      within(screen.getByRole('region', { name: 'Invented one game summary' })).getByText('1', {
        selector: 'dd',
      }),
    ).toBeVisible();
  } finally {
    vi.useRealTimers();
  }
});

it('counts shared dates once, preserves partial games, and updates both sides while retaining the window', async () => {
  const user = userEvent.setup();
  observed(
    [
      day('2026-10-19', [game('monday', '2026-10-19T23:00:00Z')]),
      day('2026-10-21', [
        game('wednesday', '2026-10-21T23:00:00Z'),
        game('wednesday-extra', '2026-10-22T00:00:00Z'),
        game('mtl-wed', '2026-10-22T01:00:00Z', { home: 'MTL' }),
      ]),
      day('2026-10-23', [game('friday', '2026-10-23T23:00:00Z', { home: 'MTL' })]),
    ],
    [
      player('one', 'TOR'),
      player('two', 'MTL'),
      player('three', 'TOR'),
      player('unknown', 'Unknown', { scheduleJoin: 'unverified' }),
    ],
  );
  await user.click(screen.getByRole('tab', { name: 'Schedule' }));
  expect(screen.getByText('Shared game dates: 1')).toBeVisible();
  expect(screen.getAllByText('Shared game date', { exact: true })).toHaveLength(1);
  expect(
    within(screen.getByRole('region', { name: 'Wednesday, October 21, 2026' })).getByText(
      'Shared game date',
    ),
  ).toBeVisible();
  expect(screen.getByText(/Schedule anomaly: multiple/)).toBeVisible();
  expect(screen.getAllByText('Partial observation · complete totals unknown')).toHaveLength(6);
  await user.selectOptions(screen.getByLabelText('Second player'), 'three');
  expect(screen.getByText('Shared game dates: 2')).toBeVisible();
  for (const name of ['one', 'three'])
    expect(
      within(screen.getByRole('region', { name: `Invented ${name} game summary` })).getByText('3', {
        selector: 'dd',
      }),
    ).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Next comparison week' }));
  await user.click(screen.getByRole('button', { name: 'Swap players' }));
  await user.click(screen.getByRole('tab', { name: 'History' }));
  await user.click(screen.getByRole('tab', { name: 'Schedule' }));
  expect(screen.getByText('Oct 26 – Nov 1, 2026')).toBeVisible();
  await user.selectOptions(screen.getByLabelText('First player'), 'unknown');
  expect(screen.getByText('Shared game dates: Unknown')).toBeVisible();
  const unavailable = screen.getByRole('region', { name: 'Invented unknown game summary' });
  expect(within(unavailable).getAllByText('Unknown', { selector: 'dd' })).toHaveLength(2);
});

it('shows head-to-head home/away for both players and every qualifying game beyond the old five-game limit', async () => {
  const user = userEvent.setup();
  observed([
    day(
      '2026-10-19',
      Array.from({ length: 6 }, (_, index) =>
        game(`game-${index}`, `2026-10-19T${String(18 + index).padStart(2, '0')}:00:00Z`, {
          away: 'MTL',
        }),
      ),
    ),
  ]);
  await user.click(screen.getByRole('tab', { name: 'Schedule' }));
  expect(
    within(screen.getByRole('group', { name: 'Invented one games on 2026-10-19' })).getAllByText(
      'vs MTL · Home',
    ),
  ).toHaveLength(6);
  expect(
    within(screen.getByRole('group', { name: 'Invented two games on 2026-10-19' })).getAllByText(
      '@ TOR · Away',
    ),
  ).toHaveLength(6);
  expect(screen.getByText('Shared game dates: 1')).toBeVisible();
});

it.each([
  ['opponent', { away: 'MTL' }],
  ['time', { startTimeUtc: '2026-10-20T00:00:00Z' }],
  ['state', { state: 'CANCELLED' }],
  ['eligibility', { upcomingEligible: false }],
  ['date outside the week', { startTimeUtc: '2026-10-26T23:00:00Z' }],
] as const)(
  'collapses identical repeats and excludes conflicting %s variants before weekly filtering',
  async (kind, changes) => {
    const user = userEvent.setup();
    observed([
      day('2026-10-19', [
        game('repeated', '2026-10-19T22:00:00Z'),
        game('repeated', '2026-10-19T22:00:00Z'),
        game('disputed', '2026-10-19T23:00:00Z'),
        game('disputed', '2026-10-19T23:00:00Z', changes),
      ]),
    ]);
    await user.click(screen.getByRole('tab', { name: 'Schedule' }));
    const summary = screen.getByRole('region', { name: 'Invented one game summary' });
    expect(within(summary).getByText('1', { selector: 'dd' })).toBeVisible();
    const cell = screen.getByRole('group', { name: 'Invented one games on 2026-10-19' });
    expect(within(cell).getAllByRole('listitem')).toHaveLength(
      kind === 'date outside the week' ? 2 : 3,
    );
    expect(
      within(cell).getAllByText('Disputed observation · excluded from counts').length,
    ).toBeGreaterThan(0);
    expect(within(cell).getAllByText(/no authoritative variant selected/).length).toBeGreaterThan(
      0,
    );
  },
);

it('counts adjacent date pairs wholly inside the window without multiplying same-day games', async () => {
  const user = userEvent.setup();
  observed(
    [
      day('2026-10-18', [game('before', '2026-10-18T23:00:00Z')]),
      day('2026-10-19', [
        game('first', '2026-10-19T23:00:00Z'),
        game('same-day', '2026-10-20T00:00:00Z'),
      ]),
      day('2026-10-20', [game('second', '2026-10-20T23:00:00Z')]),
      day('2026-10-21', [game('third', '2026-10-21T23:00:00Z')]),
      day('2026-10-25', [game('last', '2026-10-25T23:00:00Z')]),
      day('2026-10-26', [game('after', '2026-10-26T23:00:00Z')]),
    ],
    undefined,
    '2026-10-19',
    '2026-10-26',
  );
  await user.click(screen.getByRole('tab', { name: 'Schedule' }));
  const summary = screen.getByRole('region', { name: 'Invented one game summary' });
  expect(within(summary).getByText('5', { selector: 'dd' })).toBeVisible();
  expect(within(summary).getByText('2', { selector: 'dd' })).toBeVisible();
});

it.each([
  [
    '2026-03-08',
    '2026-03-08T06:30:00Z',
    '2026-03-08T07:30:00Z',
    '1:30 AM EST',
    '3:30 AM EDT',
    'Mar 15 – Mar 21, 2026',
  ],
  [
    '2026-11-01',
    '2026-11-01T05:30:00Z',
    '2026-11-01T06:30:00Z',
    '1:30 AM EDT',
    '1:30 AM EST',
    'Nov 8 – Nov 14, 2026',
  ],
  [
    '2026-12-31',
    '2027-01-01T00:30:00Z',
    '2027-01-01T02:30:00Z',
    '7:30 PM EST',
    '9:30 PM EST',
    'Jan 7 – Jan 13, 2027',
  ],
])(
  'uses Toronto dates and UTC ordering through calendar boundary %s',
  async (start, first, second, firstTime, secondTime, nextRange) => {
    const user = userEvent.setup();
    observed(
      [day(start, [game('later', second), game('earlier', first)])],
      undefined,
      start,
      '2027-01-06',
    );
    await user.click(screen.getByRole('tab', { name: 'Schedule' }));
    const cell = screen.getByRole('group', { name: `Invented one games on ${start}` });
    const items = within(cell).getAllByRole('listitem');
    expect(items[0]).toHaveTextContent(firstTime);
    expect(items[1]).toHaveTextContent(secondTime);
    await user.click(screen.getByRole('button', { name: 'Next comparison week' }));
    expect(screen.getByText(nextRange)).toBeVisible();
  },
);

it.each([{ pair: [] }, { pair: [player('only', 'TOR')] }])(
  'requires two loaded roster identities without a demo replacement',
  ({ pair }) => {
    observed([], pair);
    expect(
      screen.getByText(
        pair.length
          ? 'At least two supplied players are required to compare.'
          : 'No players are available to compare.',
      ),
    ).toBeVisible();
    expect(screen.queryByRole('tab', { name: 'Schedule' })).not.toBeInTheDocument();
    expect(screen.queryByText('Auston Matthews')).not.toBeInTheDocument();
  },
);
