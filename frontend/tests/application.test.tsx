import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it } from 'vitest';
import App from '../src/App';

beforeEach(() => window.history.replaceState(null, '', '/'));
describe('roster and profile navigation', () => {
  it('retains display choices across screen navigation without browser storage', async () => {
    window.history.replaceState(null, '', '/#settings');
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole('switch', { name: 'Show team logos' }));
    await user.click(screen.getByRole('switch', { name: 'Compact view' }));
    expect(document.querySelector('.app-shell')).toHaveClass(
      'without-team-logos',
      'compact-display',
    );
    await user.click(screen.getByRole('button', { name: '03 My Roster' }));
    await user.click(screen.getByRole('button', { name: '07 Settings' }));
    expect(screen.getByRole('switch', { name: 'Show team logos' })).toHaveAttribute(
      'aria-checked',
      'false',
    );
  });
  it('opens the roster, inspects a player, and opens their full profile with matching identity', async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole('button', { name: /^03 My Roster$/ }));
    expect(screen.getByRole('heading', { level: 1, name: 'My Roster' })).toBeVisible();
    await user.click(screen.getByRole('button', { name: /^Inspect Auston Matthews$/ }));
    await user.click(screen.getByRole('button', { name: /View Full Player Profile/ }));
    expect(screen.getByRole('heading', { level: 1, name: 'Auston Matthews' })).toBeVisible();
    expect(screen.getByText('NHL player ID: 8479318')).toBeVisible();
    expect(screen.getByText(/Player appearances are unconfirmed/)).toBeVisible();
    await user.click(screen.getByRole('tab', { name: /^Game Log$/ }));
    expect(screen.getByText(/No game-log provider is connected/)).toBeVisible();
    await user.click(screen.getByRole('button', { name: 'Back to My Roster' }));
    expect(screen.getByRole('heading', { level: 1, name: 'My Roster' })).toBeVisible();
  });
  it('keeps slots distinct from injury designations in roster subsets', async () => {
    window.history.replaceState(null, '', '/#roster');
    const user = userEvent.setup();
    render(<App />);
    expect(
      within(screen.getByRole('region', { name: 'Bench (2)' })).getByText('Demo Forward'),
    ).toBeVisible();
    const reserve = screen.getByRole('region', { name: 'Injured Reserve (1)' });
    expect(within(reserve).getByText('Demo Goalie')).toBeVisible();
    await user.click(screen.getByRole('tab', { name: /Injured \(2\)/ }));
    expect(
      within(screen.getByRole('table', { name: 'My roster' })).getAllByRole('row'),
    ).toHaveLength(3);
  });
  it('handles an invalid profile identity without substituting a photograph', () => {
    window.history.replaceState(null, '', '/#profile/not-a-player');
    render(<App />);
    expect(screen.getByRole('heading', { name: 'Player unavailable' })).toBeVisible();
    expect(document.querySelector('.profile-hero img')).toBeNull();
  });
});
