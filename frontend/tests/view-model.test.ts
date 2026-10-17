import { describe, expect, it } from 'vitest';
import { describeDatum, shiftWeek, filterPlayers } from '../src/view-model';

describe('data certainty presentation', () => {
  it('preserves a known zero without promoting incomplete coverage to a confirmed total', () => {
    expect(describeDatum({ state: 'verified', value: 0 })).toEqual({ text: '0', note: undefined });
    expect(describeDatum({ state: 'incomplete', value: 0, reason: 'Total unknown' })).toEqual({
      text: '0 observed',
      note: 'Total unknown',
    });
  });
  it('does not turn unknown or unsupported values into zero', () => {
    expect(describeDatum({ state: 'unknown', reason: 'Not supplied' })).toEqual({
      text: 'Unknown',
      note: 'Not supplied',
    });
    expect(describeDatum({ state: 'unsupported', reason: 'No projections source' })).toEqual({
      text: 'Unavailable',
      note: 'No projections source',
    });
  });
});

describe('Overview selection', () => {
  it('moves week windows across year and leap-day boundaries without using local DST arithmetic', () => {
    expect(shiftWeek('2026-12-28', 1)).toBe('2027-01-04');
    expect(shiftWeek('2024-02-26', 1)).toBe('2024-03-04');
  });
  it('combines case-insensitive search with a position group and leaves the source intact', () => {
    const players = [
      { id: 'a', name: 'Cale Makar', team: 'COL', group: 'defense' },
      { id: 'b', name: 'Nathan MacKinnon', team: 'COL', group: 'forwards' },
    ] as const;
    expect(filterPlayers(players, 'COL', 'defense').map((p) => p.id)).toEqual(['a']);
    expect(filterPlayers(players, '  makar ', 'all').map((p) => p.id)).toEqual(['a']);
    expect(players).toHaveLength(2);
  });
});
