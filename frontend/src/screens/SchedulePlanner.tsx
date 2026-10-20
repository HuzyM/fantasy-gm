import { isObservation, scheduleDays } from '../api';
import { CalendarDays, ChevronLeft, ChevronRight, ArrowRight } from 'lucide-react';
import { useState } from 'react';
import type { ScreenProps } from '../application';
import { Button, Panel, TeamMark } from '../components/primitives';
import { PlayerHeadshot } from '../components/PlayerHeadshot';
import { Tabs } from '../components/Tabs';
import { RosterWeek } from '../components/RosterWeek';
import { daysForWeek, overviewFixture } from '../fixtures/overview';
import { dateLabel, shiftWeek } from '../view-model';
import type { Game, Player } from '../view-model';
import '../planner-comparison.css';

const members = (game: Game, players: readonly Player[]) =>
  game.observationConflict
    ? []
    : players.filter(
        (player) =>
          player.scheduleJoin !== 'unverified' &&
          (player.team === game.away || player.team === game.home),
      );

const selectionKey = (game: Game) =>
  JSON.stringify([
    game.id,
    game.away,
    game.home,
    game.startTimeUtc,
    game.time,
    game.state,
    game.upcomingEligible,
  ]);
const sourceQualification = (game: Game) =>
  game.upcomingEligible === true
    ? 'source scheduled qualification supplied'
    : game.upcomingEligible === false
      ? 'source scheduled qualification excluded'
      : 'source scheduled qualification unavailable';

export default function SchedulePlanner({
  search,
  players,
  onNavigate,
  onNotice,
  local,
}: ScreenProps) {
  const observed = isObservation(local?.view);
  const unresolved = players.filter((player) => player.scheduleJoin === 'unverified').length;
  const loadedStart = observed
    ? (local?.view?.schedule?.start ?? new Date().toISOString().slice(0, 10))
    : overviewFixture.weekStart;
  const [start, setStart] = useState(loadedStart);
  const [date, setDate] = useState(loadedStart);
  const [selectedKey, setSelectedKey] = useState('');
  const [filter, setFilter] = useState('all');
  const [highlight, setHighlight] = useState(true);
  const [tab, setTab] = useState('Preview');
  const [view, setView] = useState('Daily matchups');
  const days = observed ? scheduleDays(start, local?.view) : daysForWeek(start);
  const selectedDay = days.find((day) => day.date === date) ?? days[0]!;
  const query = search.trim().toLocaleLowerCase('en-US');
  const games = selectedDay.games.filter((game) => {
    const roster = members(game, players);
    return (
      (filter !== 'rostered' || roster.length > 0) &&
      (!query ||
        `${game.away} ${game.home} ${roster.map((player) => player.name).join(' ')}`
          .toLocaleLowerCase('en-US')
          .includes(query))
    );
  });
  const selectedGame = games.find((game) => selectionKey(game) === selectedKey) ?? games[0];
  const activeKey = selectedGame ? selectionKey(selectedGame) : '';
  const roster = selectedGame ? members(selectedGame, players) : [];
  const unknown =
    selectedDay.count.state === 'unknown' || selectedDay.count.state === 'unsupported';
  function moveWeek(direction: number) {
    const next = shiftWeek(start, direction);
    setStart(next);
    setDate(next);
    setSelectedKey('');
  }
  function chooseDate(value: string) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return;
    const parsed = new Date(`${value}T12:00:00Z`);
    if (Number.isNaN(parsed.getTime())) return;
    parsed.setUTCDate(parsed.getUTCDate() - ((parsed.getUTCDay() + 6) % 7));
    setStart(parsed.toISOString().slice(0, 10));
    setDate(value);
    setSelectedKey('');
  }
  return (
    <div className="planner-screen">
      <header className="planner-heading">
        <div className="planner-title">
          <CalendarDays size={34} />
          <div>
            <h1>Schedule Planner</h1>
            <p>See team schedules, explore roster coverage, and plan ahead.</p>
          </div>
        </div>
        <div className="planner-week-controls">
          <Button aria-label="Previous week" onClick={() => moveWeek(-1)}>
            <ChevronLeft size={18} />
          </Button>
          <div>
            <strong>
              {!observed && start === overviewFixture.weekStart ? 'WEEK 14' : 'WEEK VIEW'}
            </strong>
            <span>
              {dateLabel(start, { month: 'short', day: 'numeric' })} –{' '}
              {dateLabel(days[6]!.date, { month: 'short', day: 'numeric', year: 'numeric' })}
            </span>
          </div>
          <Button aria-label="Next week" onClick={() => moveWeek(1)}>
            <ChevronRight size={18} />
          </Button>
          <Button
            onClick={() => {
              setStart(loadedStart);
              setDate(loadedStart);
              setSelectedKey('');
            }}
          >
            {observed ? 'Loaded window' : 'Demo week'}
          </Button>
        </div>
      </header>
      <p className="planner-provenance">
        {observed ? 'LOCAL PROVIDER OBSERVATION' : 'DEMO · SYNTHETIC DATA'}{' '}
        <span>Team schedules; no confirmed player appearances.</span>
      </p>
      <section className="planner-week" aria-label="Planner week">
        {days.map((day) => {
          const countKnown = day.count.state === 'verified' || day.count.state === 'incomplete';
          const count = countKnown ? day.count.value : undefined;
          const matched = players.filter((player) =>
            day.games.some(
              (game) =>
                !game.observationConflict &&
                player.scheduleJoin !== 'unverified' &&
                (player.team === game.away || player.team === game.home),
            ),
          ).length;
          const label = dateLabel(day.date, { weekday: 'long', month: 'long', day: 'numeric' });
          return (
            <button
              key={day.date}
              className={`planner-day ${day.date === date ? 'planner-day-active' : ''}`}
              aria-label={`Select ${label}: ${day.count.state === 'incomplete' ? `${count} observed games, total unknown` : countKnown ? `${count} supplied games` : 'schedule unknown'}; ${countKnown ? `${matched} roster team matches` : 'roster coverage unknown'}`}
              aria-pressed={day.date === date}
              onClick={() => {
                setDate(day.date);
                setSelectedKey('');
              }}
            >
              <span className="planner-day-name">{dateLabel(day.date, { weekday: 'short' })}</span>
              <span>{dateLabel(day.date, { month: 'short', day: 'numeric' })}</span>
              <strong>
                {countKnown ? `${count}${day.count.state === 'incomplete' ? '+' : ''}` : 'Unknown'}
              </strong>
              <small>
                {day.count.state === 'incomplete'
                  ? 'OBSERVED GAMES'
                  : countKnown
                    ? 'NHL GAMES'
                    : 'COVERAGE'}
              </small>
              <b>{countKnown ? `${matched}${day.count.state === 'incomplete' ? '+' : ''}` : '—'}</b>
              <small>ROSTER TEAM MATCHES</small>
              <span className="planner-spark" aria-hidden="true">
                {Array.from({ length: 7 }, (_, i) => (
                  <i key={i} style={{ height: countKnown ? `${i < matched ? 28 : 7}px` : '4px' }} />
                ))}
              </span>
              <span className="planner-day-caption">
                {!countKnown
                  ? 'Not supplied'
                  : day.count.state === 'incomplete'
                    ? 'Partial coverage'
                    : count! >= 10
                      ? 'Heavy night'
                      : count! <= 5
                        ? 'Light night'
                        : 'Game night'}
              </span>
            </button>
          );
        })}
      </section>
      <Tabs
        items={['Daily matchups', 'Roster week'].map((value) => ({ value, label: value }))}
        value={view}
        onChange={setView}
        label="Planner view"
        idPrefix="planner-view"
        panelId="planner-view-panel"
        className="planner-view-tabs"
      />
      <div
        id="planner-view-panel"
        role="tabpanel"
        aria-labelledby={`planner-view-${view.replace(' ', '-')}`}
      >
        {view === 'Roster week' ? (
          <RosterWeek
            start={start}
            days={observed ? (local?.view?.schedule?.days ?? []) : days}
            players={players}
            search={search}
            observed={observed}
            observedAt={local?.view?.schedule?.observedAt}
            loadedWindow={observed ? (local?.view?.schedule ?? undefined) : undefined}
            onNavigate={onNavigate}
            onChooseDate={chooseDate}
          />
        ) : (
          <div className="planner-main">
            <Panel className="planner-matchups">
              <div className="planner-table-heading">
                <h2>
                  <CalendarDays size={23} />
                  {dateLabel(date, {
                    weekday: 'long',
                    month: 'long',
                    day: 'numeric',
                    year: 'numeric',
                  })}
                </h2>
                <div className="planner-filters">
                  <label>
                    Choose date
                    <input
                      type="date"
                      value={date}
                      onChange={(event) => chooseDate(event.target.value)}
                    />
                  </label>
                  <label>
                    Show games
                    <select value={filter} onChange={(event) => setFilter(event.target.value)}>
                      <option value="all">All games</option>
                      <option value="rostered">Roster team matches</option>
                    </select>
                  </label>
                  <label className="planner-checkbox">
                    <input
                      type="checkbox"
                      checked={highlight}
                      onChange={(event) => setHighlight(event.target.checked)}
                    />
                    Highlight roster
                  </label>
                </div>
              </div>
              {selectedDay.count.state === 'incomplete' && (
                <p className="planner-data-note">
                  Partial schedule: observed games only; the total is unknown.
                </p>
              )}
              <div
                className="planner-table-scroll"
                role="region"
                aria-label="Daily matchup table"
                tabIndex={0}
              >
                <table aria-label="Daily matchups">
                  <thead>
                    <tr>
                      <th scope="col">Time (ET)</th>
                      <th scope="col">Away</th>
                      <th scope="col">Home</th>
                      <th scope="col">Roster team matches</th>
                      <th scope="col">Matchup</th>
                    </tr>
                  </thead>
                  <tbody>
                    {games.map((game) => {
                      const matches = members(game, players);
                      const key = selectionKey(game);
                      return (
                        <tr
                          key={key}
                          className={`${key === activeKey ? 'planner-row-selected' : ''} ${highlight && matches.length ? 'planner-row-rostered' : ''}`}
                        >
                          <td>
                            {game.time}
                            {observed && (
                              <small className="observed-game-note">
                                {game.observationConflict
                                  ? `Conflicting observation · ${sourceQualification(game)} · `
                                  : ''}
                                {game.state}
                              </small>
                            )}
                          </td>
                          <td>
                            <div className="planner-team">
                              <TeamMark code={game.away} />
                              <b>{game.away}</b>
                            </div>
                          </td>
                          <td>
                            <div className="planner-team">
                              <TeamMark code={game.home} />
                              <b>{game.home}</b>
                            </div>
                          </td>
                          <td>
                            <div className="planner-roster-inline">
                              {matches.slice(0, 2).map((player) => (
                                <span key={player.id}>
                                  <PlayerHeadshot nhlId={player.nhlId} name={player.name} />
                                  <span>
                                    {player.name}
                                    <small>
                                      {player.position} · {player.team}
                                    </small>
                                  </span>
                                </span>
                              ))}
                              {matches.length > 2 && <b>+{matches.length - 2}</b>}
                              {!matches.length && (
                                <span>
                                  {game.observationConflict
                                    ? 'Conflicting observation · coverage unavailable'
                                    : observed && unresolved
                                      ? 'No supported join · affiliation unknown'
                                      : 'No roster team matches'}
                                </span>
                              )}
                            </div>
                          </td>
                          <td>
                            <Button
                              aria-label={`Select ${game.away} @ ${game.home}${game.observationConflict ? `, ${game.time}, ${game.state ?? 'UNKNOWN'}, ${sourceQualification(game)}` : ''}`}
                              aria-pressed={key === activeKey}
                              onClick={() => {
                                setSelectedKey(key);
                                setTab('Preview');
                              }}
                            >
                              <span>
                                {game.observationConflict ? (
                                  'Coverage unavailable'
                                ) : (
                                  <>
                                    {matches.length} roster{' '}
                                    {matches.length === 1 ? 'match' : 'matches'}
                                  </>
                                )}
                              </span>
                              <ChevronRight size={16} />
                            </Button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              {!games.length && (
                <p className="planner-empty">
                  {unknown
                    ? 'Schedule coverage is unknown for this date.'
                    : 'No matchups match your filters.'}
                </p>
              )}
            </Panel>
            <aside className="panel planner-detail" aria-label="Selected matchup">
              {selectedGame?.observationConflict ? (
                <div className="planner-empty">
                  <h2>Conflicting fixture observations</h2>
                  <p>
                    Selected observation: {selectedGame.away} @ {selectedGame.home} ·{' '}
                    {selectedGame.time} ET · {selectedGame.state ?? 'UNKNOWN'} ·{' '}
                    {sourceQualification(selectedGame)}.
                  </p>
                  <p>
                    Conflicting observations share one fixture ID. Matchup and roster coverage are
                    unavailable; player appearances remain unconfirmed. No conflicting variant
                    qualifies for scheduled counts.
                  </p>
                </div>
              ) : selectedGame ? (
                <>
                  <h2>
                    {selectedGame.away} @ {selectedGame.home}
                  </h2>
                  <p>
                    {dateLabel(date, { weekday: 'short', month: 'short', day: 'numeric' })} ·{' '}
                    {selectedGame.time} ET
                  </p>
                  <div className="planner-detail-teams">
                    <div>
                      <TeamMark code={selectedGame.away} large />
                      <b>{selectedGame.away}</b>
                    </div>
                    <span>@</span>
                    <div>
                      <TeamMark code={selectedGame.home} large />
                      <b>{selectedGame.home}</b>
                    </div>
                  </div>
                  <Tabs
                    items={['Preview', 'Rostered players', 'Stats'].map((value) => ({
                      value,
                      label: value,
                    }))}
                    value={tab}
                    onChange={setTab}
                    label="Matchup detail"
                    className="planner-tabs"
                    idPrefix="planner-detail"
                    panelId="planner-detail-panel"
                  />
                  <div
                    id="planner-detail-panel"
                    role="tabpanel"
                    aria-labelledby={`planner-detail-${tab.replace(' ', '-')}`}
                    className="planner-detail-panel"
                  >
                    {tab === 'Stats' ? (
                      <>
                        <h3>Matchup statistics</h3>
                        <p>
                          Team records, scoring projections and matchup rankings are unavailable. No
                          source is connected.
                        </p>
                      </>
                    ) : (
                      <>
                        <h3>
                          {tab === 'Preview' ? 'Roster coverage' : 'Your roster team matches'} (
                          {roster.length})
                        </h3>
                        <p>
                          Player appearances are not confirmed. Matching a team does not confirm a
                          lineup or start.
                        </p>
                        <ul>
                          {roster.map((player) => (
                            <li key={player.id}>
                              <PlayerHeadshot nhlId={player.nhlId} name={player.name} />
                              <div>
                                <b>{player.name}</b>
                                <span>
                                  {player.position} · {player.team}
                                </span>
                              </div>
                              <Button
                                aria-label={`View ${player.name} profile`}
                                onClick={() => onNavigate('profile', player.id)}
                              >
                                <ArrowRight size={16} />
                              </Button>
                            </li>
                          ))}
                        </ul>
                        {!roster.length && (
                          <p>
                            {observed && unresolved
                              ? 'No supported roster join. Unverified affiliations do not establish absence.'
                              : 'No roster players belong to these teams.'}
                          </p>
                        )}
                        {tab === 'Preview' && (
                          <p className="planner-data-note">
                            Projected scoring and team trends are unavailable.
                          </p>
                        )}
                      </>
                    )}
                  </div>
                  <Button className="planner-detail-action" onClick={() => onNavigate('roster')}>
                    View my roster <ArrowRight size={16} />
                  </Button>
                </>
              ) : (
                <div className="planner-empty">
                  <CalendarDays size={36} />
                  <h2>No matchup selected</h2>
                  <p>
                    {unknown
                      ? observed
                        ? local?.view?.schedule
                          ? 'Return to the loaded observation window. Coverage outside it is unknown.'
                          : 'No schedule observation was supplied. Load one through a new human-operated launcher session.'
                        : 'Load the demo week to explore supplied fixtures.'
                      : 'Change the search or game filter to select a matchup.'}
                  </p>
                </div>
              )}
            </aside>
          </div>
        )}
      </div>
      <div className="planner-bottom">
        <Panel className="planner-coverage">
          <h2>Weekly Roster Coverage</h2>
          <p>Roster players whose teams have a supplied fixture; appearances unconfirmed.</p>
          <div className="planner-coverage-bars">
            {days.map((day) => {
              const supplied = day.count.state === 'verified' || day.count.state === 'incomplete';
              const matches = players.filter((player) =>
                day.games.some(
                  (game) =>
                    !game.observationConflict &&
                    player.scheduleJoin !== 'unverified' &&
                    (player.team === game.away || player.team === game.home),
                ),
              ).length;
              return (
                <div key={day.date}>
                  <strong>
                    {supplied ? `${matches}${day.count.state === 'incomplete' ? '+' : ''}` : '—'}
                  </strong>
                  <i style={{ height: supplied ? `${8 + matches * 8}px` : '3px' }} />
                  <span>{dateLabel(day.date, { weekday: 'short' })}</span>
                </div>
              );
            })}
          </div>
        </Panel>
        <Panel className="planner-quick">
          <h2>Plan Your Week</h2>
          <Button onClick={() => onNavigate('roster')}>
            Review roster <ArrowRight size={16} />
          </Button>
          <Button onClick={() => onNavigate('comparison')}>
            Compare players <ArrowRight size={16} />
          </Button>
          <Button
            onClick={() =>
              onNotice('Lineup optimization and schedule export are unavailable in this demo.')
            }
          >
            About planner tools
          </Button>
          <p>
            {observed
              ? 'Observed team games only; complete coverage and player appearances remain unverified.'
              : 'Schedule values and roster coverage are synthetic examples.'}
          </p>
        </Panel>
      </div>
      {observed && (
        <Panel className="observation-panel">
          <h2>Observation Limits</h2>
          <p>
            Loaded window: {local?.view?.schedule?.start ?? 'Unavailable'} –{' '}
            {local?.view?.schedule?.end ?? 'Unavailable'} · America/Toronto. Source observed at{' '}
            {local?.view?.schedule?.observedAt ?? 'Unavailable'}. Reported affiliations may be
            stale. Game states below describe observations, including completed or uncertain
            fixtures; they do not establish upcoming appearances.
          </p>
          <p>
            {unresolved} roster identities have unresolved schedule joins. Team games do not prove
            appearances. Empty dates are not confirmed off-days.
          </p>
          <p>Source issues: {local?.view?.schedule?.issues.join(' · ') || 'No schedule loaded.'}</p>
          {local?.view?.schedule?.teams.map((team) => (
            <p key={team.code}>
              {team.code}: {team.observedGames} observed games · total{' '}
              {team.countComplete ? 'qualified by source' : 'unknown'} · {team.uncertainDated}{' '}
              uncertain dated · {team.unplaced} unplaced · back-to-back coverage{' '}
              {team.backToBackComplete ? 'qualified by source' : 'unverified'}
            </p>
          ))}
        </Panel>
      )}
    </div>
  );
}
