import { ChevronDown, ChevronLeft, ChevronRight } from 'lucide-react';
import { useState } from 'react';
import type { DaySchedule } from '../view-model';
import { dateLabel, describeDatum } from '../view-model';
import { Button, TeamMark } from './primitives';

function DayCard({
  day,
  selected,
  onSelect,
}: {
  day: DaySchedule;
  selected: boolean;
  onSelect: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const shown = expanded ? day.games : day.games.slice(0, 3);
  const remaining = day.games.length - 3;
  const count = describeDatum(day.count);
  const fullDate = dateLabel(day.date, { weekday: 'long', month: 'long', day: 'numeric' });
  return (
    <article className={`day-card ${selected ? 'active' : ''}`} aria-label={fullDate}>
      <button
        className="day-select"
        aria-pressed={selected}
        aria-label={`Select ${fullDate}`}
        onClick={onSelect}
      >
        <span className="day-name">{dateLabel(day.date, { weekday: 'short' })}</span>
        <span className="day-date">{dateLabel(day.date, { month: 'short', day: 'numeric' })}</span>
        <strong className={day.count.state === 'unknown' ? 'unknown-count' : ''} title={count.note}>
          {day.count.state === 'incomplete' ? `${day.count.value}+` : count.text}
        </strong>
        <small>
          {day.count.state === 'incomplete'
            ? 'OBSERVED GAMES'
            : day.count.state === 'unknown'
              ? 'COVERAGE UNKNOWN'
              : 'GAMES'}
        </small>
      </button>
      <ul className="mini-games" aria-label={`${fullDate} games`}>
        {shown.map((game) => (
          <li key={game.id}>
            <span>
              <TeamMark code={game.away} />
              <b>{game.away}</b>
            </span>
            <span className="versus">@</span>
            <span>
              <TeamMark code={game.home} />
              <b>{game.home}</b>
            </span>
            <time>{game.time}</time>
          </li>
        ))}
      </ul>
      {remaining > 0 && (
        <button
          className="more-games"
          aria-expanded={expanded}
          aria-label={
            expanded ? `Show fewer ${fullDate} games` : `${remaining} more games on ${fullDate}`
          }
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? 'Show less' : `+ ${remaining} more`}{' '}
          <ChevronDown size={12} className={expanded ? 'rotate' : ''} />
        </button>
      )}
      {count.note && (
        <span className="sr-only" title={count.note}>
          Partial · total unknown
        </span>
      )}
    </article>
  );
}

export function WeekSchedule({
  days,
  start,
  selectedDay,
  onSelectDay,
  onMove,
  onReset,
  isReference,
}: {
  days: readonly DaySchedule[];
  start: string;
  selectedDay: string;
  onSelectDay: (date: string) => void;
  onMove: (direction: number) => void;
  onReset: () => void;
  isReference: boolean;
}) {
  const last = days[6]?.date ?? start;
  return (
    <section className="week-section" aria-label="Weekly schedule">
      <div className="week-heading">
        <div className="week-spacer" />
        <div className="week-controls">
          <Button aria-label="Previous week" className="week-arrow" onClick={() => onMove(-1)}>
            <ChevronLeft size={20} />
          </Button>
          <div>
            <h1>{isReference ? 'WEEK 14' : 'WEEK VIEW'}</h1>
            <p>
              {dateLabel(start, { month: 'short', day: 'numeric' })} –{' '}
              {dateLabel(last, { month: 'short', day: 'numeric', year: 'numeric' })}
            </p>
          </div>
          <Button aria-label="Next week" className="week-arrow" onClick={() => onMove(1)}>
            <ChevronRight size={20} />
          </Button>
          <Button
            className="today-button"
            onClick={onReset}
            title="Return to the populated synthetic fixture week"
          >
            DEMO WEEK
          </Button>
        </div>
        <p className="arena-tagline">
          FANTASY HOCKEY
          <br />
          <strong>LIVES HERE</strong>
          <span />
        </p>
      </div>
      <div className="week-grid">
        {days.map((day) => (
          <DayCard
            key={day.date}
            day={day}
            selected={day.date === selectedDay}
            onSelect={() => onSelectDay(day.date)}
          />
        ))}
      </div>
      {!isReference && <p className="empty-schedule">No fixture games loaded for this week.</p>}
    </section>
  );
}
