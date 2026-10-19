import { useState } from 'react';
import {
  Activity,
  ArrowRight,
  Clock3,
  Database,
  Info,
  Link2,
  LockKeyhole,
  RotateCcw,
  ShieldCheck,
  Trophy,
  Users,
  Wrench,
} from 'lucide-react';
import type { ScreenProps } from '../application';
import { Button, Panel } from '../components/primitives';
import '../league-preferences.css';

export default function Connections({ onNavigate, onNotice }: ScreenProps) {
  const [league, setLeague] = useState('riverside');
  const [showGuide, setShowGuide] = useState(false);
  const [showActivity, setShowActivity] = useState(false);
  const leagueNames = [
    {
      id: 'riverside',
      name: 'Riverside Hockey League',
      details: '12 teams · H2H Points',
      Icon: Trophy,
    },
    {
      id: 'office',
      name: 'Office Hockey Pool',
      details: '10 teams · H2H Categories',
      Icon: ShieldCheck,
    },
    { id: 'keeper', name: 'Keeper Dynasty League', details: '14 teams · H2H Points', Icon: Trophy },
  ];
  return (
    <div className="connections-screen">
      <div className="connections-heading">
        <Users size={42} />
        <div>
          <h1>Connections</h1>
          <p>Manage your account, demo leagues, and data access.</p>
        </div>
      </div>
      <div className="connections-grid">
        <div className="connections-main">
          <Panel className="connections-account">
            <div className="connections-provider-mark" aria-hidden="true">
              y!
            </div>
            <div className="connections-account-copy">
              <div className="connections-account-title">
                <h2>Yahoo Fantasy</h2>
                <span className="connections-status-pill">Disconnected</span>
              </div>
              <p>No account connected</p>
              <div className="connections-account-note">
                <LockKeyhole size={17} /> Provider access not enabled <span>│</span> Demo browsing
                is available
              </div>
            </div>
            <div className="connections-last-sync">
              <small>Last sync</small>
              <strong>Never synced</strong>
              <span>Not verified</span>
            </div>
          </Panel>
          <div className="connections-metrics">
            <Panel>
              <Users />
              <div>
                <b>0</b>
                <span>Connected leagues</span>
                <small>3 synthetic demos available</small>
              </div>
            </Panel>
            <Panel>
              <Clock3 />
              <div>
                <b>Not available</b>
                <span>Last sync time</span>
                <small>No sync has run</small>
              </div>
            </Panel>
            <Panel>
              <Activity />
              <div>
                <b>Not verified</b>
                <span>Sync health</span>
                <small>Provider is disconnected</small>
              </div>
            </Panel>
            <Panel>
              <LockKeyhole />
              <div>
                <b>No grants</b>
                <span>Permissions</span>
                <small>No account authorization</small>
              </div>
            </Panel>
          </div>
          <div className="connections-selection-grid">
            <Panel className="connections-leagues">
              <div className="connections-panel-heading">
                <Trophy />
                <div>
                  <h2>League Selection</h2>
                  <p>Choose a synthetic league to preview.</p>
                </div>
              </div>
              <fieldset>
                <legend className="sr-only">Select demo league</legend>
                {leagueNames.map(({ id, name, details, Icon }) => (
                  <label
                    key={id}
                    className={
                      league === id
                        ? 'connections-league-option connections-league-active'
                        : 'connections-league-option'
                    }
                  >
                    <input
                      type="radio"
                      name="connections-demo-league"
                      value={id}
                      checked={league === id}
                      onChange={() => setLeague(id)}
                    />
                    <span className="connections-demo-crest">
                      <Icon size={36} />
                    </span>
                    <span>
                      <strong>{name}</strong>
                      <small>{details} · 2024–25 sample</small>
                    </span>
                    {league === id && <span className="connections-chip">Selected</span>}
                  </label>
                ))}
              </fieldset>
              <p className="connections-demo-selection">
                Selected: {leagueNames.find((item) => item.id === league)?.name}. This preview does
                not select a provider league.
              </p>
            </Panel>
            <Panel className="connections-sync">
              <div className="connections-panel-heading">
                <RotateCcw />
                <h2>Sync Activity</h2>
              </div>
              <div className="connections-empty">
                <Database size={36} />
                <h3>No sync activity</h3>
                <p>There are no completed syncs or verified provider timestamps in this browser.</p>
              </div>
              <Button onClick={() => setShowActivity(!showActivity)} aria-expanded={showActivity}>
                {showActivity ? 'Hide details' : 'View sync details'}
              </Button>
              {showActivity && (
                <p className="connections-detail">
                  Roster, standings, matchups, player data, and league settings have not been
                  fetched by this frontend. Demo data is synthetic.
                </p>
              )}
            </Panel>
          </div>
          <Panel className="connections-permissions">
            <div className="connections-panel-heading">
              <LockKeyhole />
              <div>
                <h2>Permissions &amp; Access</h2>
                <p>Current frontend capabilities, independent of future provider permissions.</p>
              </div>
            </div>
            <div className="connections-capability-grid">
              {[
                ['Demo leagues', 'Browse locally'],
                ['Demo rosters', 'View only'],
                ['Provider data', 'Not connected'],
                ['Lineup changes', 'Unavailable'],
                ['Transactions', 'Unavailable'],
                ['Account tokens', 'Not accessed'],
              ].map(([title, state]) => (
                <div key={title}>
                  <Database size={20} />
                  <span>
                    <strong>{title}</strong>
                    <small>{state}</small>
                  </span>
                </div>
              ))}
            </div>
          </Panel>
        </div>
        <aside className="connections-side">
          <Panel className="connections-tools">
            <div className="connections-panel-heading">
              <Wrench />
              <h2>Connection Tools</h2>
            </div>
            <Button className="connections-tool" disabled>
              <RotateCcw />
              <span>
                <b>Sync now</b>
                <small>Unavailable without an approved local API</small>
              </span>
            </Button>
            <Button
              className="connections-tool"
              onClick={() => setShowGuide(!showGuide)}
              aria-expanded={showGuide}
            >
              <Link2 />
              <span>
                <b>Connection guidance</b>
                <small>Human-operated CLI workflow</small>
              </span>
            </Button>
            {showGuide && (
              <p className="connections-detail">
                Yahoo connection remains a human-only CLI workflow. Browser authentication and sync
                are unavailable until the local API privacy boundary is approved. Do not paste
                credentials or tokens here.
              </p>
            )}
            <Button className="connections-tool" onClick={() => onNavigate('league')}>
              <Trophy />
              <span>
                <b>Open demo league</b>
                <small>Explore the league overview</small>
              </span>
              <ArrowRight size={16} />
            </Button>
            <Button
              className="connections-tool"
              onClick={() => {
                setLeague('riverside');
                setShowActivity(false);
                onNotice('Demo league selection reset. No account data was changed.');
              }}
            >
              <RotateCcw />
              <span>
                <b>Reset demo selection</b>
                <small>Return to Riverside in this page</small>
              </span>
            </Button>
          </Panel>
          <Panel className="connections-status">
            <div className="connections-panel-heading">
              <Activity />
              <h2>Connection Status</h2>
            </div>
            <div className="connections-offline">
              <span aria-hidden="true" />
              <div>
                <h3>Disconnected</h3>
                <p>No verified Yahoo Fantasy connection is available to this frontend.</p>
              </div>
            </div>
            <dl>
              <div>
                <dt>Yahoo account</dt>
                <dd>Not connected</dd>
              </div>
              <div>
                <dt>Provider leagues</dt>
                <dd>Not loaded</dd>
              </div>
              <div>
                <dt>Last sync</dt>
                <dd>Never</dd>
              </div>
              <div>
                <dt>Sync health</dt>
                <dd>Not verified</dd>
              </div>
            </dl>
            <div className="connections-boundary">
              <Info />
              <p>
                Connection and sync require a human-operated CLI until the local API privacy
                boundary is approved.
              </p>
            </div>
          </Panel>
        </aside>
      </div>
      <p className="connections-footer">
        <Info size={18} />
        Demo browsing is read-only. This frontend does not authenticate accounts, store tokens, or
        change lineups.
      </p>
    </div>
  );
}
