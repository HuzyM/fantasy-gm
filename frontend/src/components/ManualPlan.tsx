import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode, Dispatch, SetStateAction, FormEvent } from 'react';
import type { ScreenProps } from '../application';
import { selectRosterWeek } from '../roster-week';
import { Button } from './primitives';
import '../manual-plan.css';

const factualReasons = {
  unavailable: 'Schedule coverage unavailable; verify reported affiliation or assignment in Yahoo.',
  shared: 'Shared game date observed; review prompt only, not a slot-capacity conflict.',
  observed:
    'Review observed team games and reported assignments; complete coverage and appearances remain unverified.',
};

export function canUseManualPlan(local: ScreenProps['local']): boolean {
  return (
    local?.state === 'private' &&
    local.view?.mode === 'private' &&
    local.view.source === 'yahoo' &&
    !!local.view.roster
  );
}

interface ReviewItem {
  id: string;
  playerIds: string[];
  start: string;
  end: string;
  context: 'profile' | 'roster' | 'planner' | 'comparison';
  qualifications: string[];
  date: string;
  action: string;
  reason: string;
  reviewed: boolean;
}
type PreparedReview = Pick<
  ReviewItem,
  'playerIds' | 'date' | 'start' | 'end' | 'context' | 'qualifications' | 'reason'
>;
const PlanContext = createContext<{
  items: ReviewItem[];
  setItems: Dispatch<SetStateAction<ReviewItem[]>>;
  noAction: boolean;
  setNoAction: Dispatch<SetStateAction<boolean>>;
  draft: PreparedReview | null;
  setDraft: Dispatch<SetStateAction<PreparedReview | null>>;
} | null>(null);

/** Mounted above route screens, discarded with the current observation source. */
export function ManualPlanProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [noAction, setNoAction] = useState(false);
  const [draft, setDraft] = useState<PreparedReview | null>(null);
  return (
    <PlanContext value={{ items, setItems, noAction, setNoAction, draft, setDraft }}>
      {children}
    </PlanContext>
  );
}

// Reuse the weekly observation selector, including its duplicate/conflict and eligibility rules.
function observationQualifications(
  players: ScreenProps['players'],
  local: ScreenProps['local'],
  start: string,
  date: string,
) {
  const schedule = local?.view?.schedule;
  const week = selectRosterWeek(start, schedule?.days ?? [], players, true, schedule ?? undefined);
  const notes = [
    `Source observed at ${schedule?.observedAt ?? 'Unavailable'}. Local retrieval does not establish provider freshness.`,
    'Reported affiliations may be stale. Coverage and player appearances remain unverified. Shared game dates are review prompts, not slot-capacity conflicts. Back-to-back opportunities do not confirm goalie starts or appearances.',
  ];
  const coverage = schedule?.days.find((day) => day.date === date)?.count;
  if (coverage && (coverage.state === 'incomplete' || coverage.state === 'unknown'))
    notes.push(`Date coverage qualification: ${coverage.reason}`);
  for (const row of week.rows) {
    const cell = row.cells.find((cell) => cell.date === date);
    notes.push(
      `${row.player.name} · ${row.player.id}: ${!schedule || row.player.scheduleJoin !== 'matched' ? 'Schedule coverage unavailable; reported affiliation may be unavailable or stale. No game is asserted by this review item.' : `Date coverage: ${cell?.coverage ?? 'unknown'}; complete totals unknown.`}`,
    );
    if (row.player.scheduleJoin !== 'matched') {
      notes.push(
        `${row.player.id}: Reported schedule association ${local?.view?.roster?.entries.find((entry) => entry.id === row.player.id)?.scheduleStatus ?? 'unavailable'}; schedule join unavailable.`,
      );
      continue;
    }
    for (const fixture of cell?.fixtures ?? []) {
      const game = fixture.game;
      notes.push(
        `${row.player.id}: ${game.away} @ ${game.home} · ${game.startTimeUtc ?? 'Time unavailable / unverified'} · ${fixture.status} · source eligibility ${game.upcomingEligible === true ? 'eligible' : game.upcomingEligible === false ? 'excluded' : 'unavailable'}. ${game.conflict ? 'Conflicting game ID; no authoritative variant selected. Excluded from scheduled counts and opportunities.' : fixture.eligible ? 'Scheduled observation; appearance unconfirmed.' : 'Excluded from scheduled counts and opportunities.'}`,
      );
    }
    if (cell?.backToBack)
      notes.push(
        `${row.player.id}: Back-to-back opportunity observed; no player start is confirmed.`,
      );
    if (cell?.sameDayAnomaly)
      notes.push(
        `${row.player.id}: Schedule anomaly: multiple scheduled team games observed on this date.`,
      );
    if (schedule && !cell?.fixtures.length)
      notes.push(`${row.player.id}: No qualifying game observed; no off-day is established.`);
    const team = schedule?.teams.find((team) => team.code === row.player.team);
    if (team)
      notes.push(
        `${team.code}: ${team.uncertainDated} uncertain dated · ${team.unplaced} unplaced observations; complete coverage unverified.`,
      );
  }
  if (
    players.length === 2 &&
    week.rows.every((row) =>
      row.cells.find((cell) => cell.date === date)?.fixtures.some((fixture) => fixture.eligible),
    )
  )
    notes.push('Shared game date observed; review prompt only, not a slot-capacity conflict.');
  if (schedule?.issues.length) notes.push(`Source issues: ${schedule.issues.join(' · ')}`);
  return notes;
}

export function PreparePlan({
  players,
  local,
  onNavigate,
  date,
  start,
  origin,
  children,
}: Pick<ScreenProps, 'players' | 'local' | 'onNavigate'> & {
  date: string;
  start: string;
  origin: PreparedReview['context'];
  children: ReactNode;
}) {
  const plan = useContext(PlanContext);
  const window = local?.view?.planningWindow;
  if (!canUseManualPlan(local) || !plan || !window || !players.length) return null;
  const available =
    start === window.start &&
    date >= window.start &&
    date <= window.end &&
    (origin !== 'comparison' || (players.length === 2 && players[0]!.id !== players[1]!.id));
  return (
    <>
      <Button
        disabled={!available}
        onClick={() => {
          const qualifications = observationQualifications(players, local, start, date);
          plan.setDraft({
            playerIds: players.map((player) => player.id),
            date,
            start: window.start,
            end: window.end,
            context: origin,
            qualifications,
            reason:
              !local?.view?.schedule || players.some((player) => player.scheduleJoin !== 'matched')
                ? 'Schedule coverage unavailable; verify reported affiliation or assignment in Yahoo.'
                : qualifications.includes(
                      'Shared game date observed; review prompt only, not a slot-capacity conflict.',
                    )
                  ? 'Shared game date observed; review prompt only, not a slot-capacity conflict.'
                  : 'Review observed team games and reported assignments; complete coverage and appearances remain unverified.',
          });
          onNavigate('planner', undefined, {
            comparisonStart: window.start,
            reviewDate: date,
            showPlan: true,
          });
        }}
      >
        {children}
      </Button>
      {!available && (
        <p>
          Context review unavailable for an unloaded alternate window. A new explicitly confirmed
          human launcher load is required; browsing and plan actions make no provider requests.
        </p>
      )}
    </>
  );
}

export function ManualPlan({
  players,
  local,
  onNavigate,
}: Pick<ScreenProps, 'players' | 'local' | 'onNavigate'>) {
  const plan = useContext(PlanContext);
  const window = local?.view?.planningWindow;
  const [prepared, setPrepared] = useState(plan?.draft ?? null);
  const [playerId, setPlayerId] = useState(prepared?.playerIds[0] ?? '');
  const [date, setDate] = useState(prepared?.date ?? window?.start ?? '');
  const [action, setAction] = useState('');
  const [reason, setReason] = useState(prepared?.reason ?? '');
  const [message, setMessage] = useState('');
  const [editing, setEditing] = useState<string | null>(null);
  useEffect(() => {
    plan?.setDraft(null);
  }, [plan?.setDraft]);
  const preparedQualifications = useMemo(
    () =>
      prepared && window
        ? observationQualifications(
            players.filter((player) => prepared.playerIds.includes(player.id)),
            local,
            window.start,
            date,
          )
        : [],
    [prepared?.playerIds, local?.view, window?.start, date, players],
  );
  if (!canUseManualPlan(local) || !plan || !window) return null;
  function submit(event: FormEvent) {
    event.preventDefault();
    const parsed = new Date(`${date}T12:00:00Z`);
    if (
      !window ||
      !players.some((player) => player.id === playerId) ||
      !/^\d{4}-\d{2}-\d{2}$/.test(date) ||
      !Number.isFinite(parsed.getTime()) ||
      parsed.toISOString().slice(0, 10) !== date ||
      date < window.start ||
      date > window.end ||
      !action.trim() ||
      !reason.trim()
    ) {
      setMessage(
        'Choose a returned player, a date inside the planning window, an action and a reason.',
      );
      return;
    }
    if (editing) {
      plan!.setItems((items) =>
        items.map((item) =>
          item.id === editing
            ? {
                ...item,
                date,
                action: action.trim(),
                reason: reason.trim(),
                qualifications: observationQualifications(
                  players.filter((player) => item.playerIds.includes(player.id)),
                  local,
                  item.start,
                  date,
                ),
                reviewed: false,
              }
            : item,
        ),
      );
    } else {
      const playerIds = prepared?.playerIds ?? [playerId];
      plan!.setItems((items) => [
        ...items,
        {
          id: crypto.randomUUID(),
          playerIds: [...playerIds],
          start: window!.start,
          end: window!.end,
          context: prepared?.context ?? 'profile',
          qualifications: observationQualifications(
            players.filter((player) => playerIds.includes(player.id)),
            local,
            window!.start,
            date,
          ),
          date,
          action: action.trim(),
          reason: reason.trim(),
          reviewed: false,
        },
      ]);
    }
    plan!.setNoAction(false);
    plan!.setDraft(null);
    setPrepared(null);
    setAction('');
    setReason('');
    setEditing(null);
    setMessage(editing ? 'Review item updated and returned to pending.' : 'Review item added.');
  }
  return (
    <section className="panel manual-plan" aria-label="Manual plan">
      <h2>Manual plan</h2>
      <p>
        Planning window: {window.start} – {window.end} · America/Toronto. Manual review only.
      </p>
      <p>
        Private sessions last 20 minutes from loading. Planning does not extend expiry or refresh
        observations. Reload loses this plan and the browser capability. Reopening a valid launcher
        link can reload observations, but cannot recover the plan. Disconnect, observed expiry/lock,
        session or source replacement and server restart discard private items. A suspended browser
        clears when unavailability is observed.
      </p>
      <p>
        Reviewed means human acknowledgement only. Coverage, reported affiliations and assignments
        remain unverified; team games do not confirm player appearances. Make any chosen changes
        manually in Yahoo.
      </p>
      {!players.length ? (
        <p>No returned owned-roster player is available for a review item.</p>
      ) : (
        <form onSubmit={submit} noValidate autoComplete="off">
          <label>
            Returned player
            <select
              value={playerId}
              onChange={(event) => setPlayerId(event.target.value)}
              required
              disabled={!!editing || !!prepared}
            >
              <option value="">Choose a returned player</option>
              {players.map((player) => (
                <option key={player.id} value={player.id}>
                  {player.name} · {player.id}
                </option>
              ))}
            </select>
          </label>
          {prepared?.playerIds.length === 2 && (
            <p>
              Compared pair:{' '}
              {prepared.playerIds
                .map((id) => `${players.find((player) => player.id === id)?.name} · ${id}`)
                .join(' / ')}
              . Exact returned references are retained.
            </p>
          )}
          <label>
            Review date
            <input
              type="date"
              value={date}
              min={window.start}
              max={window.end}
              required
              onChange={(event) => {
                const next = event.target.value;
                setDate(next);
                if (prepared) {
                  const qualifications = observationQualifications(
                    players.filter((player) => prepared.playerIds.includes(player.id)),
                    local,
                    window.start,
                    next,
                  );
                  const nextReason =
                    !local?.view?.schedule ||
                    prepared.playerIds.some(
                      (id) =>
                        players.find((player) => player.id === id)?.scheduleJoin !== 'matched',
                    )
                      ? 'Schedule coverage unavailable; verify reported affiliation or assignment in Yahoo.'
                      : qualifications.includes(
                            'Shared game date observed; review prompt only, not a slot-capacity conflict.',
                          )
                        ? 'Shared game date observed; review prompt only, not a slot-capacity conflict.'
                        : 'Review observed team games and reported assignments; complete coverage and appearances remain unverified.';
                  if (reason === prepared.reason && Object.values(factualReasons).includes(reason))
                    setReason(nextReason);
                  setPrepared({ ...prepared, date: next, reason: nextReason });
                }
              }}
            />
          </label>
          <label>
            Review action
            <input
              id="manual-plan-action"
              value={action}
              maxLength={240}
              required
              onChange={(event) => setAction(event.target.value)}
            />
          </label>
          <label>
            Reason
            <textarea
              value={reason}
              maxLength={1000}
              required
              onChange={(event) => setReason(event.target.value)}
            />
          </label>
          <button className="button" type="submit">
            {editing ? 'Save review item' : 'Add review item'}
          </button>
          {editing && (
            <Button
              onClick={() => {
                setEditing(null);
                setPrepared(null);
                plan.setDraft(null);
                setAction('');
                setReason('');
                setMessage('Edit cancelled.');
              }}
            >
              Cancel edit
            </Button>
          )}
        </form>
      )}
      <p role="status">{message}</p>
      {prepared && (
        <aside aria-label="Referenced observation qualifications">
          {preparedQualifications.map((note, index) => (
            <p key={index}>{note}</p>
          ))}
        </aside>
      )}
      <p>
        {plan.items.filter((item) => !item.reviewed).length} pending ·{' '}
        {plan.items.filter((item) => item.reviewed).length} reviewed. Source limitations remain
        unresolved by acknowledgement.
      </p>
      <p>{plan.noAction ? 'No action needed acknowledged.' : 'Review pending.'}</p>
      <Button
        onClick={() => {
          plan.setNoAction(!plan.noAction);
          setMessage(
            plan.noAction
              ? 'Review returned to pending.'
              : 'No action needed: human acknowledgement only. Pending items and source limitations remain visible.',
          );
        }}
      >
        {plan.noAction ? 'Return review to pending' : 'Record no action needed'}
      </Button>
      {plan.noAction && (
        <p>
          No action needed is your review outcome; any pending items above still need
          acknowledgement. Coverage and lineup legality remain unverified.
        </p>
      )}
      {plan.items.map((item, index) => (
        <article key={item.id} aria-label={`Review item ${index + 1}`}>
          <h3>
            {item.playerIds
              .map((id) => players.find((player) => player.id === id)?.name)
              .join(' / ')}
          </h3>
          <p>
            {item.playerIds.map((id) => (
              <span key={id}>{id} </span>
            ))}{' '}
            · <span>{item.date}</span> · <strong>{item.reviewed ? 'Reviewed' : 'Pending'}</strong>
          </p>
          <p>{item.action}</p>
          <p>{item.reason}</p>
          <p>
            Original planning window: {item.start} – {item.end} · America/Toronto
          </p>
          {item.qualifications.map((note, index) => (
            <p key={index}>{note}</p>
          ))}
          <div className="manual-plan-actions">
            <Button
              aria-label={`Edit item ${index + 1}`}
              onClick={() => {
                setEditing(item.id);
                setPlayerId(item.playerIds[0]!);
                setPrepared({ ...item });
                setDate(item.date);
                setAction(item.action);
                setReason(item.reason);
                setMessage('');
                document.getElementById('manual-plan-action')?.focus();
              }}
            >
              Edit
            </Button>
            <Button
              aria-label={
                item.reviewed
                  ? `Return item ${index + 1} to pending`
                  : `Mark item ${index + 1} reviewed`
              }
              onClick={() => {
                plan.setItems((items) =>
                  items.map((current) =>
                    current.id === item.id ? { ...current, reviewed: !current.reviewed } : current,
                  ),
                );
                setMessage(
                  item.reviewed
                    ? 'Item returned to pending.'
                    : 'Item reviewed: human acknowledgement only.',
                );
              }}
            >
              {item.reviewed ? 'Return to pending' : 'Mark reviewed'}
            </Button>
            <Button
              aria-label={`Reopen player for item ${index + 1}`}
              onClick={() =>
                onNavigate('profile', item.playerIds[0], {
                  comparisonStart: item.start,
                  reviewDate: item.date,
                })
              }
            >
              Reopen player context
            </Button>
            <Button
              aria-label={`Reopen context for item ${index + 1}`}
              onClick={() =>
                onNavigate(item.context, item.playerIds[0], {
                  comparisonStart: item.start,
                  comparisonRightId: item.playerIds[1],
                  reviewDate: item.date,
                })
              }
            >
              Reopen {item.context === 'comparison' ? 'comparison' : 'review'} context
            </Button>
            <Button
              aria-label={`Remove item ${index + 1}`}
              onClick={() => {
                plan.setItems((items) => items.filter((current) => current.id !== item.id));
                if (editing === item.id) {
                  setEditing(null);
                  setPrepared(null);
                  setAction('');
                  setReason('');
                }
                setMessage('Review item removed.');
              }}
            >
              Remove
            </Button>
          </div>
        </article>
      ))}
    </section>
  );
}
