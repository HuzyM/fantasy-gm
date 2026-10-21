import { fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, it, vi } from 'vitest';
import App from '../src/App';

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

it('keeps the explicit Yahoo-only window across Planner and default Schedule comparison despite the browser clock', async () => {
  vi.useFakeTimers({ toFake: ['Date'] });
  vi.setSystemTime(new Date('2030-07-01T02:00:00Z'));
  const requests: string[] = [];
  const view = {
    mode: 'private',
    source: 'yahoo',
    provenance: ['Fabricated protocol only'],
    league: { name: 'Invented league', season: 2026 },
    planningWindow: { start: '2026-12-31', end: '2027-01-06', timezone: 'America/Toronto' },
    roster: {
      teamName: 'Invented team',
      returnedCount: 2,
      contextUnverified: true,
      coverage: { kind: null, date: null, week: null },
      entries: ['one', 'two'].map((id) => ({
        id,
        name: `Invented ${id}`,
        positions: ['C'],
        slot: 'C',
        team: 'TOR',
        affiliationUnverified: false,
        scheduleStatus: 'UNAVAILABLE',
      })),
    },
    schedule: null,
  };
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      requests.push(url);
      return {
        ok: true,
        json: async () =>
          url.endsWith('/status')
            ? { mode: 'private', yahoo: 'loaded', schedule: 'unavailable' }
            : view,
      };
    }),
  );
  window.history.replaceState(
    null,
    '',
    '/#access=synthetic-window-capability-12345678901234567890',
  );
  const user = userEvent.setup();
  render(<App />);
  await screen.findByRole('button', { name: 'Inspect Invented one' });
  const loadedRequests = requests.length;
  await user.click(screen.getByRole('button', { name: '02 Schedule Planner' }));
  const week = screen.getByRole('region', { name: 'Planner week' });
  expect(within(week).getAllByRole('button')).toHaveLength(7);
  expect(within(week).getAllByText('Unknown')).toHaveLength(7);
  expect(screen.getByText('Dec 31 – Jan 6, 2027')).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Compare players' }));
  expect(screen.getByRole('tab', { name: 'Schedule' })).toHaveAttribute('aria-selected', 'true');
  expect(screen.getByRole('region', { name: 'Weekly game comparison' })).toHaveTextContent(
    'Dec 31 – Jan 6, 2027',
  );
  expect(screen.getByText('Shared game dates: Unknown')).toBeVisible();
  await user.click(screen.getByRole('button', { name: '02 Schedule Planner' }));
  fireEvent.change(screen.getByLabelText('Choose date'), { target: { value: '2027-01-02' } });
  expect(screen.getByText('Jan 2 – Jan 8, 2027')).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Compare players' }));
  expect(screen.getByRole('region', { name: 'Weekly game comparison' })).toHaveTextContent(
    'Jan 2 – Jan 8, 2027',
  );
  expect(requests).toHaveLength(loadedRequests);
  expect(window.location.hash).toBe('#comparison');
  expect(JSON.stringify(window.history.state)).not.toMatch(/2027|Invented|one|two/);
});
