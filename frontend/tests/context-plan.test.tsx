import { fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import App from '../src/App';

const view = {
  mode: 'private',
  source: 'yahoo',
  provenance: ['Fabricated context plan protocol'],
  planningWindow: { start: '2026-12-31', end: '2027-01-06', timezone: 'America/Toronto' },
  league: { name: 'Invented league', season: 2026 },
  roster: {
    teamName: 'Invented team',
    returnedCount: 3,
    contextUnverified: true,
    coverage: { kind: null, date: null, week: null },
    entries: ['first', 'second', 'third'].map((id) => ({
      id: `invented-${id}`,
      name: 'Same Name',
      positions: ['D'],
      slot: 'IR',
      team: null,
      affiliationUnverified: true,
      scheduleStatus: 'AFFILIATION_UNVERIFIED',
    })),
  },
  settings: null,
  schedule: null,
};
let current: unknown = view;
beforeEach(() => {
  current = view;
  window.history.replaceState(
    null,
    '',
    '/#access=fabricated-context-capability-12345678901234567890',
  );
  vi.stubGlobal(
    'fetch',
    vi.fn().mockImplementation((url: string) =>
      Promise.resolve({
        ok: true,
        json: async () =>
          url.endsWith('/status')
            ? { mode: 'private', yahoo: 'loaded', schedule: 'unavailable' }
            : current,
      }),
    ),
  );
});

it('keeps source qualifications factual when the manager changes the prepared review date', async () => {
  current = {
    ...view,
    roster: {
      ...view.roster,
      entries: view.roster.entries.map((entry) => ({
        ...entry,
        team: 'TOR',
        affiliationUnverified: false,
        scheduleStatus: 'MATCHED',
      })),
    },
    schedule: {
      start: '2026-12-31',
      end: '2027-01-06',
      timezone: 'America/Toronto',
      observedAt: '2026-12-30T12:00:00Z',
      issues: ['COVERAGE_UNVERIFIED'],
      teams: [],
      days: [
        {
          date: '2026-12-31',
          count: { state: 'incomplete', value: 1, reason: 'Invented partial source' },
          games: [
            {
              id: 'invented-game',
              away: 'MTL',
              home: 'TOR',
              time: '2027-01-01T00:30:00Z',
              state: 'SCHEDULED',
              upcomingEligible: true,
            },
          ],
        },
      ],
    },
  };
  const user = userEvent.setup();
  render(<App />);
  await screen.findAllByRole('button', { name: 'Inspect Same Name' });
  await user.click(screen.getByRole('button', { name: '04 Compare Players' }));
  await user.click(screen.getByRole('button', { name: 'Prepare comparison review' }));
  expect(screen.getByLabelText('Reason')).toHaveValue(
    'Shared game date observed; review prompt only, not a slot-capacity conflict.',
  );
  fireEvent.change(screen.getByLabelText('Review date'), { target: { value: '2027-01-02' } });
  const qualifications = screen.getByRole('complementary', {
    name: 'Referenced observation qualifications',
  });
  expect(within(qualifications).queryByText(/MTL @ TOR/)).not.toBeInTheDocument();
  expect(screen.getByLabelText('Reason')).toHaveValue(
    'Review observed team games and reported assignments; complete coverage and appearances remain unverified.',
  );
  await user.type(screen.getByLabelText('Review action'), 'Check assignment manually');
  await user.click(screen.getByRole('button', { name: 'Add review item' }));
  const item = screen.getByRole('article', { name: 'Review item 1' });
  expect(within(item).queryByText(/MTL @ TOR/)).not.toBeInTheDocument();
  expect(within(item).getAllByText(/Date coverage: unknown/)).toHaveLength(2);
  await user.click(screen.getByRole('button', { name: 'Reopen context for item 1' }));
  fireEvent.change(screen.getByLabelText('Comparison review date'), {
    target: { value: '2026-12-31' },
  });
  await user.click(screen.getByRole('button', { name: 'Prepare comparison review' }));
  fireEvent.change(screen.getByLabelText('Review action'), { target: { value: 'Check again' } });
  await user.click(screen.getByRole('button', { name: 'Add review item' }));
  await user.click(screen.getByRole('button', { name: 'Edit item 2' }));
  fireEvent.change(screen.getByLabelText('Review date'), { target: { value: '2027-01-02' } });
  expect(screen.getByLabelText('Reason')).toHaveValue(
    'Review observed team games and reported assignments; complete coverage and appearances remain unverified.',
  );
});
afterEach(() => vi.unstubAllGlobals());

it('prepares exact roster verification context and returns to the same player, date and planning window', async () => {
  const user = userEvent.setup();
  render(<App />);
  await screen.findAllByRole('button', { name: 'Inspect Same Name' });
  await user.click(screen.getByRole('button', { name: '03 My Roster' }));
  await user.click(screen.getByRole('button', { name: 'Prepare roster review' }));
  expect(screen.getByLabelText('Returned player')).toHaveValue('invented-first');
  expect(screen.getByLabelText('Review date')).toHaveValue('2026-12-31');
  expect(screen.getByLabelText('Reason')).toHaveValue(
    'Schedule coverage unavailable; verify reported affiliation or assignment in Yahoo.',
  );
  await user.type(screen.getByLabelText('Review action'), 'Verify reported assignment');
  fireEvent.change(screen.getByLabelText('Review date'), { target: { value: '2027-01-02' } });
  await user.click(screen.getByRole('button', { name: 'Add review item' }));
  await user.click(screen.getByRole('button', { name: 'Reopen context for item 1' }));
  expect(screen.getByRole('heading', { name: 'My Roster', level: 1 })).toBeVisible();
  expect(screen.getByText('invented-first', { exact: true })).toBeVisible();
  expect(
    screen.getByText('Review context: 2027-01-02 · 2026-12-31 – 2027-01-06 · America/Toronto'),
  ).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Prepare roster review' }));
  const item = screen.getByRole('article', { name: 'Review item 1' });
  expect(within(item).getByText('invented-first')).toBeVisible();
  expect(within(item).getByText('2027-01-02')).toBeVisible();
});

it('keeps an exact pair and date through selection, swaps, search, profile navigation and another week', async () => {
  const user = userEvent.setup();
  render(<App />);
  await screen.findAllByRole('button', { name: 'Inspect Same Name' });
  await user.click(screen.getByRole('button', { name: '04 Compare Players' }));
  expect(screen.getByRole('tab', { name: 'Schedule', selected: true })).toBeVisible();
  expect(
    within(screen.getByLabelText('First player')).getByRole('option', {
      name: 'Same Name · UNK · D · invented-first',
    }),
  ).toBeInTheDocument();
  await user.selectOptions(screen.getByLabelText('Second player'), 'invented-third');
  fireEvent.change(screen.getByLabelText('Comparison review date'), {
    target: { value: '2027-01-02' },
  });
  await user.click(screen.getByRole('button', { name: 'Prepare comparison review' }));
  expect(
    screen.getByText(/Compared pair: Same Name · invented-first \/ Same Name · invented-third/),
  ).toBeVisible();
  await user.click(screen.getByLabelText('Review action'));
  await user.paste('Check pair');
  await user.clear(screen.getByLabelText('Reason'));
  await user.paste('My reason');
  await user.click(screen.getByRole('button', { name: 'Add review item' }));
  await user.click(screen.getByRole('button', { name: 'Reopen context for item 1' }));
  expect(screen.getByLabelText('First player')).toHaveValue('invented-first');
  expect(screen.getByLabelText('Second player')).toHaveValue('invented-third');
  expect(screen.getByLabelText('Comparison review date')).toHaveValue('2027-01-02');
  await user.click(screen.getByRole('button', { name: 'Swap players' }));
  await user.selectOptions(screen.getByLabelText('Second player'), 'invented-second');
  await user.click(screen.getByLabelText('Find a comparison player'));
  await user.paste('hide all');
  await user.click(screen.getByRole('button', { name: 'Next comparison week' }));
  expect(screen.getByRole('button', { name: 'Prepare comparison review' })).toBeDisabled();
  await user.click(
    within(screen.getByRole('region', { name: 'First comparison player' })).getByRole('button', {
      name: 'View Same Name profile',
    }),
  );
  await user.click(screen.getByRole('button', { name: '02 Schedule Planner' }));
  await user.click(screen.getByRole('button', { name: 'Manual plan' }));
  const item = screen.getByRole('article', { name: 'Review item 1' });
  expect(within(item).getByText('invented-first')).toBeVisible();
  expect(within(item).getByText('invented-third')).toBeVisible();
  expect(within(item).getByText('2027-01-02')).toBeVisible();
  expect(within(item).getByText('My reason')).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Edit item 1' }));
  await user.clear(screen.getByLabelText('Review action'));
  await user.paste('Check both');
  await user.click(screen.getByRole('button', { name: 'Save review item' }));
  await user.click(screen.getByRole('button', { name: 'Mark item 1 reviewed' }));
  expect(within(item).getByText('Reviewed')).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Reopen context for item 1' }));
  expect(screen.getByLabelText('First player')).toHaveValue('invented-first');
  expect(screen.getByLabelText('Second player')).toHaveValue('invented-third');
  expect(screen.getByLabelText('Comparison review date')).toHaveValue('2027-01-02');
  expect(JSON.stringify(window.history.state)).not.toMatch(/invented-|2027-01|2026-12/);
  expect(window.location.hash).toBe('#comparison');
  expect(localStorage.length).toBe(0);
  expect(sessionStorage.length).toBe(0);
});

it('centers Yahoo-only review on the explicit planning window and prepares the selected Planner context without borrowing a new week', async () => {
  const user = userEvent.setup();
  render(<App />);
  await screen.findAllByRole('button', { name: 'Inspect Same Name' });
  expect(screen.getByRole('button', { name: /Select Thursday, December 31:/ })).toBeVisible();
  expect(screen.getByText(/Yahoo roster only: no schedule observations loaded/)).toBeVisible();
  await user.click(screen.getByRole('button', { name: '02 Schedule Planner' }));
  await user.click(screen.getByRole('button', { name: /Select Saturday, January 2:/ }));
  await user.selectOptions(screen.getByLabelText('Planner review player'), 'invented-second');
  const fetcher = vi.mocked(fetch);
  const reads = fetcher.mock.calls.length;
  await user.click(screen.getByRole('button', { name: 'Prepare Planner review' }));
  expect(screen.getByLabelText('Returned player')).toHaveValue('invented-second');
  expect(screen.getByLabelText('Review date')).toHaveValue('2027-01-02');
  await user.type(screen.getByLabelText('Review action'), 'Check assigned slot');
  await user.click(screen.getByRole('button', { name: 'Add review item' }));
  await user.click(screen.getByRole('button', { name: 'Next week' }));
  expect(screen.getByRole('button', { name: 'Prepare Planner review' })).toBeDisabled();
  expect(
    screen.getByText(/Context review unavailable for an unloaded alternate window/),
  ).toBeVisible();
  expect(
    within(screen.getByRole('article', { name: 'Review item 1' })).getByText('2027-01-02'),
  ).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Reopen context for item 1' }));
  expect(screen.getByLabelText('Planner review player')).toHaveValue('invented-second');
  expect(screen.getByRole('button', { name: /Select Saturday, January 2:/ })).toHaveAttribute(
    'aria-pressed',
    'true',
  );
  expect(fetcher.mock.calls).toHaveLength(reads);
  await user.click(screen.getByRole('button', { name: '04 Compare Players' }));
  expect(screen.getByRole('tab', { name: 'Schedule', selected: true })).toBeVisible();
  expect(screen.queryByLabelText('Statistics view')).not.toBeInTheDocument();
});

it.each(['roster', 'Planner', 'comparison'])(
  'retains partial, disputed, excluded and unplaced observation qualifications through the %s entry',
  async (origin) => {
    const game = {
      id: 'invented-eligible',
      away: 'MTL',
      home: 'TOR',
      time: '2027-01-01T00:30:00Z',
      state: 'SCHEDULED',
      upcomingEligible: true,
    };
    current = {
      ...view,
      roster: {
        ...view.roster,
        entries: view.roster.entries.map((entry) => ({
          ...entry,
          team: 'TOR',
          affiliationUnverified: false,
          scheduleStatus: 'MATCHED',
        })),
      },
      schedule: {
        start: '2026-12-31',
        end: '2027-01-06',
        timezone: 'America/Toronto',
        observedAt: '2026-12-30T12:00:00Z',
        issues: ['INVENTED_UNPLACED_WARNING'],
        teams: [
          {
            code: 'TOR',
            observedGames: 7,
            countComplete: false,
            backToBackComplete: false,
            uncertainDated: 2,
            unplaced: 1,
          },
        ],
        days: [
          {
            date: '2026-12-31',
            count: {
              state: 'incomplete',
              value: 7,
              reason: 'Invented partial source qualification',
            },
            games: [
              game,
              game,
              { ...game, id: 'invented-dispute' },
              { ...game, id: 'invented-dispute', state: 'POSTPONED', upcomingEligible: false },
              { ...game, id: 'invented-completed', state: 'FINAL', upcomingEligible: false },
              { ...game, id: 'invented-unplaced', time: null, upcomingEligible: undefined },
              { ...game, id: 'invented-excluded', upcomingEligible: false },
            ],
          },
        ],
      },
    };
    const user = userEvent.setup();
    render(<App />);
    await screen.findAllByRole('button', { name: 'Inspect Same Name' });
    await user.click(
      screen.getByRole('button', {
        name:
          origin === 'roster'
            ? '03 My Roster'
            : origin === 'comparison'
              ? '04 Compare Players'
              : '02 Schedule Planner',
      }),
    );
    await user.click(screen.getByRole('button', { name: `Prepare ${origin} review` }));
    await user.type(screen.getByLabelText('Review action'), 'Inspect observations in Yahoo');
    await user.click(screen.getByRole('button', { name: 'Add review item' }));
    const item = screen.getByRole('article', { name: 'Review item 1' });
    expect(within(item).getByText(/Invented partial source qualification/)).toBeVisible();
    const count = origin === 'comparison' ? 2 : 1;
    expect(within(item).getAllByText(/Scheduled observation; appearance unconfirmed/)).toHaveLength(
      count,
    );
    expect(
      within(item).getAllByText(/Conflicting game ID; no authoritative variant selected/),
    ).toHaveLength(count * 2);
    expect(within(item).getAllByText(/FINAL · source eligibility excluded/)).toHaveLength(count);
    expect(within(item).getAllByText(/Time unavailable \/ unverified/)).toHaveLength(count);
    expect(within(item).getAllByText(/SCHEDULED · source eligibility excluded/)).toHaveLength(
      count,
    );
    expect(within(item).getAllByText(/2 uncertain dated · 1 unplaced observations/)).toHaveLength(
      count,
    );
    expect(within(item).getByText('Source issues: INVENTED_UNPLACED_WARNING')).toBeVisible();
    await user.click(screen.getByRole('button', { name: 'Mark item 1 reviewed' }));
    expect(within(item).getByText(/Invented partial source qualification/)).toBeVisible();
  },
);

it('keeps observed profile schedule review central while allowing explicit inspection of unavailable performance panels', async () => {
  const user = userEvent.setup();
  render(<App />);
  await screen.findAllByRole('button', { name: 'Inspect Same Name' });
  await user.click(screen.getByRole('button', { name: /View Full Player Profile/ }));
  expect(screen.getByRole('heading', { name: 'Schedule Impact' })).toBeVisible();
  expect(screen.queryByRole('heading', { name: 'Recent Performance' })).not.toBeInTheDocument();
  expect(screen.queryByRole('heading', { name: 'Fantasy Outlook' })).not.toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Show unavailable performance panels' }));
  expect(screen.getByRole('heading', { name: 'Recent Performance' })).toBeVisible();
  expect(screen.getByRole('heading', { name: 'Fantasy Outlook' })).toBeVisible();
  expect(
    screen.getByText('Performance unavailable. No game-log provider is connected.'),
  ).toBeVisible();
});

it('discards unfinished prepared context on panel close and refuses a partially overlapping alternate window', async () => {
  const user = userEvent.setup();
  render(<App />);
  await screen.findAllByRole('button', { name: 'Inspect Same Name' });
  await user.click(screen.getByRole('button', { name: '04 Compare Players' }));
  await user.click(screen.getByRole('button', { name: 'Prepare comparison review' }));
  await user.type(screen.getByLabelText('Review action'), 'Unfinished action');
  await user.click(screen.getByRole('button', { name: 'Manual plan' }));
  await user.click(screen.getByRole('button', { name: 'Manual plan' }));
  expect(screen.getByLabelText('Returned player')).toHaveValue('');
  expect(screen.getByLabelText('Review action')).toHaveValue('');
  expect(screen.queryByText(/Compared pair:/)).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('Choose date'), { target: { value: '2027-01-02' } });
  expect(screen.getByRole('button', { name: 'Prepare Planner review' })).toBeDisabled();
  expect(
    screen.getByText(/Context review unavailable for an unloaded alternate window/),
  ).toBeVisible();
});

it.each([0, 1])('cannot prepare a pair from %s returned players', async (count) => {
  current = {
    ...view,
    roster: { ...view.roster, returnedCount: count, entries: view.roster.entries.slice(0, count) },
  };
  const user = userEvent.setup();
  render(<App />);
  await screen.findByRole('heading', { name: 'Weekly roster review' });
  await user.click(screen.getByRole('button', { name: '04 Compare Players' }));
  expect(
    screen.getByText(
      count
        ? 'At least two supplied players are required to compare.'
        : 'No players are available to compare.',
    ),
  ).toBeVisible();
  expect(
    screen.queryByRole('button', { name: 'Prepare comparison review' }),
  ).not.toBeInTheDocument();
});

it('can prepare identical Planner context repeatedly after adding an item or discarding an unfinished form', async () => {
  const user = userEvent.setup();
  render(<App />);
  await screen.findAllByRole('button', { name: 'Inspect Same Name' });
  await user.click(screen.getByRole('button', { name: '02 Schedule Planner' }));
  await user.click(screen.getByRole('button', { name: 'Prepare Planner review' }));
  await user.type(screen.getByLabelText('Review action'), 'First check');
  await user.click(screen.getByRole('button', { name: 'Add review item' }));
  await user.click(screen.getByRole('button', { name: 'Prepare Planner review' }));
  expect(screen.getByLabelText('Reason')).toHaveValue(
    'Schedule coverage unavailable; verify reported affiliation or assignment in Yahoo.',
  );
  await user.type(screen.getByLabelText('Review action'), 'Second check');
  await user.click(screen.getByRole('button', { name: 'Add review item' }));
  expect(screen.getAllByRole('article')).toHaveLength(2);
  await user.click(screen.getByRole('button', { name: 'Manual plan' }));
  await user.click(screen.getByRole('button', { name: 'Prepare Planner review' }));
  expect(screen.getByRole('region', { name: 'Manual plan' })).toBeVisible();
  expect(screen.getByLabelText('Review action')).toHaveValue('');
  expect(screen.getByLabelText('Returned player')).toHaveValue('invented-first');
});
