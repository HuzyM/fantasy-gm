import { useState } from 'react';
import { ArrowRight } from 'lucide-react';
import type { ScreenProps } from '../application';
import type { DaySchedule, Player } from '../view-model';
import { dateLabel } from '../view-model';
import { selectRosterWeek } from '../roster-week';
import { Button, Panel } from './primitives';

const positions = (player: Player) =>
  player.position
    .split(/[\/,]/)
    .map((p) => p.trim())
    .filter((p) => p && p !== 'Unknown');
const slot = (player: Player) =>
  player.rosterSlot.state === 'verified' || player.rosterSlot.state === 'incomplete'
    ? player.rosterSlot.value.trim() || 'Unknown'
    : 'Unknown';

export function RosterWeek({
  start,
  days,
  players,
  search,
  observed,
  observedAt,
  loadedWindow,
  onNavigate,
  onChooseDate,
}: {
  start: string;
  days: readonly DaySchedule[];
  players: readonly Player[];
  search: string;
  observed: boolean;
  observedAt?: string;
  loadedWindow?: { readonly start: string; readonly end: string };
  onNavigate: ScreenProps['onNavigate'];
  onChooseDate: (date: string) => void;
}) {
  const [position, setPosition] = useState('all');
  const [rosterSlot, setRosterSlot] = useState('all');
  const query = search.trim().toLocaleLowerCase('en-US');
  const filtered = players.filter(
    (player) =>
      (position === 'all' ||
        (position === 'Unknown'
          ? !positions(player).length
          : positions(player).includes(position))) &&
      (rosterSlot === 'all' || slot(player) === rosterSlot) &&
      `${player.name} ${player.team}`.toLocaleLowerCase('en-US').includes(query),
  );
  const week = selectRosterWeek(start, days, filtered, observed, loadedWindow);
  return (
    <Panel className="roster-week-panel">
      <div className="roster-week-heading">
        <div>
          <h2>Weekly roster schedule</h2>
          <p>Seven Toronto calendar dates · team fixtures; player appearances unconfirmed.</p>
        </div>
        <div className="planner-filters roster-week-filters">
          <label>
            Choose week date
            <input
              type="date"
              value={start}
              onChange={(event) => onChooseDate(event.target.value)}
            />
          </label>
          <label>
            Position eligibility
            <select value={position} onChange={(event) => setPosition(event.target.value)}>
              <option value="all">All positions</option>
              {[...new Set(players.flatMap(positions))].sort().map((value) => (
                <option key={value}>{value}</option>
              ))}
              <option>Unknown</option>
            </select>
          </label>
          <label>
            Reported roster slot
            <select value={rosterSlot} onChange={(event) => setRosterSlot(event.target.value)}>
              <option value="all">All slots</option>
              {[...new Set(players.map(slot))]
                .filter((value) => value !== 'Unknown')
                .sort()
                .map((value) => (
                  <option key={value}>{value}</option>
                ))}
              <option>Unknown</option>
            </select>
          </label>
        </div>
      </div>
      <p className="roster-week-note" id="roster-week-limits">
        {observed
          ? `Observed scheduled fixtures, not games remaining. Source observed at ${observedAt ?? 'Unavailable'}. Reported affiliations may be stale. Counts are loaded observations; complete totals are unknown.`
          : 'Synthetic fixture counts are examples, not provider observations.'}{' '}
        Empty cells do not establish off-days. Back-to-back opportunities require two eligible
        fixtures on consecutive dates wholly inside this week; none observed does not prove none
        exist. Roster slots do not establish lineup availability.
      </p>
      <div
        className="roster-week-scroll"
        role="region"
        aria-label="Scrollable weekly roster schedule"
        tabIndex={0}
      >
        <table
          className="roster-week-table"
          aria-label="Weekly roster schedule"
          aria-describedby="roster-week-limits"
        >
          <thead>
            <tr>
              <th scope="col">Player / reported team</th>
              {week.dates.map((date) => (
                <th scope="col" key={date}>
                  {dateLabel(date, { weekday: 'short' })}
                  <span>{dateLabel(date, { month: 'short', day: 'numeric' })}</span>
                </th>
              ))}
              <th scope="col">{observed ? 'Observed scheduled fixtures' : 'Synthetic fixtures'}</th>
              <th scope="col">Back-to-back opportunities</th>
            </tr>
          </thead>
          <tbody>
            {week.rows.map((row) => {
              const joined = !observed || row.player.scheduleJoin === 'matched';
              const opportunitiesKnown = joined && week.hasLoadedDates;
              return (
                <tr key={row.player.id}>
                  <th scope="row">
                    <Button
                      aria-label={`View ${row.player.name} profile`}
                      onClick={() => onNavigate('profile', row.player.id)}
                    >
                      {row.player.name}
                      <ArrowRight size={14} />
                    </Button>
                    <span>
                      {row.player.team} · {row.player.position}
                    </span>
                    <span>Slot: {slot(row.player)}</span>
                    {!joined && (
                      <small className="roster-week-warning">
                        Reported affiliation unavailable or unverified; schedule join unavailable.
                      </small>
                    )}
                  </th>
                  {row.cells.map((cell) => (
                    <td key={cell.date}>
                      {!joined ? (
                        <span className="roster-week-empty">Join unavailable</span>
                      ) : cell.fixtures.length ? (
                        <ul>
                          {cell.fixtures.map(({ game, eligible, status }, index) => (
                            <li
                              key={`${game.id}-${index}`}
                              className={
                                eligible ? 'roster-fixture-scheduled' : 'roster-fixture-other'
                              }
                            >
                              <strong>
                                {game.home === row.player.team ? 'vs' : '@'}{' '}
                                {game.home === row.player.team ? game.away : game.home}
                              </strong>
                              <span>
                                {game.startTimeUtc
                                  ? new Intl.DateTimeFormat('en-US', {
                                      timeZone: 'America/Toronto',
                                      hour: 'numeric',
                                      minute: '2-digit',
                                      timeZoneName: 'short',
                                    }).format(new Date(game.startTimeUtc))
                                  : game.time}
                              </span>
                              <small>
                                {!observed && eligible
                                  ? 'Synthetic fixture'
                                  : status === 'SCHEDULED'
                                    ? eligible
                                      ? 'Scheduled observation'
                                      : 'Scheduled · eligibility unverified'
                                    : status.replaceAll('_', ' ').toLocaleLowerCase('en-US')}
                              </small>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <span className="roster-week-empty">No qualifying fixture observed</span>
                      )}
                      {joined && cell.backToBack && (
                        <span className="roster-week-b2b">Back-to-back</span>
                      )}
                      {cell.sameDayAnomaly && (
                        <small className="roster-week-warning">
                          Schedule anomaly: multiple scheduled team games observed on this date.
                        </small>
                      )}
                      {joined && cell.coverage !== 'verified' && (
                        <small className="roster-week-coverage">
                          {cell.coverage === 'incomplete'
                            ? 'Partial observation'
                            : 'Coverage unknown'}
                        </small>
                      )}
                    </td>
                  ))}
                  <td className="roster-week-count">
                    {opportunitiesKnown ? row.scheduledCount : 'Unknown'}
                    {opportunitiesKnown && (
                      <small>{observed ? 'observed; total unknown' : 'synthetic'}</small>
                    )}
                  </td>
                  <td className="roster-week-count">
                    {opportunitiesKnown ? row.backToBackPairs : 'Unknown'}
                    {opportunitiesKnown && (
                      <small>
                        {row.backToBackPairs === 1 ? 'date pair' : 'date pairs'} observed
                      </small>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {!week.rows.length && <p className="planner-empty">No roster players match these filters.</p>}
      <p className="roster-week-note">
        Scroll the table to compare all seven dates. Position eligibility and reported roster slot
        are independent filters.
      </p>
    </Panel>
  );
}
