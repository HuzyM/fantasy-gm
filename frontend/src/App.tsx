import { useEffect, useRef, useState } from 'react';
import type { Screen, ScreenProps, DisplayPreferences } from './application';
import { AppShell } from './components/AppShell';
import Overview from './screens/Overview';
import MyRoster from './screens/MyRoster';
import PlayerProfile from './screens/PlayerProfile';
import SchedulePlanner from './screens/SchedulePlanner';
import PlayerComparison from './screens/PlayerComparison';
import League from './screens/League';
import Connections from './screens/Connections';
import Settings from './screens/Settings';
import { overviewFixture } from './fixtures/overview';
import './application.css';
import { useLocalSession } from './useLocalSession';
import { isObservation, providerPlayers } from './api';
import { ManualPlanProvider } from './components/ManualPlan';

type Route = {
  screen: Screen;
  playerId?: string;
  comparisonStart?: string;
  sourceGeneration?: number;
};

function readRoute(): Route {
  const [screen = '', playerId] = window.location.hash.slice(1).split('/');
  return {
    screen: [
      'roster',
      'profile',
      'planner',
      'comparison',
      'league',
      'connections',
      'settings',
    ].includes(screen)
      ? (screen as Screen)
      : 'overview',
    playerId,
  };
}
export default function App() {
  const local = useLocalSession();
  // History contains opaque keys only; private identities stay in this mounted session.
  const privateRoutes = useRef(new Map<string, Route>());
  const source = JSON.stringify([local.state, local.view]);
  const sourceContext = useRef({ source, generation: 0 });
  if (sourceContext.current.source !== source) {
    sourceContext.current = { source, generation: sourceContext.current.generation + 1 };
    privateRoutes.current.clear();
  }
  const [route, setRoute] = useState(readRoute);
  const [search, setSearch] = useState('');
  const [notice, setNotice] = useState('');
  const [display, setDisplay] = useState<DisplayPreferences>({
    logos: true,
    compact: false,
    contrast: false,
  });
  useEffect(() => {
    const update = () => {
      const next = readRoute();
      const saved = privateRoutes.current.get(window.history.state?.privateRouteKey);
      setRoute(saved?.screen === next.screen ? saved : next);
      setSearch('');
    };
    window.addEventListener('hashchange', update);
    window.addEventListener('popstate', update);
    return () => {
      window.removeEventListener('hashchange', update);
      window.removeEventListener('popstate', update);
    };
  }, []);
  const navigate: ScreenProps['onNavigate'] = (screen, playerId, context) => {
    if (
      ![
        'overview',
        'roster',
        'profile',
        'planner',
        'comparison',
        'league',
        'connections',
        'settings',
      ].includes(screen)
    ) {
      setNotice('This screen is unavailable.');
      return;
    }
    const next: Route = {
      screen,
      playerId,
      comparisonStart: context?.comparisonStart,
      sourceGeneration: sourceContext.current.generation,
    };
    const privateRouteKey =
      (local.state === 'private' && playerId) || context ? crypto.randomUUID() : null;
    if (privateRouteKey) privateRoutes.current.set(privateRouteKey, next);
    window.history.pushState(
      privateRouteKey ? { privateRouteKey } : null,
      '',
      `#${screen}${playerId && local.state !== 'private' ? `/${encodeURIComponent(playerId)}` : ''}`,
    );
    setRoute(next);
    setSearch('');
    setNotice('');
    requestAnimationFrame(() => document.getElementById('main-content')?.focus());
  };
  useEffect(() => {
    if (local.state === 'locked' || local.state === 'loading') privateRoutes.current.clear();
    if (local.state === 'locked') {
      setSearch('');
      setNotice('');
      setRoute({ screen: 'overview' });
      // A fresh launcher fragment must reach the session handler before route cleanup.
      if (!window.location.hash.startsWith('#access='))
        window.history.replaceState(null, '', '#overview');
    }
  }, [local.state]);
  useEffect(() => {
    setSearch('');
    setNotice('');
  }, [source]);
  const props = {
    search,
    players: isObservation(local.view) ? providerPlayers(local.view!) : overviewFixture.players,
    local,
    onNavigate: navigate,
    onNotice: setNotice,
  };
  return (
    <AppShell
      current={route.screen}
      search={local.state === 'locked' || local.state === 'loading' ? '' : search}
      onSearch={setSearch}
      onNotice={setNotice}
      onNavigate={navigate}
      display={display}
      contextName={
        isObservation(local.view)
          ? (local.view?.league?.name ?? 'Public NHL schedule')
          : local.state === 'locked' || local.state === 'loading'
            ? local.private
              ? 'Private local session'
              : 'Local observations'
            : undefined
      }
      contextLabel={
        isObservation(local.view)
          ? 'LOCAL OBSERVATION · READ-ONLY · COVERAGE UNVERIFIED'
          : local.state === 'locked' || local.state === 'loading'
            ? local.private
              ? 'PRIVATE SESSION · NO DATA DISPLAYED'
              : 'LOCAL OBSERVATION UNAVAILABLE'
            : undefined
      }
    >
      {local.state === 'locked' || local.state === 'loading' ? (
        <section className="panel session-locked">
          <h1>
            {local.state === 'loading'
              ? 'Loading local session'
              : local.private
                ? 'Private session unavailable'
                : 'Local observation unavailable'}
          </h1>
          <p>
            {local.private
              ? 'Private display data has been cleared. Start or reopen the human-operated local launcher link. No synthetic data is substituted.'
              : 'The local observation is unavailable. It will reload from the local server when the service recovers; no provider refresh is requested.'}
          </p>
        </section>
      ) : (
        <ManualPlanProvider key={sourceContext.current.generation}>
          <div
            key={`${sourceContext.current.generation}-${route.screen}-${route.playerId ?? ''}-${route.comparisonStart ?? ''}`}
            className="screen-content"
            data-source={local.state}
          >
            {route.screen === 'overview' && <Overview {...props} />}
            {route.screen === 'roster' && <MyRoster {...props} />}
            {route.screen === 'profile' && (
              <PlayerProfile
                {...props}
                selectedId={
                  route.sourceGeneration === undefined ||
                  route.sourceGeneration === sourceContext.current.generation
                    ? route.playerId
                    : undefined
                }
              />
            )}
            {route.screen === 'planner' && <SchedulePlanner {...props} />}
            {route.screen === 'comparison' && (
              <PlayerComparison
                {...props}
                comparisonStart={
                  route.sourceGeneration === sourceContext.current.generation
                    ? route.comparisonStart
                    : undefined
                }
                selectedId={
                  route.sourceGeneration === undefined ||
                  route.sourceGeneration === sourceContext.current.generation
                    ? route.playerId
                    : undefined
                }
              />
            )}
            {route.screen === 'league' && <League {...props} />}
            {route.screen === 'connections' && <Connections {...props} />}
            {route.screen === 'settings' && (
              <Settings {...props} display={display} onDisplayChange={setDisplay} />
            )}
          </div>
        </ManualPlanProvider>
      )}
      {notice && local.state !== 'locked' && local.state !== 'loading' && (
        <div className="notice visible" role="status">
          {notice}
          <button className="button" onClick={() => setNotice('')}>
            Dismiss
          </button>
        </div>
      )}
    </AppShell>
  );
}
