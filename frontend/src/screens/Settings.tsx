import { isObservation } from '../api';
import { useState, useEffect } from 'react';
import {
  Bell,
  ChartNoAxesCombined,
  Database,
  ExternalLink,
  Info,
  LockKeyhole,
  Monitor,
  Settings2,
  Trophy,
  UserRound,
} from 'lucide-react';
import type { Screen, ScreenProps, DisplayPreferences } from '../application';
import { Button, Panel, TeamMark } from '../components/primitives';
import { ImageCredits } from '../components/ImageCredits';
import '../league-preferences.css';

function Toggle({
  label,
  checked,
  onChange,
  disabled = false,
}: {
  label: string;
  checked: boolean;
  onChange?: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-label={label}
      aria-checked={checked}
      disabled={disabled}
      onClick={onChange}
      className={`settings-toggle ${checked ? 'settings-toggle-on' : ''}`}
    >
      <span />
    </button>
  );
}

export default function Settings({
  onNavigate,
  onNotice,
  local,
  display,
  onDisplayChange,
}: ScreenProps & {
  display?: DisplayPreferences;
  onDisplayChange?: (value: DisplayPreferences) => void;
}) {
  const observed = isObservation(local?.view);
  const [defaultView, setDefaultView] = useState<Screen>('overview');
  const [range, setRange] = useState('season');
  const [logos, setLogos] = useState(display?.logos ?? true);
  const [compact, setCompact] = useState(display?.compact ?? false);
  const [contrast, setContrast] = useState(display?.contrast ?? false);
  useEffect(() => {
    onDisplayChange?.({ logos, compact, contrast });
  }, [logos, compact, contrast, onDisplayChange]);
  const [time24, setTime24] = useState(false);
  const [format, setFormat] = useState('per-game');
  const [chart, setChart] = useState('bars');
  const [credits, setCredits] = useState(false);
  const [activeSection, setActiveSection] = useState('general');
  const categories = [
    {
      id: 'general',
      title: 'General',
      description: 'App preferences and sample preview',
      Icon: Settings2,
    },
    {
      id: 'scoring',
      title: 'League & Scoring',
      description: 'Read-only sample league rules',
      Icon: ChartNoAxesCombined,
    },
    { id: 'notifications', title: 'Notifications', description: 'Alerts and updates', Icon: Bell },
    { id: 'display', title: 'Display', description: 'Theme and data presentation', Icon: Monitor },
    { id: 'data', title: 'Data & Sync', description: 'Current data capabilities', Icon: Database },
    { id: 'account', title: 'Account', description: 'Manage your connection', Icon: UserRound },
    { id: 'about', title: 'About', description: 'App details and credits', Icon: Info },
  ];
  return (
    <div className={`settings-screen ${contrast ? 'settings-high-contrast' : ''}`}>
      <div className="settings-heading">
        <Settings2 size={42} />
        <div>
          <h1>Settings</h1>
          <p>Customize this page’s session preview and review your data access.</p>
        </div>
      </div>
      <div className="settings-session-note">
        <Info size={17} />
        Display choices apply across the app for this session. Other controls change the synthetic
        preview below. All preferences stay in memory; closing the app resets them.
      </div>
      <div className="settings-grid">
        <nav aria-label="Settings sections" className="settings-nav panel">
          {categories.map(({ id, title, description, Icon }) => (
            <button
              type="button"
              key={id}
              onClick={() => {
                setActiveSection(id);
                document
                  .getElementById(`settings-${id}`)
                  ?.scrollIntoView?.({ block: 'start', behavior: 'smooth' });
              }}
              aria-pressed={activeSection === id}
            >
              <Icon size={25} />
              <span>
                <b>{title}</b>
                <small>{description}</small>
              </span>
            </button>
          ))}
        </nav>
        <div className="settings-center">
          <Panel className="settings-section">
            <div id="settings-general" className="settings-panel-heading">
              <Settings2 />
              <h2>General Settings</h2>
            </div>
            <div className="settings-row">
              <label htmlFor="settings-start-view">
                <b>Default view</b>
                <small>Choose the destination for the preview action</small>
              </label>
              <select
                id="settings-start-view"
                value={defaultView}
                onChange={(event) => setDefaultView(event.target.value as Screen)}
              >
                <option value="overview">Overview</option>
                <option value="roster">My Roster</option>
                <option value="planner">Schedule Planner</option>
                <option value="league">League</option>
              </select>
            </div>
            <div className="settings-row">
              <label htmlFor="settings-date-range">
                <b>Default date range</b>
                <small>Changes the sample preview’s time range</small>
              </label>
              <select
                id="settings-date-range"
                value={range}
                onChange={(event) => setRange(event.target.value)}
              >
                <option value="season">This Season</option>
                <option value="week">This Week</option>
              </select>
            </div>
            <div className="settings-row">
              <div>
                <b>Show projected stats</b>
                <small>Projections are unavailable in this demo</small>
              </div>
              <Toggle label="Show projected stats" checked={false} disabled />
            </div>
            <div className="settings-row">
              <div>
                <b>Show rostered %</b>
                <small>Provider roster percentages are not verified</small>
              </div>
              <Toggle label="Show rostered percentage" checked={false} disabled />
            </div>
            <div className="settings-row">
              <div>
                <b>Use 24-hour time</b>
                <small>Changes the time in the preview</small>
              </div>
              <Toggle
                label="Use 24-hour time"
                checked={time24}
                onChange={() => setTime24(!time24)}
              />
            </div>
            <details className="settings-preview-details">
              <summary>Open preference preview</summary>
              <div
                className={`settings-preview ${compact ? 'settings-preview-compact' : ''}`}
                role="region"
                aria-label="Preference preview"
              >
                <div className="settings-preview-title">
                  <span>SESSION PREVIEW · SYNTHETIC SAMPLE</span>
                  <b>{range === 'season' ? '2024–25 Season' : 'Week 14'}</b>
                </div>
                <div className="settings-preview-team">
                  {logos && <TeamMark code="TOR" />}
                  <strong>Sample skater</strong>
                  <span>
                    {format === 'total' ? '24 points · season total' : '1.2 points · per game'}
                  </span>
                </div>
                <div
                  className={`settings-preview-chart settings-chart-${chart}`}
                  aria-label={`Sample chart: ${chart}`}
                >
                  <i />
                  <i />
                  <i />
                  <i />
                  <i />
                  <span>{chart === 'bars' ? 'Bars' : 'Dots'} · illustrative scoring trend</span>
                </div>
                <p>Sample game time: {time24 ? '19:00' : '7:00 PM'}</p>
                <p>
                  Selected destination:{' '}
                  {defaultView === 'roster'
                    ? 'My Roster'
                    : defaultView === 'planner'
                      ? 'Schedule Planner'
                      : defaultView === 'league'
                        ? 'League'
                        : 'Overview'}
                </p>
                <Button onClick={() => onNavigate(defaultView)}>
                  Open selected view <ExternalLink size={15} />
                </Button>
              </div>
            </details>
          </Panel>
          <div className="settings-center-bottom">
            <Panel className="settings-section">
              <div id="settings-notifications" className="settings-panel-heading">
                <Bell />
                <h2>Notifications</h2>
              </div>
              <p className="settings-section-note">
                Unavailable: no alert delivery service or account connection is enabled.
              </p>
              {[
                'Game start alerts',
                'Player performance alerts',
                'Injury updates',
                'Roster and lineup changes',
                'Weekly matchup reminders',
                'Email notifications',
              ].map((title) => (
                <div className="settings-row" key={title}>
                  <b>{title}</b>
                  <Toggle label={title} checked={false} disabled />
                </div>
              ))}
            </Panel>
            <Panel className="settings-section">
              <div id="settings-scoring" className="settings-panel-heading">
                <ChartNoAxesCombined />
                <h2>League &amp; Scoring</h2>
              </div>
              <p className="settings-section-note">Read-only synthetic scoring sample.</p>
              {observed ? (
                <p>Scoring rules are unavailable in this bounded browser session.</p>
              ) : (
                <dl className="settings-list">
                  <div>
                    <dt>League</dt>
                    <dd>Riverside Hockey League</dd>
                  </div>
                  <div>
                    <dt>Scoring type</dt>
                    <dd>Head-to-Head Points</dd>
                  </div>
                  <div>
                    <dt>Goals / assists</dt>
                    <dd>3 / 2 points</dd>
                  </div>
                  <div>
                    <dt>Shots / blocks</dt>
                    <dd>0.5 / 0.5 points</dd>
                  </div>
                  <div>
                    <dt>Goalie win / shutout</dt>
                    <dd>4 / 3 points</dd>
                  </div>
                  <div>
                    <dt>Waiver type</dt>
                    <dd>Weekly (FAAB)</dd>
                  </div>
                  <div>
                    <dt>Playoffs</dt>
                    <dd>Weeks 22–24 · Top 6</dd>
                  </div>
                </dl>
              )}
              <Button onClick={() => onNavigate('league')}>
                {observed ? 'View league' : 'View demo league'} <Trophy size={16} />
              </Button>
            </Panel>
          </div>
        </div>
        <aside className="settings-right">
          <Panel className="settings-section">
            <div id="settings-display" className="settings-panel-heading">
              <Monitor />
              <h2>Display Settings</h2>
            </div>
            <div className="settings-row">
              <label htmlFor="settings-theme">
                <b>Theme</b>
                <small>Current supported appearance</small>
              </label>
              <select id="settings-theme" value="dark" disabled>
                <option value="dark">Dark Blue</option>
              </select>
            </div>
            <div className="settings-row">
              <div>
                <b>Show team logos</b>
                <small>Show team marks throughout this session</small>
              </div>
              <Toggle label="Show team logos" checked={logos} onChange={() => setLogos(!logos)} />
            </div>
            <div className="settings-row">
              <div>
                <b>Compact view</b>
                <small>Reduce table spacing throughout this session</small>
              </div>
              <Toggle
                label="Compact view"
                checked={compact}
                onChange={() => setCompact(!compact)}
              />
            </div>
            <div className="settings-row">
              <label htmlFor="settings-stats-format">
                <b>Stats format</b>
                <small>Changes the sample points display</small>
              </label>
              <select
                aria-label="Stats format"
                id="settings-stats-format"
                value={format}
                onChange={(event) => setFormat(event.target.value)}
              >
                <option value="per-game">Per Game</option>
                <option value="total">Season Total</option>
              </select>
            </div>
            <div className="settings-row">
              <label htmlFor="settings-chart-style">
                <b>Chart style</b>
                <small>Changes the sample trend display</small>
              </label>
              <select
                id="settings-chart-style"
                value={chart}
                onChange={(event) => setChart(event.target.value)}
              >
                <option value="bars">Bars</option>
                <option value="dots">Dots</option>
              </select>
            </div>
            <div className="settings-row">
              <div>
                <b>High contrast</b>
                <small>Increase contrast throughout this session</small>
              </div>
              <Toggle
                label="High contrast"
                checked={contrast}
                onChange={() => setContrast(!contrast)}
              />
            </div>
          </Panel>
          <Panel className="settings-section">
            <div id="settings-account" className="settings-panel-heading">
              <UserRound />
              <h2>Account</h2>
            </div>
            <div className="settings-account-detail">
              <UserRound />
              <div>
                <b>
                  {local?.view?.mode === 'private'
                    ? 'Account details not fetched'
                    : 'Not signed in'}
                </b>
                <small>No account details loaded</small>
              </div>
            </div>
            <div className="settings-account-detail">
              <LockKeyhole />
              <div>
                <b>
                  {observed
                    ? local?.view?.mode === 'private'
                      ? 'Private observation loaded'
                      : 'Yahoo disconnected'
                    : 'Yahoo disconnected'}
                </b>
                <small>Ongoing connection health is not verified</small>
              </div>
            </div>
            <Button className="primary" onClick={() => onNavigate('connections')}>
              <ExternalLink size={16} />
              Manage connection
            </Button>
          </Panel>
          <Panel className="settings-section">
            <div id="settings-data" className="settings-panel-heading">
              <Database />
              <h2>Data &amp; Sync</h2>
            </div>
            <p className="settings-section-note">
              Provider loads require the human-operated local launcher. No browser credentials,
              automated provider refresh or persistent private data. Use Connections for loaded
              source details.
            </p>
            <Button onClick={() => onNavigate('connections')}>View connection details</Button>
          </Panel>
          <Panel className="settings-section">
            <div id="settings-about" className="settings-panel-heading">
              <Info />
              <h2>About</h2>
            </div>
            <h3>Fantasy GM Hockey</h3>
            <p className="settings-section-note">
              Local frontend demo · v0.1.0
              <br />
              Synthetic fantasy data; historical NHL identity assets.
            </p>
            <Button onClick={() => setCredits(!credits)} aria-expanded={credits}>
              {credits ? 'Hide image credits' : 'View image credits'}
            </Button>
            <Button
              onClick={() =>
                onNotice('This local demo has no support portal or published legal documents yet.')
              }
            >
              Demo information <Info size={16} />
            </Button>
          </Panel>
        </aside>
      </div>
      {credits && <ImageCredits />}
    </div>
  );
}
