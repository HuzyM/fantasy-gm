import { fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, it, vi } from 'vitest';
import App from '../src/App';

afterEach(() => vi.unstubAllGlobals());

async function review(days: unknown[] = []) {
  const view = {
    mode: 'private',
    source: 'yahoo',
    provenance: ['Fabricated coverage protocol'],
    league: { name: 'Invented league', season: 2026 },
    planningWindow: { start: '2026-12-31', end: '2027-01-06', timezone: 'America/Toronto' },
    roster: {
      teamName: 'Invented team',
      returnedCount: 2,
      contextUnverified: true,
      coverage: { kind: null, date: null, week: null },
      entries: ['First', 'Second'].map((name, index) => ({
        id: `fabricated-${index}`,
        name: `Invented ${name}`,
        positions: ['C'],
        slot: 'C',
        team: index ? 'MTL' : 'TOR',
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
      days,
    },
  };
  const requests: string[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      requests.push(url);
      return {
        ok: true,
        json: async () =>
          url.endsWith('/status')
            ? { mode: 'private', yahoo: 'loaded', schedule: 'observed' }
            : view,
      };
    }),
  );
  window.history.replaceState(
    null,
    '',
    '/#access=synthetic-coverage-capability-12345678901234567890',
  );
  const user = userEvent.setup();
  render(<App />);
  await screen.findByRole('button', { name: 'Inspect Invented First' });
  return { user, requests };
}

it('keeps fully unloaded aggregate opportunities unknown in Comparison and the roster matrix', async () => {
  const { user, requests } = await review();
  await user.click(screen.getByRole('button', { name: '04 Compare Players' }));
  await user.click(screen.getByRole('button', { name: 'Next comparison week' }));
  const week = screen.getByRole('region', { name: 'Weekly game comparison' });
  expect(within(week).getByText('Jan 7 – Jan 13, 2027')).toBeVisible();
  for (const name of ['First', 'Second']) {
    const summary = within(week).getByRole('region', { name: `Invented ${name} game summary` });
    expect(within(summary).getAllByText('Unknown', { selector: 'dd' })).toHaveLength(2);
  }
  expect(within(week).getByText('Shared game dates: Unknown')).toBeVisible();
  expect(within(week).getAllByText('Coverage unknown')).toHaveLength(14);
  expect(within(week).queryByText(/Required affiliation join unavailable/)).not.toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: '02 Schedule Planner' }));
  fireEvent.change(screen.getByLabelText('Choose date'), { target: { value: '2027-01-07' } });
  await user.click(screen.getByRole('tab', { name: 'Roster week' }));
  const row = screen.getByRole('row', { name: /Invented First/ });
  const cells = within(row).getAllByRole('cell');
  expect(cells.slice(-2).map((cell) => cell.textContent)).toEqual(['Unknown', 'Unknown']);
  expect(within(row).getAllByText('Coverage unknown')).toHaveLength(7);
  expect(requests).toEqual(['/api/status', '/api/view']);
});

const partialDays = [
  {
    date: '2026-12-31',
    count: { state: 'incomplete', value: 1, reason: 'Fabricated partial observation' },
    games: [
      {
        id: 'first',
        away: 'MTL',
        home: 'TOR',
        time: '2027-01-01T00:30:00Z',
        state: 'SCHEDULED',
        upcomingEligible: true,
      },
    ],
  },
  {
    date: '2027-01-01',
    count: { state: 'incomplete', value: 1, reason: 'Fabricated partial observation' },
    games: [
      {
        id: 'second',
        away: 'MTL',
        home: 'TOR',
        time: '2027-01-02T00:30:00Z',
        state: 'SCHEDULED',
        upcomingEligible: true,
      },
    ],
  },
];

it.each([
  {
    label: 'loaded partial observations',
    start: '2026-12-31',
    days: partialDays,
    scheduled: 2,
    pairs: 1,
    shared: 2,
  },
  {
    label: 'overlap with loaded observations',
    start: '2026-12-30',
    days: partialDays,
    scheduled: 2,
    pairs: 1,
    shared: 2,
  },
  {
    label: 'one loaded date overlapping without qualifying games',
    start: '2027-01-06',
    days: partialDays,
    scheduled: 0,
    pairs: 0,
    shared: 0,
  },
  {
    label: 'loaded empty response with no returned days',
    start: '2026-12-31',
    days: [],
    scheduled: 0,
    pairs: 0,
    shared: 0,
  },
])(
  'retains numeric observed opportunities for $label without claiming complete totals',
  async ({ start, days, scheduled, pairs, shared }) => {
    const { user, requests } = await review(days);
    await user.click(screen.getByRole('button', { name: '02 Schedule Planner' }));
    fireEvent.change(screen.getByLabelText('Choose date'), { target: { value: start } });
    await user.click(screen.getByRole('tab', { name: 'Roster week' }));
    const row = screen.getByRole('row', { name: /Invented First/ });
    const cells = within(row).getAllByRole('cell');
    expect(cells.at(-2)?.textContent).toBe(`${scheduled}observed; total unknown`);
    expect(cells.at(-1)?.textContent).toBe(
      `${pairs}${pairs === 1 ? 'date pair' : 'date pairs'} observed`,
    );
    await user.click(screen.getByRole('button', { name: 'Compare players' }));
    for (const name of ['First', 'Second']) {
      const summary = screen.getByRole('region', { name: `Invented ${name} game summary` });
      expect(
        within(summary)
          .getAllByRole('definition')
          .map((value) => value.textContent),
      ).toEqual([String(scheduled), String(pairs)]);
      expect(
        within(summary).getByText('Loaded observations; complete totals unknown.'),
      ).toBeVisible();
    }
    expect(screen.getByText(`Shared game dates: ${shared}`)).toBeVisible();
    expect(requests).toEqual(['/api/status', '/api/view']);
  },
);
