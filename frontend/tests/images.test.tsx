import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { PlayerHeadshot } from '../src/components/PlayerHeadshot';
import { TeamMark } from '../src/components/primitives';
import { PlayerInspection } from '../src/components/PlayerInspection';
import { players } from '../src/fixtures/overview';

describe('Identity-safe local player photographs', () => {
  it('exposes loading, then the verified player image after load', () => {
    render(<PlayerHeadshot nhlId={8480069} name="Cale Makar" />);
    expect(screen.getByRole('img', { name: 'Cale Makar: photo loading' })).toBeVisible();
    const image = screen.getByAltText('Cale Makar photograph');
    expect(image).toHaveAttribute('src', '/assets/players/8480069.jpg');
    fireEvent.load(image);
    expect(screen.getByRole('img', { name: 'Cale Makar photograph' })).toBeVisible();
    expect(screen.queryByRole('img', { name: /photo loading/ })).not.toBeInTheDocument();
  });

  it('uses a clear fallback on error and resets when the selected identity changes', () => {
    const { rerender } = render(
      <PlayerHeadshot nhlId={8480069} name="Cale Makar" variant="hero" />,
    );
    fireEvent.error(screen.getByAltText('Cale Makar photograph'));
    expect(screen.getByRole('img', { name: 'Cale Makar: photo unavailable' })).toBeVisible();
    expect(
      screen.getByRole('img', { name: 'Cale Makar: photo unavailable' }).closest('.headshot'),
    ).toHaveAttribute('data-image-state', 'error');
    rerender(<PlayerHeadshot nhlId={8480803} name="Evan Bouchard" variant="hero" />);
    expect(screen.getByAltText('Evan Bouchard photograph')).toHaveAttribute(
      'src',
      '/assets/players/8480803.jpg',
    );
    expect(screen.queryByAltText('Cale Makar photograph')).not.toBeInTheDocument();
    expect(screen.getByRole('img', { name: 'Evan Bouchard: photo loading' })).toBeVisible();
  });

  it('never chooses a picture by approximate name or substitutes another player', () => {
    render(<PlayerHeadshot name="Cale Makar" nhlId={1234567} />);
    expect(screen.getByRole('img', { name: 'Cale Makar: photo unavailable' })).toBeVisible();
    expect(screen.queryByAltText('Cale Makar photograph')).not.toBeInTheDocument();
  });

  it('rejects a conflicting player identity even when a photograph exists for that ID', () => {
    render(<PlayerHeadshot name="Cale Makar" nhlId={8480803} />);
    expect(screen.queryByAltText('Cale Makar photograph')).not.toBeInTheDocument();
    expect(screen.getByRole('img', { name: 'Cale Makar: photo unavailable' })).toBeVisible();
  });

  it('does not credit a rejected photograph in the inspection panel', () => {
    const player = players.find((entry) => entry.id === 'makar')!;
    const { rerender } = render(
      <PlayerInspection player={{ ...player, nhlId: 8480803 }} referenceWeek onClose={() => {}} />,
    );
    expect(screen.getByRole('img', { name: 'Cale Makar: photo unavailable' })).toBeVisible();
    expect(screen.queryByRole('link', { name: 'Photo credit / license' })).not.toBeInTheDocument();
    rerender(<PlayerInspection player={player} referenceWeek onClose={() => {}} />);
    expect(screen.getByRole('link', { name: 'Photo credit / license' })).toHaveAttribute(
      'href',
      expect.stringContaining('Cale_Makar'),
    );
  });
});

describe('Official team logos', () => {
  it('loads the identity-mapped local logo and falls back on errors or unknown teams', () => {
    const { container, rerender } = render(<TeamMark code="COL" />);
    const logo = screen.getByAltText('Colorado Avalanche logo');
    expect(logo).toHaveAttribute('src', '/assets/teams/COL.svg');
    fireEvent.error(logo);
    expect(container.querySelector('img')).toBeNull();
    expect(
      screen.getByRole('img', { name: 'Colorado Avalanche: logo unavailable' }),
    ).toHaveTextContent('COL');
    rerender(<TeamMark code="UNKNOWN" />);
    expect(screen.getByTitle(/Team identity unavailable/)).toHaveTextContent('UNKNOWN');
  });
});
