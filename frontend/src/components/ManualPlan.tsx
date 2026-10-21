import { createContext, useContext, useState } from 'react';
import type { ReactNode, Dispatch, SetStateAction, FormEvent } from 'react';
import type { ScreenProps } from '../application';
import { Button } from './primitives';
import '../manual-plan.css';

interface ReviewItem {
  id: string;
  playerId: string;
  date: string;
  action: string;
  reason: string;
  reviewed: boolean;
}
const PlanContext = createContext<{
  items: ReviewItem[];
  setItems: Dispatch<SetStateAction<ReviewItem[]>>;
  noAction: boolean;
  setNoAction: Dispatch<SetStateAction<boolean>>;
} | null>(null);

/** Mounted above route screens, discarded with the current observation source. */
export function ManualPlanProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [noAction, setNoAction] = useState(false);
  return <PlanContext value={{ items, setItems, noAction, setNoAction }}>{children}</PlanContext>;
}

export function ManualPlan({
  players,
  local,
  onNavigate,
}: Pick<ScreenProps, 'players' | 'local' | 'onNavigate'>) {
  const plan = useContext(PlanContext);
  const window = local?.view?.planningWindow;
  const [playerId, setPlayerId] = useState('');
  const [date, setDate] = useState(window?.start ?? '');
  const [action, setAction] = useState('');
  const [reason, setReason] = useState('');
  const [message, setMessage] = useState('');
  const [editing, setEditing] = useState<string | null>(null);
  if (!plan || !window) return null;
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
                reviewed: false,
              }
            : item,
        ),
      );
    } else {
      plan!.setItems((items) => [
        ...items,
        {
          id: crypto.randomUUID(),
          playerId,
          date,
          action: action.trim(),
          reason: reason.trim(),
          reviewed: false,
        },
      ]);
    }
    plan!.setNoAction(false);
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
      {!local?.view?.roster ? (
        <p>An owned Yahoo roster is required for a manual plan.</p>
      ) : (
        <>
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
                  disabled={!!editing}
                >
                  <option value="">Choose a returned player</option>
                  {players.map((player) => (
                    <option key={player.id} value={player.id}>
                      {player.name} · {player.id}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Review date
                <input
                  type="date"
                  value={date}
                  min={window.start}
                  max={window.end}
                  required
                  onChange={(event) => setDate(event.target.value)}
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
              <h3>{players.find((player) => player.id === item.playerId)?.name}</h3>
              <p>
                <span>{item.playerId}</span> · <span>{item.date}</span> ·{' '}
                <strong>{item.reviewed ? 'Reviewed' : 'Pending'}</strong>
              </p>
              <p>{item.action}</p>
              <p>{item.reason}</p>
              <p>
                {!local?.view?.schedule ||
                players.find((player) => player.id === item.playerId)?.scheduleJoin === 'unverified'
                  ? 'Schedule coverage unavailable; reported affiliation may be unavailable or stale. No game is asserted by this review item.'
                  : 'Observed team games only; coverage and player appearances remain unverified.'}
              </p>
              <div className="manual-plan-actions">
                <Button
                  aria-label={`Edit item ${index + 1}`}
                  onClick={() => {
                    setEditing(item.id);
                    setPlayerId(item.playerId);
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
                        current.id === item.id
                          ? { ...current, reviewed: !current.reviewed }
                          : current,
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
                  onClick={() => onNavigate('profile', item.playerId)}
                >
                  Reopen player context
                </Button>
                <Button
                  aria-label={`Remove item ${index + 1}`}
                  onClick={() => {
                    plan.setItems((items) => items.filter((current) => current.id !== item.id));
                    if (editing === item.id) {
                      setEditing(null);
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
        </>
      )}
    </section>
  );
}
