import type { ScreenProps } from '../application';
import { Button, Panel } from './primitives';
export function ObservationLeague({ local, onNavigate }: ScreenProps) {
  const view = local?.view;
  return (
    <div className="league-screen">
      <header className="screen-heading">
        <div>
          <h1>{view?.league?.name ?? 'League unavailable'}</h1>
          <p>Local read-only provider observation · completeness unverified</p>
        </div>
      </header>
      <div className="observation-grid">
        <Panel>
          <h2>Reported League</h2>
          <dl>
            <div>
              <dt>Season</dt>
              <dd>{view?.league?.season ?? 'Unknown'}</dd>
            </div>
            <div>
              <dt>Selected owned team</dt>
              <dd>{view?.roster?.teamName ?? 'Not loaded'}</dd>
            </div>
            <div>
              <dt>Returned roster count</dt>
              <dd>{view?.roster?.returnedCount ?? 'Unknown'} · total unknown</dd>
            </div>
          </dl>
          <Button onClick={() => onNavigate('roster')}>View reported roster</Button>
        </Panel>
        <Panel>
          <h2>Standings &amp; Matchups</h2>
          <p>
            Unavailable. The existing read-only Yahoo client does not fetch standings, league
            scores, playoffs or activity. No sample scores are substituted.
          </p>
        </Panel>
        <Panel>
          <h2>League Settings</h2>
          <p>
            Unavailable in this browser session. The existing human-only league CLI can inspect
            supported settings; this bounded browser load fetches only league and roster identity.
          </p>
          <Button onClick={() => onNavigate('connections')}>Connection details</Button>
        </Panel>
      </div>
    </div>
  );
}
export function ObservationConnections({ local, onNavigate }: ScreenProps) {
  const view = local?.view;
  const privateData = view?.mode === 'private';
  return (
    <div className="connections-screen">
      <header className="connections-heading">
        <div>
          <h1>Connections</h1>
          <p>Local process observations · read-only · no background provider refresh</p>
        </div>
      </header>
      <div className="connections-grid">
        <div className="connections-main">
          <Panel className="observation-panel">
            <h2>
              {privateData ? 'Yahoo roster loaded locally' : 'Public NHL schedule observation'}
            </h2>
            <p>
              {privateData
                ? 'Selected display fields were loaded by the human-operated launcher. Tokens were discarded before serving. This is not an ongoing health check.'
                : 'No Yahoo account is connected. Public team observations were loaded by the human-operated launcher.'}
            </p>
            <dl>
              <div>
                <dt>League</dt>
                <dd>{view?.league?.name ?? 'Unavailable'}</dd>
              </div>
              <div>
                <dt>Team</dt>
                <dd>{view?.roster?.teamName ?? 'Unavailable'}</dd>
              </div>
              <div>
                <dt>Connection health</dt>
                <dd>Not verified</dd>
              </div>
              <div>
                <dt>Schedule observation</dt>
                <dd>{view?.schedule?.observedAt ?? 'Unavailable'}</dd>
              </div>
            </dl>
          </Panel>
          <Panel className="observation-panel">
            <h2>Coverage &amp; Access</h2>
            {view?.provenance.map((line, i) => (
              <p key={i}>{line}</p>
            ))}
            <p>
              {privateData
                ? 'Read-only Yahoo GETs only.'
                : 'Read-only public PuckAPI schedule requests only; no Yahoo requests.'}{' '}
              No transactions, lineup writes, browser credential input, cookies, saved private data
              or automated refresh.
            </p>
            <p>
              Player IDs from Yahoo are not NHL IDs. Photos require a verified crosswalk; no
              approximate name matches are used.
            </p>
            {view?.schedule && (
              <p>
                Schedule issues:{' '}
                {view.schedule.issues.join(' · ') ||
                  'No issue codes supplied; completeness follows the count flags.'}
              </p>
            )}
          </Panel>
        </div>
        <aside className="connections-side">
          <Panel className="observation-panel">
            <h2>Session Tools</h2>
            {privateData && (
              <Button onClick={() => void local?.disconnect()}>Disconnect local session</Button>
            )}
            <Button onClick={() => onNavigate('roster')}>View roster</Button>
            <Button onClick={() => onNavigate('planner')}>View team schedule</Button>
            <p>
              Reloading loses the browser access key. Expiry, disconnect or an unavailable private
              server clears the display. Restart or reopen the private launcher link to reconnect.
            </p>
            <p>
              Refresh requires a new explicit human-operated launcher session; browser reads spend
              no provider calls.
            </p>
          </Panel>
        </aside>
      </div>
    </div>
  );
}
