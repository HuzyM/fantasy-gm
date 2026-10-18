import { useEffect, useState } from 'react';
import type { Screen } from './application';
import { AppShell } from './components/AppShell';
import Overview from './screens/Overview';
import MyRoster from './screens/MyRoster';
import PlayerProfile from './screens/PlayerProfile';
import SchedulePlanner from './screens/SchedulePlanner';
import PlayerComparison from './screens/PlayerComparison';
import { overviewFixture } from './fixtures/overview';
import './application.css';

function readRoute(): { screen: Screen; playerId?: string } {
  const [screen = '', playerId] = window.location.hash.slice(1).split('/');
  return {
    screen: ['roster', 'profile', 'planner', 'comparison'].includes(screen)
      ? (screen as Screen)
      : 'overview',
    playerId,
  };
}
export default function App() {
  const [route, setRoute] = useState(readRoute);
  const [search, setSearch] = useState('');
  const [notice, setNotice] = useState('');
  useEffect(() => {
    const update = () => {
      setRoute(readRoute());
      setSearch('');
    };
    window.addEventListener('hashchange', update);
    return () => window.removeEventListener('hashchange', update);
  }, []);
  function navigate(screen: Screen, playerId?: string) {
    if (!['overview', 'roster', 'profile', 'planner', 'comparison'].includes(screen)) {
      setNotice('Player Comparison is planned for a later milestone.');
      return;
    }
    window.history.pushState(
      null,
      '',
      `#${screen}${playerId ? `/${encodeURIComponent(playerId)}` : ''}`,
    );
    setRoute({ screen, playerId });
    setSearch('');
    setNotice('');
    requestAnimationFrame(() => document.getElementById('main-content')?.focus());
  }
  const props = {
    search,
    players: overviewFixture.players,
    onNavigate: navigate,
    onNotice: setNotice,
  };
  return (
    <AppShell
      current={route.screen}
      search={search}
      onSearch={setSearch}
      onNotice={setNotice}
      onNavigate={navigate}
    >
      {route.screen === 'overview' && <Overview {...props} />}
      {route.screen === 'roster' && <MyRoster {...props} />}
      {route.screen === 'profile' && <PlayerProfile {...props} selectedId={route.playerId} />}
      {route.screen === 'planner' && <SchedulePlanner {...props} />}
      {route.screen === 'comparison' && <PlayerComparison {...props} selectedId={route.playerId} />}
      {notice && (
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
