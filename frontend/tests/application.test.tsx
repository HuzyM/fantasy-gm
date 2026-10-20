import { fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it } from 'vitest';
import App from '../src/App';

beforeEach(() => window.history.replaceState(null, '', '/'));
describe('roster and profile navigation', () => {
  it('carries the exact selected Planner window into the comparison Schedule tab in mounted memory', async () => {
    window.history.replaceState(null, '', '/#planner');
    const user = userEvent.setup();
    render(<App />);
    fireEvent.change(screen.getByLabelText('Choose date'), { target: { value: '2027-01-01' } });
    await user.click(screen.getByRole('button', { name: 'Compare players' }));
    expect(screen.getByRole('tab', { name: 'Schedule' })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByRole('region', { name: 'Weekly game comparison' })).toHaveTextContent(
      'Dec 28 – Jan 3, 2027',
    );
    expect(window.location.hash).toBe('#comparison');
    expect(JSON.stringify(window.history.state)).not.toContain('2026-12-28');
  });
  it('keeps keyboard skip navigation on the current roster screen', async () => {
    window.history.replaceState(null, '', '/#roster');
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole('link', { name: 'Skip to content' }));
    expect(window.location.hash).toBe('#roster');
    expect(screen.getByRole('main')).toHaveFocus();
    expect(screen.getByRole('heading', { level: 1, name: 'My Roster' })).toBeVisible();
  });
  it('updates the comparison identity when its routed player changes', async () => {
    window.history.replaceState(null, '', '/#comparison/matthews');
    const user = userEvent.setup();
    render(<App />);
    expect(screen.getByLabelText('First player')).toHaveValue('matthews');
    await user.click(screen.getByRole('link', { name: 'Fantasy GM Hockey Overview' }));
    window.location.hash = '#comparison/makar';
    await screen.findByRole('heading', { name: 'Player Comparison', level: 1 });
    expect(screen.getByLabelText('First player')).toHaveValue('makar');
  });
  it('applies the roster query to bench and reserve sections too', async () => {
    window.history.replaceState(null, '', '/#roster');
    const user = userEvent.setup();
    render(<App />);
    await user.type(screen.getByRole('searchbox'), 'matthews');
    expect(
      within(screen.getByRole('region', { name: /^Bench/ })).queryByText('Demo Forward'),
    ).not.toBeInTheDocument();
    expect(
      within(screen.getByRole('region', { name: /^Injured Reserve/ })).queryByText('Demo Goalie'),
    ).not.toBeInTheDocument();
  });
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
