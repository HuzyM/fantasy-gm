import { fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import SchedulePlanner from '../src/screens/SchedulePlanner';
import PlayerComparison from '../src/screens/PlayerComparison';
import { players } from '../src/fixtures/overview';

const props = () => ({ players, search: '', onNavigate: vi.fn(), onNotice: vi.fn() });

describe('Schedule Planner', () => {
  it('announces schedule coverage together with each date', () => {
    render(<SchedulePlanner {...props()} />);
    expect(
      screen.getByRole('button', { name: /Select Thursday, December 10/ }),
    ).toHaveAccessibleName(/9 observed games.*total unknown/i);
  });
  it('selects real fixture dates and matchups, with exact team membership and no appearance claim', async () => {
    const user = userEvent.setup();
    render(<SchedulePlanner {...props()} />);
    const detail = screen.getByRole('complementary', { name: 'Selected matchup' });
    expect(within(detail).getByRole('heading', { name: 'TOR @ BUF' })).toBeVisible();
    expect(within(detail).getByText('Auston Matthews')).toBeVisible();
    expect(within(detail).queryByText('Cale Makar')).not.toBeInTheDocument();
    expect(within(detail).getByText(/Player appearances are not confirmed/)).toBeVisible();
    await user.click(screen.getByRole('button', { name: 'Select COL @ STL' }));
    expect(within(detail).getByText('Cale Makar')).toBeVisible();
    expect(within(detail).getByText('Nathan MacKinnon')).toBeVisible();
    await user.click(screen.getByRole('button', { name: /Select Tuesday, December 8/ }));
    expect(screen.getByRole('heading', { name: 'Tuesday, December 8, 2026' })).toBeVisible();
    expect(
      within(screen.getByRole('table', { name: 'Daily matchups' })).getByText('EDM', {
        selector: 'b',
      }),
    ).toBeVisible();
  });

  it('combines search and roster filter and keeps unloaded weeks unknown', async () => {
    const user = userEvent.setup();
    const input = props();
    const { rerender } = render(<SchedulePlanner {...input} />);
    await user.selectOptions(screen.getByLabelText('Show games'), 'rostered');
    const table = screen.getByRole('table', { name: 'Daily matchups' });
    expect(within(table).queryByText('ANA')).not.toBeInTheDocument();
    rerender(<SchedulePlanner {...input} search="Makar" />);
    expect(within(table).getByText('COL', { selector: 'b' })).toBeVisible();
    expect(within(table).queryByText('TOR')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Next week' }));
    expect(
      within(screen.getByRole('region', { name: 'Planner week' })).getAllByText('Unknown'),
    ).toHaveLength(7);
    expect(screen.getByText('Schedule coverage is unknown for this date.')).toBeVisible();
    expect(screen.queryByText(/off.day/i)).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Demo week' }));
    fireEvent.change(screen.getByLabelText('Choose date'), { target: { value: '2026-12-10' } });
    expect(
      screen.getByText('Partial schedule: observed games only; the total is unknown.'),
    ).toBeVisible();
  });
});

describe('Player Comparison', () => {
  it('keeps missing player media and statistics explicit when a fictional fixture is selected', async () => {
    const user = userEvent.setup();
    render(<PlayerComparison {...props()} />);
    await user.selectOptions(screen.getByLabelText('First player'), 'demo-ir');
    const first = screen.getByRole('region', { name: 'First comparison player' });
    expect(within(first).getByText('Player photograph unavailable')).toBeVisible();
    expect(within(first).getAllByText('Unknown')).toHaveLength(2);
    expect(within(first).queryByText('Historical licensed photograph')).not.toBeInTheDocument();
    expect(within(first).queryByRole('img', { name: /photograph$/ })).not.toBeInTheDocument();
  });

  it('derives per-game statistics from supplied games played and exchanges duplicate selections', async () => {
    const user = userEvent.setup();
    render(<PlayerComparison {...props()} />);
    await user.selectOptions(screen.getByLabelText('Statistics view'), 'per-game');
    const panel = screen.getByRole('tabpanel');
    expect(within(panel).getByText('0.38')).toBeVisible();
    await user.selectOptions(screen.getByLabelText('First player'), 'mackinnon');
    expect(screen.getByLabelText('Second player')).toHaveValue('matthews');
    expect(screen.getByLabelText('First player')).toHaveValue('mackinnon');
    await user.click(screen.getByRole('tab', { name: 'History' }));
    expect(screen.getByText(/Head-to-head results and game history are unavailable/)).toBeVisible();
  });

  it('selects fixture identities, swaps both sides, and opens selected profiles', async () => {
    const user = userEvent.setup();
    const input = props();
    render(<PlayerComparison {...input} />);
    const left = screen.getByLabelText('First player');
    const right = screen.getByLabelText('Second player');
    expect(left).toHaveValue('matthews');
    expect(right).toHaveValue('mackinnon');
    await user.selectOptions(right, 'bouchard');
    await user.click(screen.getByRole('button', { name: 'Swap players' }));
    expect(left).toHaveValue('bouchard');
    expect(right).toHaveValue('matthews');
    await user.click(screen.getByRole('button', { name: 'View Evan Bouchard profile' }));
    expect(input.onNavigate).toHaveBeenCalledWith('profile', 'bouchard');
    expect(screen.getAllByText(/Synthetic statistics/).length).toBeGreaterThan(0);
    expect(screen.getByText(/Historical performance is unavailable/)).toBeVisible();
    expect(screen.getByText(/Projections, news and rankings are unavailable/)).toBeVisible();
  });

  it('searches available choices without replacing the current player and supports keyboard tabs', async () => {
    const user = userEvent.setup();
    const input = props();
    const { rerender } = render(<PlayerComparison {...input} selectedId="makar" />);
    expect(screen.getByLabelText('First player')).toHaveValue('makar');
    await user.type(
      screen.getByRole('searchbox', { name: 'Find a comparison player' }),
      'Pastrnak',
    );
    expect(
      within(screen.getByLabelText('First player')).getByRole('option', { name: /Pastrnak/ }),
    ).toBeVisible();
    expect(
      within(screen.getByLabelText('First player')).queryByRole('option', { name: /Kucherov/ }),
    ).not.toBeInTheDocument();
    expect(screen.getByLabelText('First player')).toHaveValue('makar');
    await user.click(screen.getByRole('tab', { name: 'Statistics' }));
    await user.keyboard('{ArrowRight}');
    expect(screen.getByRole('tab', { name: 'Schedule' })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByText(/Team games; player appearances are unconfirmed/)).toBeVisible();
    rerender(<PlayerComparison {...input} players={[]} />);
    expect(screen.getByText('No players are available to compare.')).toBeVisible();
  });

  it('combines the app search with a team search as independent filters', async () => {
    const user = userEvent.setup();
    render(<PlayerComparison {...props()} search="COL" />);
    await user.type(screen.getByRole('searchbox', { name: 'Find a comparison player' }), 'Makar');
    expect(
      screen.queryByText('No matching player choices. Current selections are retained.'),
    ).not.toBeInTheDocument();
    expect(
      within(screen.getByLabelText('First player')).getByRole('option', { name: /Cale Makar/ }),
    ).toBeVisible();
  });
});
