import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import League from '../src/screens/League';
import Connections from '../src/screens/Connections';
import Settings from '../src/screens/Settings';

const props = { search: '', players: [], onNavigate: vi.fn(), onNotice: vi.fn() };

describe('League and preferences', () => {
  it('sorts synthetic standings and changes weeks without inventing scores', async () => {
    const user = userEvent.setup();
    render(<League {...props} />);
    const table = screen.getByRole('table', { name: 'Demo league standings' });
    expect(within(table).getAllByRole('row')[1]).toHaveTextContent('Northern Ice');
    await user.click(within(table).getByRole('button', { name: 'Sort by team' }));
    expect(within(table).getAllByRole('row')[1]).toHaveTextContent('Bay Area Blades');
    await user.click(screen.getByRole('button', { name: 'Next matchup week' }));
    expect(screen.getByText('No synthetic matchup scores loaded for Week 15.')).toBeVisible();
    expect(screen.getByLabelText('Demo league')).toBeDisabled();
    expect(screen.queryByRole('option', { name: 'Office Hockey Pool' })).not.toBeInTheDocument();
  });

  it('shows disconnected and unverified provider state, with no fake sync', async () => {
    const user = userEvent.setup();
    render(<Connections {...props} />);
    expect(screen.getByRole('heading', { name: 'Disconnected' })).toBeVisible();
    expect(screen.getByText('Never synced')).toBeVisible();
    expect(screen.getAllByRole('radio')).toHaveLength(1);
    expect(screen.getByRole('radio')).toBeChecked();
    expect(screen.getByRole('radio')).toBeDisabled();
    expect(screen.queryByText('Office Hockey Pool')).not.toBeInTheDocument();
    expect(screen.queryByText('Keeper Dynasty League')).not.toBeInTheDocument();
    expect(
      screen.queryByText(/Connected & Healthy|john.*@|Token expires/i),
    ).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Sync now/i })).toBeDisabled();
    await user.click(screen.getByRole('button', { name: /Reset demo view/i }));
    expect(props.onNotice).toHaveBeenCalledWith('Demo view reset. No account data was changed.');
  });

  it('changes only session preview preferences and resets after remount', async () => {
    const user = userEvent.setup();
    const storage = vi.spyOn(Storage.prototype, 'setItem');
    const view = render(<Settings {...props} />);
    await user.click(screen.getByText('Open preference preview'));
    const preview = screen.getByRole('region', { name: 'Preference preview' });
    await user.click(screen.getByRole('switch', { name: 'Show team logos' }));
    expect(within(preview).queryByRole('img')).not.toBeInTheDocument();
    await user.click(screen.getByRole('switch', { name: 'Compact view' }));
    expect(preview).toHaveClass('settings-preview-compact');
    await user.selectOptions(screen.getByLabelText('Stats format'), 'total');
    expect(within(preview).getByText('24 points · season total')).toBeVisible();
    expect(storage).not.toHaveBeenCalled();
    view.unmount();
    render(<Settings {...props} />);
    expect(screen.getByRole('switch', { name: 'Show team logos' })).toHaveAttribute(
      'aria-checked',
      'true',
    );
    expect(screen.getByRole('switch', { name: 'Compact view' })).toHaveAttribute(
      'aria-checked',
      'false',
    );
    storage.mockRestore();
  });

  it('keeps notifications unsupported and routes connection management', async () => {
    const user = userEvent.setup();
    render(<Settings {...props} />);
    expect(screen.getByRole('switch', { name: 'Game start alerts' })).toBeDisabled();
    await user.click(screen.getByRole('button', { name: /Manage connection/i }));
    expect(props.onNavigate).toHaveBeenCalledWith('connections');
  });

  it('navigates settings categories without changing the application route', async () => {
    const user = userEvent.setup();
    render(<Settings {...props} />);
    const initialHash = window.location.hash;
    const nav = screen.getByRole('navigation', { name: 'Settings sections' });
    const notifications = within(nav).getByRole('button', { name: /Notifications/ });
    await user.click(notifications);
    expect(notifications).toHaveAttribute('aria-pressed', 'true');
    expect(window.location.hash).toBe(initialHash);
  });
});
