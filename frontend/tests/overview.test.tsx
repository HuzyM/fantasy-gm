import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import App from '../src/App';
describe('Overview', () => {
  it('focuses the mobile navigation and returns focus to its opener on Escape', async () => {
    const user = userEvent.setup();
    render(<App />);
    const opener = screen.getByRole('button', { name: /^Open navigation$/ });
    await user.click(opener);
    expect(screen.getByRole('button', { name: /^Close navigation$/ })).toHaveFocus();
    await user.keyboard('{Escape}');
    expect(opener).toHaveAttribute('aria-expanded', 'false');
    expect(opener).toHaveFocus();
  });
  it('supports arrow-key navigation in the roster tabs', async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole('tab', { name: /Defense/ }));
    await user.keyboard('{ArrowRight}');
    expect(screen.getByRole('tab', { name: /Goalies/ })).toHaveAttribute('aria-selected', 'true');
    await user.keyboard('{Home}');
    expect(screen.getByRole('tab', { name: /All Players/ })).toHaveAttribute(
      'aria-selected',
      'true',
    );
  });
  it('identifies synthetic data and never presents missing schedule coverage as zero', async () => {
    const user = userEvent.setup();
    render(<App />);
    expect(screen.getByText('DEMO · SYNTHETIC DATA')).toBeVisible();
    await user.click(screen.getByRole('button', { name: 'Next week' }));
    expect(
      within(screen.getByRole('region', { name: 'Weekly schedule' })).getAllByText('Unknown'),
    ).toHaveLength(7);
    expect(screen.getByText('No fixture games loaded for this week.')).toBeVisible();
  });
  it('combines roster search and tabs, and selecting a player updates inspection', async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole('tab', { name: /Defense/ }));
    const table = screen.getByRole('table', { name: 'My roster' });
    expect(within(table).queryByText('Nathan MacKinnon')).not.toBeInTheDocument();
    await user.type(screen.getByRole('searchbox'), 'Bouchard');
    await user.click(screen.getByRole('button', { name: 'Inspect Evan Bouchard' }));
    expect(
      within(screen.getByRole('complementary', { name: 'Player inspection' })).getByRole(
        'heading',
        { name: 'Evan Bouchard' },
      ),
    ).toBeVisible();
    await user.click(screen.getByRole('button', { name: 'Close player inspection' }));
    expect(
      screen.queryByRole('complementary', { name: 'Player inspection' }),
    ).not.toBeInTheDocument();
  });
  it('expands actual day fixtures and explains unsupported actions without navigating to another screen', async () => {
    const user = userEvent.setup();
    render(<App />);
    const monday = screen.getByRole('article', { name: /Monday, December 7/ });
    expect(within(monday).getAllByRole('listitem')).toHaveLength(3);
    await user.click(within(monday).getByRole('button', { name: /3 more games/ }));
    expect(within(monday).getAllByRole('listitem')).toHaveLength(6);
    await user.click(screen.getByRole('button', { name: 'Compare players' }));
    expect(screen.getByRole('status')).toHaveTextContent(
      'Player Comparison is planned for a later milestone.',
    );
    expect(screen.getByRole('heading', { name: 'My Roster' })).toBeVisible();
  });
});
