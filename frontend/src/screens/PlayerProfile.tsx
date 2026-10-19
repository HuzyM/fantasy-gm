import { dateLabel } from '../view-model';
import { isObservation } from '../api';
import { useState } from 'react';
import type { ScreenProps } from '../application';
import { Button, DataValue, Panel, TeamMark } from '../components/primitives';
import { PlayerHeadshot } from '../components/PlayerHeadshot';
import { Tabs } from '../components/Tabs';
import { getPlayerPhoto, teamAssets } from '../media';
import { overviewFixture } from '../fixtures/overview';

const statTabs = ['Season Stats', 'Game Log', 'Advanced Stats', 'Splits'] as const;
export default function PlayerProfile({
  players,
  selectedId,
  local,
  onNavigate,
}: ScreenProps & { selectedId?: string }) {
  const observed = isObservation(local?.view);
  const days = observed ? (local?.view?.schedule?.days ?? []) : overviewFixture.days;
  const player = players.find((p) => p.id === selectedId);
  const [tab, setTab] = useState<(typeof statTabs)[number]>('Season Stats');
  const [period, setPeriod] = useState('10');
  if (!player)
    return (
      <section className="panel unavailable-profile">
        <h1>Player unavailable</h1>
        <p>This identity is not in the loaded roster.</p>
        <Button onClick={() => onNavigate('roster')}>Back to My Roster</Button>
      </section>
    );
  const photo = getPlayerPhoto(player.nhlId, player.name);
  const games =
    player.scheduleJoin === 'unverified'
      ? []
      : days.flatMap((day) =>
          day.games
            .filter((game) => game.away === player.team || game.home === player.team)
            .map((game) => ({ ...game, date: day.date })),
        );
  const performance = observed
    ? []
    : [18.2, 22.1, 16.8, 24.5, 12.3, 20.7, 19.1, 15.8, 28.4, 18.6].slice(-Number(period));
  return (
    <div className="profile-page">
      <Button className="profile-back" onClick={() => onNavigate('roster')}>
        Back to My Roster
      </Button>
      <p className="source-banner">
        {observed
          ? 'Reported Yahoo identity · NHL photo crosswalk, performance, injuries and coverage unverified'
          : 'Synthetic performance and schedule examples · historical licensed photograph'}
      </p>
      <section className="panel profile-hero" aria-label="Player identity">
        <div className="profile-portrait">
          <PlayerHeadshot nhlId={player.nhlId} name={player.name} variant="hero" />
          {photo && (
            <a className="portrait-credit" href={photo.source} target="_blank" rel="noreferrer">
              Photo credit / license
            </a>
          )}
        </div>
        <div className="profile-identity">
          <h1>{player.name}</h1>
          <p>
            {player.number === undefined ? 'Number unknown' : `#${player.number}`} &nbsp; | &nbsp;{' '}
            {player.position} &nbsp; | &nbsp;{' '}
            {teamAssets[player.team]?.name ??
              (player.identitySource === 'yahoo' ? 'Team unknown' : 'Fictional demo club')}
          </p>
          <p className="muted">
            {player.nhlId
              ? `NHL player ID: ${player.nhlId}`
              : player.identitySource === 'yahoo'
                ? 'Yahoo identity · NHL match unverified'
                : 'Fictional demo identity'}
          </p>
          <div className="profile-status">
            <span>
              Roster slot: <DataValue datum={player.rosterSlot} />
            </span>
            <span>
              Injury: <DataValue datum={player.injury} />
            </span>
          </div>
          <p className="muted">
            {observed
              ? 'Reported affiliation does not establish current team or appearance.'
              : 'Team affiliation shown in the synthetic roster is illustrative.'}
          </p>
        </div>
        <div className="profile-club">
          <TeamMark code={player.team} large />
        </div>
        <div className="profile-stats">
          {player.stats.length ? (
            player.stats.map((stat) => (
              <div key={stat.label}>
                <strong>
                  <DataValue datum={stat.datum} />
                </strong>
                <span>{stat.label}</span>
              </div>
            ))
          ) : (
            <p>No statistics supplied for this fictional player.</p>
          )}
        </div>
      </section>
      <div className="profile-grid">
        <div className="profile-wide">
          <Panel className="performance-panel">
            <div className="section-toolbar">
              <h2>Recent Performance</h2>
              <label>
                Demo games{' '}
                <select
                  disabled={observed}
                  value={period}
                  onChange={(e) => setPeriod(e.target.value)}
                >
                  <option value="10">Last 10</option>
                  <option value="5">Last 5</option>
                </select>
              </label>
            </div>
            <p className="muted">
              {observed
                ? 'Performance unavailable. No game-log provider is connected.'
                : 'Illustrative series only; no real game results.'}
            </p>
            <div
              className="performance-chart"
              role="img"
              aria-label={
                observed
                  ? 'Performance unavailable'
                  : `Synthetic fantasy points: ${performance.join(', ')}`
              }
            >
              {performance.map((value, i) => (
                <div className="performance-column" key={i}>
                  <span>{value}</span>
                  <div style={{ height: `${value * 5}px` }} />
                  <small>Demo {i + 1}</small>
                </div>
              ))}
            </div>
            <details>
              <summary>Chart data</summary>
              <p>{performance.join(' · ')}</p>
            </details>
          </Panel>
          <Panel className="profile-season">
            <Tabs
              label="Profile statistics"
              className="inspection-tabs"
              value={tab}
              onChange={setTab}
              idPrefix="profile-stat"
              panelId="profile-stats"
              items={statTabs.map((value) => ({ value, label: value }))}
            />
            <div
              id="profile-stats"
              role="tabpanel"
              aria-labelledby={`profile-stat-${tab.replace(' ', '-')}`}
            >
              {tab === 'Season Stats' ? (
                <table>
                  <caption>
                    {observed ? 'Performance statistics unavailable' : 'Synthetic season totals'}
                  </caption>
                  <thead>
                    <tr>
                      <th>Category</th>
                      <th>Total</th>
                      <th>Rank</th>
                    </tr>
                  </thead>
                  <tbody>
                    {player.stats.map((stat) => (
                      <tr key={stat.label}>
                        <th scope="row">{stat.label}</th>
                        <td>
                          <DataValue datum={stat.datum} />
                        </td>
                        <td>Unavailable</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="unavailable-state">
                  <h3>{tab} unavailable</h3>
                  <p>
                    {tab === 'Game Log'
                      ? 'No game-log provider is connected.'
                      : 'No verified source supplies this breakdown.'}
                  </p>
                </div>
              )}
            </div>
          </Panel>
        </div>
        <div className="profile-middle">
          <Panel className="profile-outlook">
            <h2>Fantasy Outlook</h2>
            {[
              'Weekly projection',
              'Rest of season projection',
              'Ownership',
              'Start / sit advice',
              'Trade value',
            ].map((label) => (
              <div className="info-row" key={label}>
                <span>{label}</span>
                <DataValue
                  datum={{
                    state: 'unsupported',
                    reason: 'No verified projection or advice provider is implemented.',
                  }}
                />
              </div>
            ))}
            <p className="muted">Synthetic averages are not forecasts.</p>
          </Panel>
          <Panel className="profile-impact">
            <h2>Schedule Impact</h2>
            <div className="impact-days">
              {days.map((day) => (
                <div key={day.date}>
                  <span>{day.date.slice(-2)}</span>
                  <span
                    role="img"
                    className={
                      player.scheduleJoin !== 'unverified' &&
                      day.games.some((g) => g.home === player.team || g.away === player.team)
                        ? 'observed-dot'
                        : 'unknown-dot'
                    }
                    aria-label={
                      player.scheduleJoin !== 'unverified' &&
                      day.games.some((g) => g.home === player.team || g.away === player.team)
                        ? observed
                          ? 'Observed team game; appearance unconfirmed'
                          : 'Synthetic team game'
                        : observed
                          ? 'Schedule or affiliation unknown'
                          : 'No game in fixture'
                    }
                  />
                </div>
              ))}
            </div>
            <p>
              Player appearances are unconfirmed.{' '}
              {observed
                ? 'Schedule and affiliation coverage are unverified.'
                : 'Thursday has incomplete fixture coverage.'}
            </p>
            <Button onClick={() => onNavigate('planner')}>View Schedule</Button>
          </Panel>
          <Panel className="profile-news">
            <h2>News &amp; Updates</h2>
            <p>No news provider is connected.</p>
          </Panel>
        </div>
        <div className="profile-right">
          <Panel className="profile-upcoming">
            <div className="section-toolbar">
              <h2>Upcoming Games</h2>
              <Button onClick={() => onNavigate('planner')}>View Schedule →</Button>
            </div>
            <p className="muted">
              {observed
                ? 'Observed team schedule · affiliation and coverage unverified'
                : 'Synthetic team schedule · no confirmed appearances'}
            </p>
            {games.length ? (
              games.map((game) => (
                <div className="profile-game" key={game.id}>
                  <time dateTime={game.date}>
                    {dateLabel(game.date, { month: 'short', day: 'numeric' })}
                  </time>
                  <TeamMark code={game.away === player.team ? game.home : game.away} />
                  <span>
                    {game.away === player.team ? '@' : 'vs'}{' '}
                    {game.away === player.team ? game.home : game.away}
                  </span>
                  <span>{game.time} ET</span>
                </div>
              ))
            ) : (
              <p>No joined team games supplied. Complete schedule unknown.</p>
            )}
          </Panel>
          <Panel className="profile-considerations">
            <h2>Lineup Considerations</h2>
            <p>
              Line combinations, power-play unit and player availability are unknown. No advice
              inferred from a team game.
            </p>
          </Panel>
          <Panel className="profile-quick">
            <h2>Quick Actions</h2>
            <Button onClick={() => onNavigate('comparison', player.id)}>Compare Player</Button>
            <Button disabled>Trade Player · read-only</Button>
          </Panel>
        </div>
      </div>
    </div>
  );
}
