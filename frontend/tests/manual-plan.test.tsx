import { act, fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import App from '../src/App';

const view = {
  mode: 'private',
  source: 'yahoo',
  planningWindow: { start: '2026-12-31', end: '2027-01-06', timezone: 'America/Toronto' },
  provenance: ['Fabricated manual plan protocol'],
  league: { name: 'Fabricated league', season: 2026 },
  roster: {
    teamName: 'Fabricated roster',
    returnedCount: 2,
    contextUnverified: true,
    coverage: { kind: null, date: null, week: null },
    entries: ['fabricated-first', 'fabricated-second'].map((id) => ({
      id,
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
beforeEach(() =>
  window.history.replaceState(null, '', '/#access=fabricated-plan-capability-12345678901234567890'),
);
afterEach(() => vi.unstubAllGlobals());
function transport(current: () => unknown = () => view) {
  const fetcher = vi.fn().mockImplementation((url: string) =>
    Promise.resolve({
      ok: true,
      json: async () =>
        url.endsWith('/status')
          ? { mode: 'private', yahoo: 'loaded', schedule: 'unavailable' }
          : current(),
    }),
  );
  vi.stubGlobal('fetch', fetcher);
  return fetcher;
}
async function openPlan(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole('button', { name: '02 Schedule Planner' }));
  await user.click(screen.getByRole('button', { name: 'Manual plan' }));
  return screen.getByRole('region', { name: 'Manual plan' });
}
it('records an exact returned player and loaded date for Yahoo-only verification without a game', async () => {
  const fetcher = transport();
  const user = userEvent.setup();
  render(<App />);
  await screen.findAllByRole('button', { name: 'Inspect Same Name' });
  const plan = await openPlan(user);
  expect(within(plan).getByText(/20 minutes/)).toBeVisible();
  await user.selectOptions(screen.getByLabelText('Returned player'), 'fabricated-second');
  fireEvent.change(screen.getByLabelText('Review date'), { target: { value: '2027-01-06' } });
  await user.type(screen.getByLabelText('Review action'), 'Check reported affiliation');
  await user.type(screen.getByLabelText('Reason'), 'Affiliation unavailable; check in Yahoo');
  const reads = fetcher.mock.calls.length;
  await user.click(screen.getByRole('button', { name: 'Add review item' }));
  const item = screen.getByRole('article', { name: 'Review item 1' });
  expect(within(item).getByText('fabricated-second')).toBeVisible();
  expect(within(item).getByText('2027-01-06')).toBeVisible();
  expect(within(item).getByText('Pending')).toBeVisible();
  expect(within(item).getByText(/Schedule coverage unavailable/)).toBeVisible();
  expect(fetcher.mock.calls).toHaveLength(reads);
});
it('refuses unknown players, missing text and dates outside the loaded window', async () => {
  transport();
  const user = userEvent.setup();
  render(<App />);
  await screen.findAllByRole('button', { name: 'Inspect Same Name' });
  await openPlan(user);
  await user.click(screen.getByRole('button', { name: 'Add review item' }));
  expect(screen.getByRole('status')).toHaveTextContent('Choose a returned player');
  await user.selectOptions(screen.getByLabelText('Returned player'), 'fabricated-second');
  await user.type(screen.getByLabelText('Review action'), 'Verify');
  await user.type(screen.getByLabelText('Reason'), 'Unknown coverage');
  for (const date of ['2026-12-30', '2027-01-07', '']) {
    fireEvent.change(screen.getByLabelText('Review date'), { target: { value: date } });
    await user.click(screen.getByRole('button', { name: 'Add review item' }));
    expect(screen.queryByRole('article')).not.toBeInTheDocument();
  }
  expect(screen.getByLabelText('Review date')).toHaveAttribute('min', '2026-12-31');
  expect(screen.getByLabelText('Review date')).toHaveAttribute('max', '2027-01-06');
});
it.each(['source replacement', 'session replacement', 'disconnect', 'server restart', 'reload'])(
  'discards plan items and acknowledgement after %s, including history navigation',
  async (boundary) => {
    let current = view;
    const fetcher = transport(() => current);
    const user = userEvent.setup();
    const mounted = render(<App />);
    await screen.findAllByRole('button', { name: 'Inspect Same Name' });
    await openPlan(user);
    await user.selectOptions(screen.getByLabelText('Returned player'), 'fabricated-first');
    await user.type(screen.getByLabelText('Review action'), 'Fabricated private action');
    await user.type(screen.getByLabelText('Reason'), 'Fabricated private reason');
    await user.click(screen.getByRole('button', { name: 'Add review item' }));
    await user.click(screen.getByRole('button', { name: 'Record no action needed' }));
    if (boundary === 'source replacement') {
      current = { ...view, provenance: ['Fabricated replacement observation'] };
      fireEvent.focus(window);
      await screen.findByRole('button', { name: 'Manual plan' });
    } else if (boundary === 'reload') {
      mounted.unmount();
      render(<App />);
      await screen.findByRole('heading', { name: 'Private session unavailable' });
    } else if (boundary === 'disconnect') {
      await user.click(screen.getByRole('button', { name: '06 Connections' }));
      await user.click(screen.getByRole('button', { name: 'Disconnect local session' }));
      await screen.findByRole('heading', { name: 'Private session unavailable' });
    } else if (boundary === 'server restart') {
      fetcher.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ mode: 'private', yahoo: 'expired' }),
      });
      fireEvent.focus(window);
      await screen.findByRole('heading', { name: 'Private session unavailable' });
    }
    if (boundary !== 'source replacement') {
      act(() => {
        window.location.hash = '#access=fabricated-reopened-capability-12345678901234567890';
        fireEvent(window, new HashChangeEvent('hashchange'));
      });
      await screen.findAllByRole('button', { name: 'Inspect Same Name' });
    }
    await openPlan(user);
    expect(screen.queryByText('Fabricated private action')).not.toBeInTheDocument();
    expect(screen.queryByRole('article')).not.toBeInTheDocument();
    expect(screen.getByText('Review pending.')).toBeVisible();
    act(() => window.history.back());
    expect(screen.queryByText('Fabricated private reason')).not.toBeInTheDocument();
    expect(JSON.stringify(window.history.state)).not.toContain('fabricated-first');
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
  },
);
it('plan interactions do not extend the existing twenty-minute private lifetime', async () => {
  vi.useFakeTimers();
  transport();
  try {
    render(<App />);
    await act(async () => {});
    fireEvent.click(screen.getByRole('button', { name: '02 Schedule Planner' }));
    fireEvent.click(screen.getByRole('button', { name: 'Manual plan' }));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(19 * 60 * 1000);
    });
    fireEvent.change(screen.getByLabelText('Returned player'), {
      target: { value: 'fabricated-first' },
    });
    fireEvent.change(screen.getByLabelText('Review action'), {
      target: { value: 'Private near-expiry action' },
    });
    fireEvent.change(screen.getByLabelText('Reason'), {
      target: { value: 'Private near-expiry reason' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Add review item' }));
    expect(screen.getByRole('article')).toBeVisible();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(60 * 1000);
    });
    expect(screen.getByRole('heading', { name: 'Private session unavailable' })).toBeVisible();
    expect(screen.queryByText('Private near-expiry action')).not.toBeInTheDocument();
    act(() => window.history.back());
    expect(screen.queryByText('Private near-expiry reason')).not.toBeInTheDocument();
  } finally {
    vi.clearAllTimers();
    vi.useRealTimers();
  }
});
it.each([
  ['absent', null],
  ['present', view.roster],
] as const)(
  'does not expose private plan affordance or contents in a public PuckAPI session (roster %s)',
  async (_, roster) => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((url: string) =>
        Promise.resolve({
          ok: true,
          json: async () =>
            url.endsWith('/status')
              ? { mode: 'synthetic' }
              : { ...view, mode: 'synthetic', source: 'puckapi', roster, league: null },
        }),
      ),
    );
    window.history.replaceState(null, '', '/#overview');
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText('Public NHL schedule');
    await user.click(screen.getByRole('button', { name: '02 Schedule Planner' }));
    expect(screen.queryByRole('button', { name: 'Manual plan' })).not.toBeInTheDocument();
    expect(screen.queryByRole('region', { name: 'Manual plan' })).not.toBeInTheDocument();
    expect(screen.queryByText(/Private sessions last 20 minutes/)).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Returned player')).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: 'Record no action needed' }),
    ).not.toBeInTheDocument();
  },
);
it('permits no-action acknowledgement for a private Yahoo session with an empty owned roster', async () => {
  transport(() => ({ ...view, roster: { ...view.roster, returnedCount: 0, entries: [] } }));
  const user = userEvent.setup();
  render(<App />);
  await screen.findByText('Fabricated league');
  const plan = await openPlan(user);
  expect(
    within(plan).getByText('No returned owned-roster player is available for a review item.'),
  ).toBeVisible();
  expect(screen.queryByLabelText('Returned player')).not.toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Record no action needed' }));
  expect(within(plan).getByText('No action needed acknowledged.')).toBeVisible();
});
it.each(['response', 'failure'] as const)(
  'a stale private %s cannot restore discarded plan content',
  async (outcome) => {
    let phase = 'initial';
    let resolveOld: (value: unknown) => void = () => {};
    let rejectOld: (reason: Error) => void = () => {};
    const pending = new Promise((resolve, reject) => {
      resolveOld = resolve;
      rejectOld = reject;
    });
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((url: string) => {
        if (phase === 'old' && url.endsWith('/view')) return pending;
        return Promise.resolve({
          ok: true,
          json: async () =>
            url.endsWith('/status')
              ? { mode: 'private', yahoo: 'loaded', schedule: 'unavailable' }
              : view,
        });
      }),
    );
    const user = userEvent.setup();
    render(<App />);
    await screen.findAllByRole('button', { name: 'Inspect Same Name' });
    await openPlan(user);
    await user.selectOptions(screen.getByLabelText('Returned player'), 'fabricated-first');
    await user.type(screen.getByLabelText('Review action'), 'Old private review');
    await user.type(screen.getByLabelText('Reason'), 'Old private reason');
    await user.click(screen.getByRole('button', { name: 'Add review item' }));
    phase = 'old';
    await act(async () => {
      fireEvent.focus(window);
    });
    phase = 'replacement';
    act(() => {
      window.location.hash = '#access=fabricated-replacement-capability-12345678901234567890';
      fireEvent(window, new HashChangeEvent('hashchange'));
    });
    await screen.findAllByRole('button', { name: 'Inspect Same Name' });
    await act(async () => {
      if (outcome === 'failure') rejectOld(new Error('Fabricated stale failure'));
      else resolveOld({ ok: true, json: async () => view });
    });
    await openPlan(user);
    expect(screen.queryByRole('article')).not.toBeInTheDocument();
    expect(screen.queryByText('Old private review')).not.toBeInTheDocument();
    expect(screen.getByText('Review pending.')).toBeVisible();
  },
);
it('edits, acknowledges, reopens and removes an item while keeping its exact original context', async () => {
  transport();
  const user = userEvent.setup();
  render(<App />);
  await screen.findAllByRole('button', { name: 'Inspect Same Name' });
  await openPlan(user);
  await user.selectOptions(screen.getByLabelText('Returned player'), 'fabricated-second');
  await user.type(screen.getByLabelText('Review action'), 'Check assignment');
  await user.type(screen.getByLabelText('Reason'), 'Reported slot is unverified');
  await user.click(screen.getByRole('button', { name: 'Add review item' }));
  await user.click(screen.getByRole('button', { name: 'Edit item 1' }));
  expect(screen.getByLabelText('Returned player')).toBeDisabled();
  await user.clear(screen.getByLabelText('Review action'));
  await user.type(screen.getByLabelText('Review action'), 'Check in Yahoo');
  fireEvent.change(screen.getByLabelText('Review date'), { target: { value: '2027-01-02' } });
  await user.click(screen.getByRole('button', { name: 'Save review item' }));
  await user.click(screen.getByRole('button', { name: 'Mark item 1 reviewed' }));
  let item = screen.getByRole('article', { name: 'Review item 1' });
  expect(within(item).getByText('Reviewed')).toBeVisible();
  expect(within(item).getByText(/Schedule coverage unavailable/)).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Return item 1 to pending' }));
  await user.click(screen.getByRole('button', { name: 'Next week' }));
  await user.type(screen.getByRole('searchbox'), 'hide everything');
  item = screen.getByRole('article', { name: 'Review item 1' });
  expect(within(item).getByText('2027-01-02')).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Reopen player for item 1' }));
  expect(screen.getByRole('heading', { name: 'Same Name', level: 1 })).toBeVisible();
  expect(screen.getByText('fabricated-second')).toBeVisible();
  const plan = await openPlan(user);
  expect(within(plan).getByText('Check in Yahoo')).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Remove item 1' }));
  expect(screen.queryByRole('article')).not.toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Record no action needed' }));
  expect(within(plan).getByText('No action needed acknowledged.')).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Return review to pending' }));
  expect(within(plan).getByText('Review pending.')).toBeVisible();
});
