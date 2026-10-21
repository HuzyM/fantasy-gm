import { describe, expect, it } from 'vitest';
import { parseView, providerPlayers, scheduleDays } from '../src/api';
const response = () => ({
  mode: 'private',
  source: 'yahoo',
  planningWindow: { start: '2026-10-19', end: '2026-10-25', timezone: 'America/Toronto' },
  provenance: ['Reported roster; coverage unverified'],
  league: { name: 'Synthetic test league', season: 2026 },
  roster: {
    teamName: 'Synthetic test team',
    returnedCount: 1,
    contextUnverified: true,
    coverage: { kind: null, date: null, week: null },
    entries: [
      {
        id: 'synthetic-private-id',
        name: 'Cale Makar',
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
});
describe('local display adapter', () => {
  it.each([
    { start: '2026-02-30', end: '2026-03-08', timezone: 'America/Toronto' },
    { start: '2026-12-31', end: '2027-01-07', timezone: 'America/Toronto' },
    { start: '2026-12-31', end: '2027-01-05', timezone: 'America/Toronto' },
    { start: '2026-12-31', end: '2027-01-06', timezone: 'Asia/Tokyo' },
  ])(
    'rejects malformed or conflicting planning window %s with a sanitized failure',
    (planningWindow) => {
      expect(() => parseView({ ...response(), planningWindow })).toThrow(
        'Local service response unavailable',
      );
    },
  );
  it('never guesses an NHL photo identity, injury, statistic, number or appearance from a Yahoo name/slot', () => {
    const view = parseView(response());
    const player = providerPlayers(view)[0]!;
    expect(player.nhlId).toBeUndefined();
    expect(player.number).toBeUndefined();
    expect(player.injury.state).toBe('unknown');
    expect(player.weeklyPoints.state).toBe('unsupported');
    expect(player.rosterSlot).toEqual({ state: 'verified', value: 'IR' });
    expect(player.nextGame).toBe('Unavailable');
    expect(player.stats).toEqual([]);
  });
  it('keeps absent schedule dates unknown rather than zero and does not reuse fixtures', () => {
    const days = scheduleDays('2026-10-19', parseView(response()));
    expect(days).toHaveLength(7);
    expect(days.every((day) => day.count.state === 'unknown' && !day.games.length)).toBe(true);
  });
  it('rejects malformed provider boundaries without serializing the supplied body in its error', () => {
    const duplicate = response();
    duplicate.roster.entries.push({ ...duplicate.roster.entries[0]! });
    expect(() => parseView(duplicate)).toThrow('Local service response unavailable');
    expect(() => parseView({ ...response(), mode: 'synthetic' })).toThrow(
      'Local service response unavailable',
    );
    expect(() => parseView({ ...response(), mode: 'live-secret-test' })).toThrow(
      'Local service response unavailable',
    );
    expect(() =>
      parseView({ ...response(), roster: { entries: [{ name: 'SECRET TEST INPUT' }] } }),
    ).toThrow('Local service response unavailable');
  });
});
