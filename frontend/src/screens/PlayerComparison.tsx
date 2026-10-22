import { isObservation } from '../api';
import { ArrowLeftRight, ArrowRight, ChartNoAxesCombined } from 'lucide-react';
import { useState } from 'react';
import type { ScreenProps } from '../application';
import { PlayerHeadshot } from '../components/PlayerHeadshot';
import { Button, DataValue, Panel, TeamMark } from '../components/primitives';
import { Tabs } from '../components/Tabs';
import { overviewFixture } from '../fixtures/overview';
import { ComparisonWeek } from '../components/ComparisonWeek';
import { canUseManualPlan, PreparePlan } from '../components/ManualPlan';
import type { Datum, Player } from '../view-model';
import { getPlayerPhoto, teamAssets } from '../media';
import '../planner-comparison.css';

type Mode = 'totals' | 'per-game';
const unavailable: Datum<number> = { state: 'unsupported', reason: 'No statistic was supplied.' };

function statistic(player: Player, label: string, mode: Mode): Datum<number> {
  const datum = player.stats.find((stat) => stat.label === label)?.datum ?? unavailable;
  if (
    mode === 'totals' ||
    label === 'GP' ||
    datum.state === 'unknown' ||
    datum.state === 'unsupported'
  )
    return datum;
  const games = player.stats.find((stat) => stat.label === 'GP')?.datum;
  if (!games || games.state !== 'verified' || games.value <= 0)
    return {
      state: 'unknown',
      reason: 'A complete positive games-played denominator is required.',
    };
  return { ...datum, value: datum.value / games.value };
}

function PlayerCard({
  player,
  side,
  onProfile,
}: {
  player: Player;
  side: 'left' | 'right';
  onProfile: () => void;
}) {
  return (
    <div className={`comparison-player-hero comparison-player-${side}`}>
      <div className="comparison-portrait">
        <PlayerHeadshot nhlId={player.nhlId} name={player.name} variant="hero" />
      </div>
      <div className="comparison-watermark">
        <TeamMark code={player.team} large />
      </div>
      <div className="comparison-player-copy">
        <h2>{player.name}</h2>
        {player.identitySource === 'yahoo' && (
          <p className="returned-player-reference">
            Returned player reference: <span>{player.id}</span>
          </p>
        )}
        <p>
          {player.number === undefined ? 'Number unknown' : `#${player.number}`} &nbsp; | &nbsp;{' '}
          {player.position}
        </p>
        <div className="comparison-identity">
          <TeamMark code={player.team} />
          <span>{teamAssets[player.team]?.name ?? player.team}</span>
        </div>
        <span className="comparison-badge">
          {player.identitySource === 'yahoo' ? 'Reported roster' : 'Synthetic roster'} ·{' '}
          {player.position}
        </span>
        <p>
          {getPlayerPhoto(player.nhlId, player.name)
            ? 'Historical licensed photograph'
            : 'Player photograph unavailable'}
        </p>
        <Button onClick={onProfile} aria-label={`View ${player.name} profile`}>
          View profile <ArrowRight size={14} />
        </Button>
      </div>
    </div>
  );
}

function Summary({ player }: { player: Player }) {
  return (
    <div className="comparison-kpis">
      <div>
        <strong>
          <DataValue datum={player.weeklyPoints} format={(value) => value.toFixed(1)} />
        </strong>
        <small>Supplied weekly points</small>
      </div>
      <div>
        <strong>
          <DataValue datum={player.average} format={(value) => value.toFixed(1)} />
        </strong>
        <small>Supplied average</small>
      </div>
      <div>
        <strong>
          <DataValue datum={statistic(player, 'GP', 'totals')} />
        </strong>
        <small>Games played</small>
      </div>
    </div>
  );
}

function Statistics({
  player,
  other,
  mode,
  side,
}: {
  player: Player;
  other: Player;
  mode: Mode;
  side: 'left' | 'right';
}) {
  return (
    <Panel className={`comparison-stats comparison-stats-${side}`}>
      <h3>{player.name}</h3>
      <p>Supplied statistics · {mode === 'totals' ? 'Supplied totals' : 'Per supplied game'}</p>
      {['GP', 'G', 'A', 'PTS', 'SOG', 'BLK'].map((label) => {
        const datum = statistic(player, label, mode);
        const opposing = statistic(other, label, mode);
        const value =
          datum.state === 'verified' || datum.state === 'incomplete' ? datum.value : undefined;
        const otherValue =
          opposing.state === 'verified' || opposing.state === 'incomplete'
            ? opposing.value
            : undefined;
        const max = Math.max(value ?? 0, otherValue ?? 0, 1);
        return (
          <div className="comparison-stat-row" key={label}>
            <span>{label}</span>
            <DataValue
              datum={datum}
              format={(value) =>
                mode === 'per-game' && label !== 'GP' ? value.toFixed(2) : String(value)
              }
            />
            <span className="comparison-bar" aria-hidden="true">
              {value !== undefined && <i style={{ width: `${(value / max) * 100}%` }} />}
            </span>
          </div>
        );
      })}
    </Panel>
  );
}

export default function PlayerComparison({
  search,
  players,
  onNavigate,
  selectedId,
  local,
  comparisonStart,
  context,
}: ScreenProps & { selectedId?: string; comparisonStart?: string }) {
  const observed = isObservation(local?.view);
  const exactReturn = !!context?.comparisonRightId;
  const initialLeft = exactReturn
    ? players.find((player) => player.id === selectedId)
    : (players.find((player) => player.id === selectedId) ??
      players.find((player) => player.nhlId === 8479318) ??
      players[0]);
  const initialRight = exactReturn
    ? players.find(
        (player) => player.id === context.comparisonRightId && player.id !== initialLeft?.id,
      )
    : (players.find((player) => player.nhlId === 8477492 && player.id !== initialLeft?.id) ??
      players.find((player) => player.id !== initialLeft?.id));
  const [leftId, setLeftId] = useState(initialLeft?.id ?? '');
  const [rightId, setRightId] = useState(initialRight?.id ?? '');
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState<Mode>('totals');
  const [tab, setTab] = useState(comparisonStart || observed ? 'Schedule' : 'Statistics');
  const [start, setStart] = useState(
    comparisonStart ??
      (observed
        ? (local?.view?.planningWindow?.start ?? local?.view?.schedule?.start ?? '')
        : overviewFixture.weekStart),
  );
  const [reviewDate, setReviewDate] = useState(context?.reviewDate ?? start);
  const left = players.find((player) => player.id === leftId) ?? initialLeft;
  const right = players.find((player) => player.id === rightId);
  const queries = [search, query].map((value) => value.trim().toLocaleLowerCase('en-US'));
  const choices = players.filter((player) => {
    const identity = `${player.name} ${player.team}`.toLocaleLowerCase('en-US');
    return queries.every((value) => !value || identity.includes(value));
  });
  function selectPlayer(side: 'left' | 'right', value: string) {
    if (side === 'left') {
      if (value === right?.id) setRightId(left?.id ?? '');
      setLeftId(value);
    } else {
      if (value === left?.id) setLeftId(right?.id ?? '');
      setRightId(value);
    }
  }
  function picker(side: 'left' | 'right', player: Player) {
    const options = choices.some((choice) => choice.id === player.id)
      ? choices
      : [player, ...choices];
    return (
      <label className="comparison-picker">
        {side === 'left' ? 'First player' : 'Second player'}
        <select value={player.id} onChange={(event) => selectPlayer(side, event.target.value)}>
          {options.map((option) => (
            <option key={option.id} value={option.id}>
              {option.name} · {option.team} · {option.position}
              {observed ? ` · ${option.id}` : ''}
            </option>
          ))}
        </select>
      </label>
    );
  }
  if (!left || !right)
    return (
      <div className="comparison-screen">
        <header className="comparison-heading">
          <h1>Player Comparison</h1>
        </header>
        <Panel className="comparison-empty">
          <p>
            {players.length === 0
              ? 'No players are available to compare.'
              : 'At least two supplied players are required to compare.'}
          </p>
          <Button onClick={() => onNavigate('roster')}>View roster</Button>
        </Panel>
      </div>
    );
  return (
    <div className="comparison-screen">
      <header className="comparison-heading">
        <div>
          <h1>Player Comparison</h1>
          <p>Compare players head-to-head with stats, schedules and roster context.</p>
        </div>
        <p className="comparison-provenance">
          {observed ? 'LOCAL PROVIDER OBSERVATION' : 'DEMO · SYNTHETIC DATA'}
        </p>
      </header>
      <div className="comparison-controls">
        <label>
          Find a comparison player
          <input
            type="search"
            value={query}
            placeholder="Search supplied players or teams"
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>
        {(!observed || tab === 'Statistics') && (
          <label>
            Statistics view
            <select value={mode} onChange={(event) => setMode(event.target.value as Mode)}>
              <option value="totals">Supplied totals</option>
              <option value="per-game">Per game</option>
            </select>
          </label>
        )}
        <span className="comparison-provenance">
          {observed
            ? 'Performance unavailable; no provider statistics supplied'
            : 'Synthetic statistics · supplied game sample'}
        </span>
      </div>
      {choices.length === 0 && (
        <p className="comparison-provenance">
          No matching player choices. Current selections are retained.
        </p>
      )}
      <div className="comparison-hero">
        <section
          className="comparison-contender comparison-contender-left"
          aria-label="First comparison player"
        >
          {picker('left', left)}
          <PlayerCard player={left} side="left" onProfile={() => onNavigate('profile', left.id)} />
          {!observed && <Summary player={left} />}
        </section>
        <div className="comparison-vs">
          <strong aria-hidden="true">VS</strong>
          <Button
            aria-label="Swap players"
            onClick={() => {
              setLeftId(right.id);
              setRightId(left.id);
            }}
          >
            <ArrowLeftRight size={15} />
            Swap players
          </Button>
        </div>
        <section
          className="comparison-contender comparison-contender-right"
          aria-label="Second comparison player"
        >
          {picker('right', right)}
          <PlayerCard
            player={right}
            side="right"
            onProfile={() => onNavigate('profile', right.id)}
          />
          {!observed && <Summary player={right} />}
        </section>
      </div>
      <Tabs
        items={['Statistics', 'Schedule', 'History'].map((value) => ({ value, label: value }))}
        value={tab}
        onChange={setTab}
        label="Comparison views"
        className="comparison-tabs"
        idPrefix="comparison-view"
        panelId="comparison-panel"
      />
      <div id="comparison-panel" role="tabpanel" aria-labelledby={`comparison-view-${tab}`}>
        {tab === 'Statistics' && (
          <div className="comparison-stat-grid">
            <Statistics player={left} other={right} mode={mode} side="left" />
            <Panel className="comparison-history">
              <h2>Recent Performance</h2>
              <p>Game-by-game comparison</p>
              <div className="comparison-chart-empty">
                <ChartNoAxesCombined size={39} />
                <p>Historical performance is unavailable. No game log was supplied.</p>
              </div>
              <p>Season totals cannot establish recent form or head-to-head history.</p>
            </Panel>
            <Statistics player={right} other={left} mode={mode} side="right" />
          </div>
        )}
        {tab === 'Schedule' && (
          <>
            <ComparisonWeek
              players={[left, right]}
              local={local}
              start={start}
              onStartChange={(next) => {
                setStart(next);
                setReviewDate(next);
              }}
            />
            {canUseManualPlan(local) && (
              <section className="panel manual-plan" aria-label="Prepare comparison review">
                <h2>Review this pair</h2>
                <label>
                  Comparison review date
                  <input
                    type="date"
                    value={reviewDate}
                    min={start}
                    max={new Date(Date.parse(`${start}T12:00:00Z`) + 6 * 86400000)
                      .toISOString()
                      .slice(0, 10)}
                    onChange={(event) => setReviewDate(event.target.value)}
                  />
                </label>
                <PreparePlan
                  players={[left, right]}
                  local={local}
                  onNavigate={onNavigate}
                  date={reviewDate}
                  start={start}
                  origin="comparison"
                >
                  Prepare comparison review
                </PreparePlan>
              </section>
            )}
          </>
        )}
        {tab === 'History' && (
          <Panel className="comparison-history">
            <h2>Head-to-Head History</h2>
            <div className="comparison-chart-empty">
              <ChartNoAxesCombined size={36} />
              <p>
                Head-to-head results and game history are unavailable. No historical games were
                supplied.
              </p>
            </div>
          </Panel>
        )}
      </div>
      <div className="comparison-bottom">
        <Panel className="comparison-insights">
          <h2>Comparison Context</h2>
          <p>
            Projections, news and rankings are unavailable. No performance provider is connected.
          </p>
          <dl>
            <div>
              <dt>Statistics</dt>
              <dd>
                {observed
                  ? 'No performance observations supplied.'
                  : 'Sample values are synthetic.'}{' '}
                Per-game statistics divide supplied totals by supplied games played; they are not
                projections.
              </dd>
            </div>
            <div>
              <dt>Schedule coverage</dt>
              <dd>
                {observed
                  ? 'Complete schedule and affiliation coverage remain unverified.'
                  : 'Thursday is partial.'}{' '}
                An absent game is not a confirmed off-day.
              </dd>
            </div>
            <div>
              <dt>Player identity</dt>
              <dd>
                NHL photo identities require a verified mapping; Yahoo identities are never matched
                approximately. Historical photographs are separate from performance data.
              </dd>
            </div>
          </dl>
          <Button onClick={() => onNavigate('roster')}>
            Review my roster <ArrowRight size={15} />
          </Button>
        </Panel>
      </div>
    </div>
  );
}
