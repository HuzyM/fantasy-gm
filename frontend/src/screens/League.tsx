import { useState } from 'react';
import {
  ArrowRight,
  ChevronLeft,
  ChevronRight,
  Crown,
  Settings2,
  Trophy,
  Users,
  Activity,
  Info,
} from 'lucide-react';
import type { ScreenProps } from '../application';
import { Button, Panel, TeamMark } from '../components/primitives';
import '../league-preferences.css';

// Fictional fantasy teams and scores, independent of provider/account data.
const demoTeams = [
  {
    name: 'Northern Ice',
    logo: 'WPG',
    record: '9-4-1',
    points: 824,
    against: 712,
    streak: 'W3',
    moves: 28,
  },
  {
    name: 'Maple City Kings',
    logo: 'LAK',
    record: '9-4-1',
    points: 801,
    against: 738,
    streak: 'W1',
    moves: 24,
  },
  {
    name: 'Coastal Whalers',
    logo: 'CAR',
    record: '8-5-1',
    points: 789,
    against: 734,
    streak: 'L1',
    moves: 31,
  },
  {
    name: 'Prairie Storm',
    logo: 'TBL',
    record: '8-6-0',
    points: 776,
    against: 748,
    streak: 'W2',
    moves: 26,
  },
  {
    name: 'Redwood Rangers',
    logo: 'MIN',
    record: '7-6-1',
    points: 762,
    against: 751,
    streak: 'W1',
    moves: 22,
  },
  {
    name: 'Lakeside Blues',
    logo: 'STL',
    record: '7-6-1',
    points: 745,
    against: 760,
    streak: 'L2',
    moves: 29,
  },
  {
    name: 'Metro Polar Bears',
    logo: 'BOS',
    record: '6-7-1',
    points: 736,
    against: 769,
    streak: 'L1',
    moves: 18,
  },
  {
    name: 'Summit Sabres',
    logo: 'BUF',
    record: '6-7-1',
    points: 728,
    against: 772,
    streak: 'W2',
    moves: 25,
  },
  {
    name: 'Valley Vipers',
    logo: 'SJS',
    record: '5-8-1',
    points: 701,
    against: 780,
    streak: 'L3',
    moves: 34,
  },
  {
    name: 'Capital Citizens',
    logo: 'WSH',
    record: '5-8-1',
    points: 698,
    against: 791,
    streak: 'W1',
    moves: 21,
  },
  {
    name: 'Glacier Giants',
    logo: 'COL',
    record: '4-9-1',
    points: 680,
    against: 806,
    streak: 'L2',
    moves: 17,
  },
  {
    name: 'Bay Area Blades',
    logo: 'ANA',
    record: '4-10-0',
    points: 655,
    against: 819,
    streak: 'L4',
    moves: 20,
  },
];
const matches: readonly [number, number, number, number][] = [
  [0, 4, 124.6, 98.3],
  [1, 2, 118.2, 121.7],
  [3, 5, 105.4, 110.1],
  [6, 7, 96.8, 123.9],
  [8, 9, 101.6, 99.4],
  [10, 11, 112.7, 107.3],
];
type Sort = 'rank' | 'name' | 'points';

export default function League({ search, onNavigate }: ScreenProps) {
  const [league, setLeague] = useState('riverside');
  const [week, setWeek] = useState(14);
  const [sort, setSort] = useState<Sort>('rank');
  const [descending, setDescending] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [activity, setActivity] = useState('all');
  const teams = league === 'riverside' ? demoTeams : demoTeams.slice(0, 10);
  const visibleTeams = teams
    .map((team, rank) => ({ ...team, rank: rank + 1 }))
    .filter((team) => team.name.toLowerCase().includes(search.toLowerCase()))
    .sort((a, b) => {
      const order =
        sort === 'name'
          ? a.name.localeCompare(b.name)
          : sort === 'points'
            ? a.points - b.points
            : a.rank - b.rank;
      return descending ? -order : order;
    });
  const name = league === 'riverside' ? 'Riverside Hockey League' : 'Office Hockey Pool';
  function changeSort(next: Sort) {
    setDescending(sort === next ? !descending : next === 'points');
    setSort(next);
  }
  return (
    <div className="league-screen">
      <div className="league-heading">
        <div className="league-emblem">
          <Trophy size={48} />
        </div>
        <div>
          <span className="league-eyebrow">DEMO · SYNTHETIC DATA</span>
          <h1>{name}</h1>
          <p>
            {teams.length} Teams <span>│</span> H2H Points <span>│</span> 2024–25 sample season
          </p>
        </div>
        <label className="league-picker">
          Demo league
          <select value={league} onChange={(event) => setLeague(event.target.value)}>
            <option value="riverside">Riverside Hockey League</option>
            <option value="office">Office Hockey Pool</option>
          </select>
        </label>
      </div>
      <div className="league-facts">
        <span>
          <Users /> <b>{teams.length}</b> Teams
        </span>
        <span>
          <Trophy />
          <b>H2H Points</b> Scoring type
        </span>
        <span>
          <Settings2 />
          <b>Weekly (FAAB)</b> Sample waiver type
        </span>
        <span>
          <Crown />
          <b>Week 22</b> Sample playoffs begin
        </span>
      </div>
      <div className="league-main-grid">
        <Panel className="league-standings">
          <div className="league-panel-heading">
            <h2>Standings</h2>
            <span className="league-chip">2024–25 · Demo</span>
          </div>
          <div className="league-table-scroll">
            <table aria-label="Demo league standings">
              <thead>
                <tr>
                  <th
                    aria-sort={sort === 'rank' ? (descending ? 'descending' : 'ascending') : 'none'}
                  >
                    <button onClick={() => changeSort('rank')} aria-label="Sort by rank">
                      Rank
                    </button>
                  </th>
                  <th
                    aria-sort={sort === 'name' ? (descending ? 'descending' : 'ascending') : 'none'}
                  >
                    <button onClick={() => changeSort('name')} aria-label="Sort by team">
                      Team
                    </button>
                  </th>
                  <th>W-L-T</th>
                  <th
                    aria-sort={
                      sort === 'points' ? (descending ? 'descending' : 'ascending') : 'none'
                    }
                  >
                    <button onClick={() => changeSort('points')} aria-label="Sort by points">
                      Pts for
                    </button>
                  </th>
                  <th>Pts against</th>
                  <th>Streak</th>
                  <th>Moves</th>
                </tr>
              </thead>
              <tbody>
                {visibleTeams.slice(0, expanded ? 12 : 10).map((team) => (
                  <tr key={team.name} className={team.rank === 1 ? 'league-selected-row' : ''}>
                    <td>{team.rank}</td>
                    <td>
                      <span className="league-team">
                        <TeamMark code={team.logo} />
                        {team.name}
                      </span>
                    </td>
                    <td>{team.record}</td>
                    <td>
                      <strong>{team.points}</strong>
                    </td>
                    <td>{team.against}</td>
                    <td>{team.streak}</td>
                    <td>{team.moves}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!visibleTeams.length && (
              <p className="league-empty">No demo teams match “{search}”.</p>
            )}
          </div>
          <div className="league-panel-footer">
            <span>Fictional teams and scores. NHL logos identify visual samples.</span>
            <button onClick={() => setExpanded(!expanded)}>
              {expanded ? 'Show top 10' : 'View full standings'} <ArrowRight size={16} />
            </button>
          </div>
        </Panel>
        <div className="league-match-column">
          <Panel className="league-matchup">
            <div className="league-panel-heading">
              <h2>Current Matchup</h2>
              <span className="league-chip">Week {week} · Demo</span>
            </div>
            {week === 14 ? (
              <>
                <div className="league-versus">
                  <div>
                    <TeamMark code="WPG" large />
                    <h3>Northern Ice</h3>
                    <span>Fictional team</span>
                  </div>
                  <div className="league-score">
                    <b>124.6</b>
                    <small>VS</small>
                    <b>98.3</b>
                  </div>
                  <div>
                    <TeamMark code="MIN" large />
                    <h3>Redwood Rangers</h3>
                    <span>Fictional team</span>
                  </div>
                </div>
                <p className="league-disclaimer">
                  Projections and win probability unavailable. Demo scores only.
                </p>
              </>
            ) : (
              <p className="league-empty">No synthetic matchup scores loaded for Week {week}.</p>
            )}
          </Panel>
          <Panel className="league-weekly">
            <div className="league-panel-heading">
              <h2>Weekly Matchups</h2>
              <div className="league-week-controls">
                <button
                  aria-label="Previous matchup week"
                  disabled={week <= 1}
                  onClick={() => setWeek(week - 1)}
                >
                  <ChevronLeft size={17} />
                </button>
                <span>Week {week}</span>
                <button
                  aria-label="Next matchup week"
                  disabled={week >= 24}
                  onClick={() => setWeek(week + 1)}
                >
                  <ChevronRight size={17} />
                </button>
              </div>
            </div>
            {week === 14 ? (
              <div>
                {matches.map(([a, b, first, second]) => {
                  const left = teams[a];
                  const right = teams[b];
                  if (!left || !right) return null;
                  return (
                    <div className="league-week-row" key={a}>
                      <TeamMark code={left.logo} />
                      <span>{left.name}</span>
                      <b>{first.toFixed(1)}</b>
                      <small>vs</small>
                      <b>{second.toFixed(1)}</b>
                      <span>{right.name}</span>
                      <TeamMark code={right.logo} />
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="league-empty">Matchups unavailable for this sample week.</p>
            )}
          </Panel>
        </div>
      </div>
      <div className="league-bottom-grid">
        <Panel className="league-rule-panel">
          <div className="league-panel-heading">
            <h2>
              <Settings2 />
              League Settings
            </h2>
            <button onClick={() => onNavigate('settings')}>
              View settings <ArrowRight size={15} />
            </button>
          </div>
          <div className="league-rule-columns">
            <dl>
              <div>
                <dt>Roster size</dt>
                <dd>F 4 / D 2 / G 2 / UTIL 2</dd>
              </div>
              <div>
                <dt>Bench spots</dt>
                <dd>4</dd>
              </div>
              <div>
                <dt>IR spots</dt>
                <dd>2</dd>
              </div>
              <div>
                <dt>Acquisitions / week</dt>
                <dd>6</dd>
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
            <dl>
              <div>
                <dt>Goals</dt>
                <dd>3</dd>
              </div>
              <div>
                <dt>Assists</dt>
                <dd>2</dd>
              </div>
              <div>
                <dt>Shots on goal</dt>
                <dd>0.5</dd>
              </div>
              <div>
                <dt>Blocked shots</dt>
                <dd>0.5</dd>
              </div>
              <div>
                <dt>Goalie win</dt>
                <dd>4</dd>
              </div>
              <div>
                <dt>Shutouts</dt>
                <dd>3</dd>
              </div>
            </dl>
          </div>
          <p className="league-disclaimer">
            Read-only sample rules; provider settings are not verified.
          </p>
        </Panel>
        <Panel className="league-activity">
          <div className="league-panel-heading">
            <h2>
              <Activity />
              League Activity
            </h2>
            <select
              aria-label="Activity filter"
              value={activity}
              onChange={(event) => setActivity(event.target.value)}
            >
              <option value="all">All activity</option>
              <option value="transactions">Transactions</option>
              <option value="demo">Demo notes</option>
            </select>
          </div>
          {activity !== 'transactions' && (
            <div className="league-activity-item">
              <Info />
              <div>
                <b>Sample league loaded</b>
                <p>Explore standings and matchups using fictional data.</p>
                <small>Demo note · no provider timestamp</small>
              </div>
            </div>
          )}
          <p className="league-empty">
            Transactions unavailable. No live activity feed is connected.
          </p>
          <Button onClick={() => onNavigate('connections')}>
            Manage connection <ArrowRight size={15} />
          </Button>
        </Panel>
        <Panel className="league-playoffs">
          <div className="league-panel-heading">
            <h2>
              <Crown />
              Playoff Picture
            </h2>
            <span className="league-chip">Top 6 · Demo</span>
          </div>
          <ol>
            {teams.slice(0, 6).map((team) => (
              <li key={team.name}>
                <TeamMark code={team.logo} />
                <span>{team.name}</span>
                <b>{team.record}</b>
                <span>{team.points}</span>
              </li>
            ))}
          </ol>
          <p className="league-disclaimer">Illustrative seeds only. Qualification not verified.</p>
        </Panel>
      </div>
    </div>
  );
}
