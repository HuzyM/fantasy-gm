import { ChevronLeft, ChevronRight, CalendarDays } from 'lucide-react';
import { isObservation } from '../api';
import type { ScreenProps } from '../application';
import { overviewFixture } from '../fixtures/overview';
import { selectRosterWeek } from '../roster-week';
import { dateLabel, shiftWeek, type Player } from '../view-model';
import { Button, Panel } from './primitives';

export function ComparisonWeek({
  players,
  local,
  start,
  onStartChange,
}: {
  players: readonly [Player, Player];
  local: ScreenProps['local'];
  start: string;
  onStartChange: (start: string) => void;
}) {
  const observed = isObservation(local?.view);
  const schedule = observed ? local?.view?.schedule : undefined;
  const week = selectRosterWeek(
    start,
    observed ? (schedule?.days ?? []) : overviewFixture.days,
    players,
    observed,
    observed ? (schedule ?? undefined) : { start: overviewFixture.weekStart, end: '2026-12-13' },
  );
  const joined = week.rows.map((row) => !observed || row.player.scheduleJoin === 'matched');
  const shared = week.dates.filter((_, index) =>
    week.rows.every((row) => row.cells[index]!.fixtures.some((game) => game.eligible)),
  );
  return (
    <Panel className="comparison-week">
      <section role="region" aria-label="Weekly game comparison">
        <h2>
          <CalendarDays size={20} /> Schedule Comparison
        </h2>
        <div className="comparison-week-controls">
          <Button
            aria-label="Previous comparison week"
            onClick={() => onStartChange(shiftWeek(start, -1))}
          >
            <ChevronLeft size={18} /> Previous week
          </Button>
          <strong>
            {dateLabel(start, { month: 'short', day: 'numeric' })} –{' '}
            {dateLabel(week.dates[6]!, { month: 'short', day: 'numeric', year: 'numeric' })}
          </strong>
          <Button
            aria-label="Next comparison week"
            onClick={() => onStartChange(shiftWeek(start, 1))}
          >
            Next week <ChevronRight size={18} />
          </Button>
        </div>
        <p>
          {observed && 'America/Toronto · seven inclusive dates. '}
          {observed
            ? `Source observed at ${schedule?.observedAt ?? 'Unavailable'}. Reported affiliations may be stale.`
            : 'Synthetic games · demo observations only.'}{' '}
          Team games; player appearances are unconfirmed. Counts describe loaded observations;
          complete totals remain unknown.
        </p>
        <p>
          Back-to-back opportunities count adjacent qualifying Toronto dates inside this week.
          Shared game dates count each qualifying date once. Zero observed opportunities does not
          prove none exist.
        </p>
        <div className="comparison-week-summaries">
          {week.rows.map((row, index) => (
            <section key={row.player.id} aria-label={`${row.player.name} game summary`}>
              <h4>
                {row.player.name} · {row.player.team}
              </h4>
              <dl>
                <div>
                  <dt>{observed ? 'Observed scheduled games' : 'Synthetic scheduled games'}</dt>
                  <dd>{joined[index] ? row.scheduledCount : 'Unknown'}</dd>
                </div>
                <div>
                  <dt>Back-to-back opportunities</dt>
                  <dd>{joined[index] ? row.backToBackPairs : 'Unknown'}</dd>
                </div>
              </dl>
              <p>
                {joined[index]
                  ? 'Loaded observations; complete totals unknown.'
                  : 'Reported affiliation unavailable or unverified; schedule join unavailable.'}
              </p>
            </section>
          ))}
        </div>
        <p className="comparison-shared-summary">
          <strong>Shared game dates: {joined.every(Boolean) ? shared.length : 'Unknown'}</strong> ·{' '}
          {joined.every(Boolean)
            ? 'observed; total unknown'
            : 'Required affiliation join unavailable'}
        </p>
        <div className="comparison-week-dates">
          {week.dates.map((date, dateIndex) => (
            <section
              className="comparison-date-row"
              key={date}
              aria-label={dateLabel(date, {
                weekday: 'long',
                month: 'long',
                day: 'numeric',
                year: 'numeric',
              })}
            >
              <header>
                <h3>
                  <time dateTime={date}>
                    {dateLabel(date, { weekday: 'short', month: 'short', day: 'numeric' })}
                  </time>
                </h3>
                {shared.includes(date) && <strong>Shared game date</strong>}
              </header>
              {week.rows.map((row, playerIndex) => {
                const cell = row.cells[dateIndex]!;
                return (
                  <div
                    className="comparison-date-player"
                    key={row.player.id}
                    role="group"
                    aria-label={`${row.player.name} games on ${date}`}
                  >
                    <h4>
                      {row.player.name} · {row.player.team}
                    </h4>
                    {!joined[playerIndex] ? (
                      <p>Join unavailable</p>
                    ) : cell.fixtures.length ? (
                      <ul>
                        {cell.fixtures.map(({ game, eligible, status }, index) => (
                          <li key={`${game.id}-${index}`}>
                            {game.conflict && (
                              <strong>Disputed observation · excluded from counts</strong>
                            )}
                            <strong>
                              {game.home === row.player.team ? 'vs' : '@'}{' '}
                              {game.home === row.player.team ? game.away : game.home} ·{' '}
                              {game.home === row.player.team ? 'Home' : 'Away'}
                            </strong>
                            <span>
                              {game.startTimeUtc && Number.isFinite(Date.parse(game.startTimeUtc))
                                ? new Intl.DateTimeFormat('en-US', {
                                    timeZone: 'America/Toronto',
                                    hour: 'numeric',
                                    minute: '2-digit',
                                    timeZoneName: 'short',
                                  }).format(new Date(game.startTimeUtc))
                                : observed
                                  ? 'Time unavailable / unverified'
                                  : `${game.time} ET · synthetic`}
                            </span>
                            <span>
                              {!observed && eligible
                                ? 'Synthetic scheduled game'
                                : status === 'SCHEDULED'
                                  ? eligible
                                    ? 'Scheduled observation'
                                    : game.upcomingEligible === false
                                      ? 'Scheduled · source eligibility excluded'
                                      : 'Scheduled · source eligibility unavailable'
                                  : status.replaceAll('_', ' ')}
                            </span>
                            {game.conflict && (
                              <small>
                                Conflicting game ID; no authoritative variant selected. Reported
                                state: {game.state ?? 'UNKNOWN'}. Source eligibility:{' '}
                                {game.upcomingEligible === true
                                  ? 'eligible'
                                  : game.upcomingEligible === false
                                    ? 'excluded'
                                    : 'unavailable'}
                                .
                              </small>
                            )}
                            {!eligible && !game.conflict && (
                              <small>Excluded from scheduled counts and opportunities.</small>
                            )}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p>No qualifying game observed</p>
                    )}
                    {joined[playerIndex] && (
                      <small>
                        {cell.coverage === 'incomplete'
                          ? 'Partial observation · complete totals unknown'
                          : cell.coverage === 'verified'
                            ? 'Loaded date coverage · appearances unconfirmed'
                            : 'Coverage unknown'}
                      </small>
                    )}
                    {cell.backToBack && <strong>Back-to-back opportunity</strong>}
                    {cell.sameDayAnomaly && (
                      <p>Schedule anomaly: multiple scheduled team games observed on this date.</p>
                    )}
                  </div>
                );
              })}
            </section>
          ))}
        </div>
      </section>
    </Panel>
  );
}
