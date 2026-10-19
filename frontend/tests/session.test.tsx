import { StrictMode } from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import App from '../src/App';
const privateResponse = {
  mode: 'private',
  source: 'yahoo',
  provenance: ['Synthetic protocol test only'],
  league: { name: 'Synthetic private test league', season: 2026 },
  roster: {
    teamName: 'Synthetic private test team',
    returnedCount: 1,
    contextUnverified: true,
    coverage: { kind: null, date: null, week: null },
    entries: [
      {
        id: 'synthetic-private-id',
        name: 'Synthetic Private Player',
        positions: ['D'],
        slot: 'IR',
        team: 'COL',
        affiliationUnverified: true,
        scheduleStatus: 'AFFILIATION_UNVERIFIED',
      },
    ],
  },
  settings: null,
  schedule: null,
};
beforeEach(() =>
  window.history.replaceState(
    null,
    '',
    '/#access=synthetic-test-capability-1234567890123456789012345',
  ),
);
afterEach(() => vi.unstubAllGlobals());
describe('synthetic tests of private transport boundaries', () => {
  it('recovers a public observation after a transient loopback failure without restoring private capability', async () => {
    window.history.replaceState(null, '', '/#overview');
    let available = true;
    const publicView = {
      ...privateResponse,
      mode: 'synthetic',
      source: 'puckapi',
      league: null,
      roster: null,
      schedule: null,
    };
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((url: string) =>
        available
          ? Promise.resolve({
              ok: true,
              json: async () =>
                url.endsWith('/status')
                  ? { mode: 'synthetic', yahoo: 'disconnected', schedule: 'observed' }
                  : publicView,
            })
          : Promise.reject(new Error('Synthetic local outage')),
      ),
    );
    render(<App />);
    await waitFor(() =>
      expect(document.querySelector('.screen-content')).toHaveAttribute('data-source', 'public'),
    );
    available = false;
    fireEvent.focus(window);
    await screen.findByRole('heading', { name: 'Local observation unavailable' });
    available = true;
    fireEvent.focus(window);
    await waitFor(() =>
      expect(document.querySelector('.screen-content')).toHaveAttribute('data-source', 'public'),
    );
    expect(screen.queryByText('Cale Makar')).not.toBeInTheDocument();
  });
  it('removes the bootstrap fragment, uses a header and displays only supplied observations', async () => {
    const fetcher = vi.fn().mockImplementation((url: string) =>
      Promise.resolve({
        ok: true,
        json: async () =>
          url.endsWith('/status')
            ? { mode: 'private', yahoo: 'loaded', schedule: 'unavailable' }
            : privateResponse,
      }),
    );
    vi.stubGlobal('fetch', fetcher);
    render(
      <StrictMode>
        <App />
      </StrictMode>,
    );
    await screen.findByRole('button', { name: /^Inspect Synthetic Private Player$/ });
    expect(window.location.hash).not.toContain('access');
    expect(document.body.textContent).not.toContain('synthetic-test-capability');
    expect(screen.queryByText('Cale Makar')).not.toBeInTheDocument();
    expect(screen.queryByText('DEMO · SYNTHETIC DATA')).not.toBeInTheDocument();
    const call = fetcher.mock.calls.find((args) => args[0] === '/api/view')!;
    expect(call[1].headers.Authorization).toBe(
      'Bearer synthetic-test-capability-1234567890123456789012345',
    );
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
    expect(document.cookie).toBe('');
    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: 'View Full Player Profile →' }));
    expect(window.location.hash).toBe('#profile');
    expect(window.location.href).not.toContain('synthetic-private-id');
    expect(
      screen.getByRole('heading', { name: 'Synthetic Private Player', level: 1 }),
    ).toBeVisible();
    expect(document.querySelectorAll('.performance-column')).toHaveLength(0);
    await user.click(screen.getByRole('button', { name: '05 League' }));
    expect(screen.getByText(/No sample scores are substituted/)).toBeVisible();
    expect(screen.queryByText('Northern Ice')).not.toBeInTheDocument();
    await user.type(screen.getByRole('searchbox'), 'synthetic private query');
    fetcher.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ mode: 'private', yahoo: 'expired', schedule: 'unavailable' }),
    });
    fireEvent.focus(window);
    await screen.findByRole('heading', { name: 'Private session unavailable' });
    expect(screen.getByRole('searchbox')).toHaveValue('');
    expect(screen.queryByText('Synthetic private test league')).not.toBeInTheDocument();
  });
  it('does not resurrect a private display from an in-flight response after page exit', async () => {
    let resolveView: (value: unknown) => void = () => {};
    const pending = new Promise<unknown>((resolve) => {
      resolveView = resolve;
    });
    const fetcher = vi.fn().mockImplementation((url: string) =>
      Promise.resolve({
        ok: true,
        json: () =>
          url.endsWith('/status')
            ? Promise.resolve({ mode: 'private', yahoo: 'loaded', schedule: 'unavailable' })
            : pending,
      }),
    );
    vi.stubGlobal('fetch', fetcher);
    render(<App />);
    await waitFor(() =>
      expect(fetcher.mock.calls.some((args) => args[0] === '/api/view')).toBe(true),
    );
    fireEvent(window, new Event('pagehide'));
    await screen.findByRole('heading', { name: 'Private session unavailable' });
    await act(async () => resolveView(privateResponse));
    expect(screen.getByRole('heading', { name: 'Private session unavailable' })).toBeVisible();
    expect(screen.queryByText('Synthetic Private Player')).not.toBeInTheDocument();
  });
  it('clears the prior private display when a restarted server rejects its capability despite loaded status', async () => {
    const fetcher = vi.fn().mockImplementation((url: string) =>
      Promise.resolve({
        ok: true,
        json: async () =>
          url.endsWith('/status')
            ? { mode: 'private', yahoo: 'loaded', schedule: 'unavailable' }
            : privateResponse,
      }),
    );
    vi.stubGlobal('fetch', fetcher);
    render(<App />);
    await screen.findByRole('button', { name: /^Inspect Synthetic Private Player$/ });
    fetcher.mockImplementation((url: string) =>
      Promise.resolve(
        url.endsWith('/status')
          ? {
              ok: true,
              json: async () => ({ mode: 'private', yahoo: 'loaded', schedule: 'unavailable' }),
            }
          : { ok: false, status: 401, json: async () => ({ error: 'Session unavailable' }) },
      ),
    );
    fireEvent.focus(window);
    await screen.findByRole('heading', { name: 'Private session unavailable' });
    expect(screen.queryByText('Synthetic Private Player')).not.toBeInTheDocument();
    expect(screen.queryByText('Cale Makar')).not.toBeInTheDocument();
  });
  it('fails closed when the private session is unavailable; it never substitutes the demo', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        json: async () => ({ error: 'Session unavailable' }),
      }),
    );
    render(<App />);
    await screen.findByRole('heading', { name: 'Private session unavailable' });
    expect(screen.queryByText('Cale Makar')).not.toBeInTheDocument();
    expect(screen.queryByText('Synthetic Private Player')).not.toBeInTheDocument();
  });
  it('discards the private display on disconnect without a provider write or synthetic fallback', async () => {
    const fetcher = vi.fn().mockImplementation((url: string) =>
      Promise.resolve({
        ok: true,
        json: async () =>
          url.endsWith('/status')
            ? { mode: 'private', yahoo: 'loaded', schedule: 'unavailable' }
            : privateResponse,
      }),
    );
    vi.stubGlobal('fetch', fetcher);
    const user = userEvent.setup();
    render(<App />);
    await screen.findByRole('button', { name: /^Inspect Synthetic Private Player$/ });
    await user.click(screen.getByRole('button', { name: '06 Connections' }));
    await user.click(screen.getByRole('button', { name: 'Disconnect local session' }));
    await waitFor(() =>
      expect(screen.getByRole('heading', { name: 'Private session unavailable' })).toBeVisible(),
    );
    expect(screen.queryByText('Synthetic Private Player')).not.toBeInTheDocument();
    expect(fetcher.mock.calls.find((args) => args[0] === '/api/disconnect')?.[1].method).toBe(
      'POST',
    );
  });
});
