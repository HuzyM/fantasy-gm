import { CalendarDays, Info, X } from 'lucide-react';
import { useState } from 'react';
import type { InspectorTab, Player } from '../view-model';
import { teamAssets, playerPhotos } from '../media';
import { DataValue, TeamMark } from './primitives';
import { PlayerHeadshot } from './PlayerHeadshot';
import { Tabs } from './Tabs';

const tabs: readonly InspectorTab[] = ['Overview', 'Stats', 'Schedule', 'Game log'];
export function PlayerInspection({
  player,
  onClose,
  referenceWeek,
}: {
  player: Player;
  onClose: () => void;
  referenceWeek: boolean;
}) {
  const [tab, setTab] = useState<InspectorTab>('Overview');
  return (
    <aside className="panel inspection-panel" aria-label="Player inspection">
      <div className="inspection-heading">
        <h2>PLAYER INSPECTION</h2>
        <button className="icon-button" aria-label="Close player inspection" onClick={onClose}>
          <X size={22} />
        </button>
      </div>
      <div className="player-hero">
        <PlayerHeadshot nhlId={player.nhlId} name={player.name} variant="hero" />
        <p
          className={`inspection-injury ${player.injury.state === 'verified' && player.injury.value !== 'Healthy' ? 'injury-reported' : ''}`}
        >
          Injury: <DataValue datum={player.injury} />{' '}
          <span>
            · Roster slot: <DataValue datum={player.rosterSlot} />
          </span>
        </p>

        <div className="player-hero-copy">
          <span className="jersey-number">
            {player.nhlId === undefined ? 'FICTIONAL DEMO' : `#${player.number}`}
          </span>
          <h3 aria-label={player.name}>
            {player.name.split(' ').slice(0, -1).join(' ')}
            <br />
            {player.name.split(' ').slice(-1)}
          </h3>
          <div className="player-club">
            <TeamMark code={player.team} large />
            <div>
              <strong>
                {player.team} <span>·</span> {player.position}
              </strong>
              <small>{teamAssets[player.team]?.name ?? 'Fictional demo club'}</small>
            </div>
          </div>
        </div>
        {player.nhlId !== undefined && playerPhotos[player.nhlId] && (
          <a
            className="portrait-credit"
            href={playerPhotos[player.nhlId]?.source}
            target="_blank"
            rel="noreferrer"
          >
            Photo credit / license
          </a>
        )}
      </div>
      <Tabs
        className="inspection-tabs"
        label="Player details"
        value={tab}
        onChange={setTab}
        idPrefix="player-tab"
        panelId="player-details"
        items={tabs.map((name) => ({ value: name, label: name }))}
      />
      <div
        id="player-details"
        role="tabpanel"
        aria-labelledby={`player-tab-${tab.replace(' ', '-')}`}
        className="inspection-body"
      >
        {tab === 'Overview' && (
          <>
            <div className="player-highlights">
              <div className="highlight-card">
                <small>NEXT TEAM GAME</small>
                <div className="next-game-highlight">
                  <TeamMark code={player.team} large />
                  <strong>{referenceWeek ? player.nextGame.split(' · ')[0] : 'Unknown'}</strong>
                </div>
                <span>
                  {referenceWeek
                    ? player.nextGame.split(' · ')[1]
                    : 'No fixture schedule for this week'}
                </span>
              </div>
              <div className="highlight-card">
                <small>FANTASY AVERAGE</small>
                <strong className="average-value">
                  <DataValue datum={player.average} format={(n) => n.toFixed(1)} />
                </strong>
                <span className="fixture-trend">SYNTHETIC PERIOD</span>
              </div>
            </div>
            <p className="stat-caption">
              2026–27 DEMO SEASON / {player.group === 'goalies' ? 'GOALIE' : 'SKATER'}
            </p>
            <div className="mini-stat-grid">
              {player.stats.map((stat) => (
                <div key={stat.label}>
                  <small>{stat.label}</small>
                  <strong>
                    <DataValue datum={stat.datum} />
                  </strong>
                </div>
              ))}
            </div>
          </>
        )}
        {tab === 'Stats' && (
          <div className="detail-stats">
            <p>Synthetic season statistics</p>
            {player.stats.map((stat) => (
              <div key={stat.label}>
                <span>{stat.label}</span>
                <DataValue datum={stat.datum} />
              </div>
            ))}
          </div>
        )}
        {tab === 'Schedule' && (
          <div className="detail-message">
            <CalendarDays />
            <h4>Reported team schedule</h4>
            <p>{referenceWeek ? player.nextGame : 'Unknown — this week has no loaded fixture.'}</p>
            <p>
              Team games do not guarantee player appearances. All schedules in this prototype are
              invented.
            </p>
          </div>
        )}
        {tab === 'Game log' && (
          <div className="detail-message">
            <Info />
            <h4>Game log unavailable</h4>
            <p>No game-log data source is implemented in this milestone.</p>
          </div>
        )}
      </div>
    </aside>
  );
}
