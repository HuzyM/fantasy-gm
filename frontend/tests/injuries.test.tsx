import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import App from '../src/App';
import { RosterTable } from '../src/components/RosterTable';
import { players } from '../src/fixtures/overview';
import { filterPlayers, isInjured } from '../src/view-model';

describe('Reported injury filtering', () => {
  it.each(['DTD', 'Out', 'IR', 'IR+'] as const)(
    'counts reported %s independently of a roster slot',
    (value) => {
      const player = {
        name: 'Fictional example',
        team: 'DEMO',
        group: 'forwards',
        injury: { state: 'verified', value },
        rosterSlot: { state: 'verified', value: 'BN' },
      } as const;
      expect(isInjured(player)).toBe(true);
      expect(filterPlayers([player], '', 'injured')).toEqual([player]);
      expect(filterPlayers([player], '', 'forwards')).toEqual([player]);
      expect(filterPlayers([player], 'no match', 'injured')).toEqual([]);
    },
  );

  it('does not infer injury from an IR slot, unknown or unsupported status', () => {
    expect(
      isInjured({
        injury: { state: 'verified', value: 'Healthy' },
        rosterSlot: { state: 'verified', value: 'IR' },
      }),
    ).toBe(false);
    expect(isInjured({ injury: { state: 'unknown', reason: 'Not supplied' } })).toBe(false);
    expect(isInjured({ injury: { state: 'unsupported', reason: 'Not supported' } })).toBe(false);
    expect(isInjured({})).toBe(false);
    expect(
      isInjured({
        injury: {
          state: 'incomplete',
          value: 'DTD',
          reason: 'Observed designation; detail missing',
        },
      }),
    ).toBe(true);
  });

  it('derives the count from the full roster, preserves positional membership and keyboard navigation', async () => {
    const user = userEvent.setup();
    render(<App />);
    const injured = screen.getByRole('tab', { name: /Injured \(2\)/ });
    await user.click(screen.getByRole('tab', { name: /Goalies/ }));
    await user.keyboard('{ArrowRight}');
    expect(injured).toHaveFocus();
    expect(injured).toHaveAttribute('aria-selected', 'true');
    const table = screen.getByRole('table', { name: 'My roster' });
    expect(within(table).getByText('Demo Forward')).toBeVisible();
    expect(within(table).queryByText('Cale Makar')).not.toBeInTheDocument();
    await user.click(screen.getByRole('tab', { name: /Forwards/ }));
    expect(within(table).getByText('Demo Forward')).toBeVisible();
    await user.type(screen.getByRole('searchbox'), 'makar');
    expect(screen.getByRole('tab', { name: /Injured \(2\)/ })).toBeInTheDocument();
  });

  it('shows an honest empty injury state and updates counts for a changed roster', () => {
    const healthy = players.filter((player) => !isInjured(player));
    const { rerender } = render(
      <RosterTable
        players={players.filter(isInjured)}
        allPlayers={players}
        group="injured"
        onGroup={() => {}}
        onSelect={() => {}}
        onNotice={() => {}}
        referenceWeek
      />,
    );
    expect(screen.getByRole('tab', { name: /Injured \(2\)/ })).toBeVisible();
    rerender(
      <RosterTable
        players={[]}
        allPlayers={healthy}
        group="injured"
        onGroup={() => {}}
        onSelect={() => {}}
        onNotice={() => {}}
        referenceWeek
      />,
    );
    expect(screen.getByRole('tab', { name: /Injured \(0\)/ })).toBeVisible();
    expect(screen.getByText('No reported injury designations.')).toBeVisible();
    expect(screen.getByText(/Unknown injury status does not mean healthy/)).toBeVisible();
  });

  it('keeps invented injury examples off real NHL identities', () => {
    expect(players.filter(isInjured).every((player) => player.nhlId === undefined)).toBe(true);
    expect(
      players
        .filter((player) => player.nhlId !== undefined)
        .every((player) => player.injury.state === 'unknown'),
    ).toBe(true);
  });
});
