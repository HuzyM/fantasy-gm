import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { WeekSchedule } from '../src/components/WeekSchedule';
import type { DaySchedule } from '../src/view-model';

const cases: { count: DaySchedule['count']; announcement: string; reason: string }[] = [
  {
    count: { state: 'verified', value: 6 },
    announcement: '6 games, supplied count',
    reason: '',
  },
  {
    count: { state: 'incomplete', value: 9, reason: 'Only part of this fixture is supplied.' },
    announcement: '9 observed games, total unknown',
    reason: 'Only part of this fixture is supplied.',
  },
  {
    count: { state: 'unknown', reason: 'No fixture coverage for this day.' },
    announcement: 'Game count unknown',
    reason: 'No fixture coverage for this day.',
  },
  {
    count: { state: 'unsupported', reason: 'This source cannot supply a game count.' },
    announcement: 'Game count unavailable',
    reason: 'This source cannot supply a game count.',
  },
];

describe('Schedule certainty announcements', () => {
  it.each(cases)(
    'announces $count.state coverage with its actual reason',
    ({ count, announcement, reason }) => {
      render(
        <WeekSchedule
          days={[{ date: '2026-12-07', games: [], count }]}
          start="2026-12-07"
          selectedDay="2026-12-07"
          onSelectDay={() => {}}
          onMove={() => {}}
          onReset={() => {}}
          isReference
        />,
      );
      expect(
        screen.getByRole('button', { name: `Select Monday, December 7: ${announcement}` }),
      ).toHaveAccessibleDescription(reason);
    },
  );
});
