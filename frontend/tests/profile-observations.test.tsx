import { render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import PlayerProfile from '../src/screens/PlayerProfile';
import { parseView, providerPlayers } from '../src/api';
it('renders the observed October date instead of the demo fixture month', () => {
  const view = parseView({
    mode: 'private',
    source: 'yahoo',
    provenance: ['Synthetic protocol input only'],
    league: { name: 'Synthetic league', season: 2026 },
    roster: {
      teamName: 'Synthetic team',
      returnedCount: 1,
      contextUnverified: true,
      coverage: { kind: null, date: null, week: null },
      entries: [
        {
          id: 'synthetic-id',
          name: 'Synthetic Player',
          positions: ['D'],
          slot: 'D',
          team: 'COL',
          affiliationUnverified: false,
          scheduleStatus: 'MATCHED',
        },
      ],
    },
    schedule: {
      start: '2026-10-19',
      end: '2026-10-25',
      timezone: 'America/Toronto',
      observedAt: '2026-10-18T00:00:00Z',
      issues: ['COVERAGE_UNVERIFIED'],
      days: [
        {
          date: '2026-10-19',
          count: { state: 'incomplete', value: 1, reason: 'Coverage unverified' },
          games: [
            {
              id: 'synthetic-game',
              away: 'COL',
              home: 'STL',
              time: '2026-10-19T23:00:00Z',
              state: 'SCHEDULED',
            },
          ],
        },
      ],
      teams: [],
    },
  });
  render(
    <PlayerProfile
      search=""
      players={providerPlayers(view)}
      selectedId="synthetic-id"
      onNavigate={vi.fn()}
      onNotice={vi.fn()}
      local={{ view, state: 'private', disconnect: async () => {} }}
    />,
  );
  expect(screen.getByText('Oct 19')).toBeVisible();
  expect(screen.queryByText('Dec 19')).not.toBeInTheDocument();
});
