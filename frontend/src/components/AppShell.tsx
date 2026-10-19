import {
  Bell,
  CalendarDays,
  ChartNoAxesColumnIncreasing,
  ChevronDown,
  Crown,
  House,
  Link,
  Menu,
  Search,
  Settings,
  Shield,
  Trophy,
  Users,
  X,
} from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { Button } from './primitives';
import type { Screen, DisplayPreferences } from '../application';

const navigation = [
  ['Overview', House, 'overview'],
  ['Schedule Planner', CalendarDays, 'planner'],
  ['My Roster', Users, 'roster'],
  ['Compare Players', ChartNoAxesColumnIncreasing, 'comparison'],
  ['League', Trophy, 'league'],
  ['Connections', Link, 'connections'],
  ['Settings', Settings, 'settings'],
] as const;

export function AppShell({
  children,
  search,
  onSearch,
  onNotice,
  current = 'overview',
  onNavigate,
  display,
}: {
  current?: Screen;
  display?: DisplayPreferences;
  onNavigate?: (screen: Screen) => void;
  children: ReactNode;
  search: string;
  onSearch: (query: string) => void;
  onNotice: (message: string) => void;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const sidebar = useRef<HTMLElement>(null);
  const opener = useRef<HTMLButtonElement>(null);
  const closeButton = useRef<HTMLButtonElement>(null);
  function closeMenu() {
    setMenuOpen(false);
    opener.current?.focus();
  }
  useEffect(() => {
    if (!menuOpen) return;
    closeButton.current?.focus();
    function handleKey(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        event.preventDefault();
        closeMenu();
      } else if (event.key === 'Tab') {
        const controls = sidebar.current?.querySelectorAll<HTMLElement>('a[href], button');
        const first = controls?.[0];
        const last = controls?.[controls.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last?.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first?.focus();
        }
      }
    }
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [menuOpen]);
  return (
    <div
      className={`app-shell ${display?.logos === false ? 'without-team-logos' : ''} ${display?.compact ? 'compact-display' : ''} ${display?.contrast ? 'high-contrast-display' : ''}`}
    >
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <aside
        ref={sidebar}
        className={`sidebar ${menuOpen ? 'is-open' : ''}`}
        aria-label="Main navigation"
      >
        <a href="#overview" className="wordmark" aria-label="Fantasy GM Hockey Overview">
          <Crown aria-hidden="true" />
          <span>
            FANTASY<span>GM</span>
          </span>
          <small>HOCKEY</small>
        </a>
        <button
          className="mobile-close icon-button"
          aria-label="Close navigation"
          ref={closeButton}
          onClick={closeMenu}
        >
          <X />
        </button>
        <nav aria-label="Screens">
          {navigation.map(([name, Icon, route], index) => (
            <button
              key={name}
              aria-label={`${String(index + 1).padStart(2, '0')} ${name}`}
              className={`nav-item ${current === route || (current === 'profile' && route === 'roster') ? 'selected' : ''}`}
              aria-current={current === route ? 'page' : undefined}

              onClick={() => {
                onNavigate?.(route);
                closeMenu();
              }}
            >
              <Icon aria-hidden="true" />
              <small>{String(index + 1).padStart(2, '0')}</small>
              <span>{name}</span>
            </button>
          ))}
        </nav>
        <div className="sidebar-motto">
          GOOD
          <br />
          MANAGERS
          <br />
          MAKE GREAT
          <br />
          SEASONS
          <span />
        </div>
      </aside>
      {menuOpen && (
        <button
          className="nav-backdrop"
          aria-label="Close navigation overlay"
          onClick={closeMenu}
        />
      )}
      <div className="workspace">
        <header className="top-bar">
          <button
            className="mobile-menu icon-button"
            aria-label="Open navigation"
            aria-expanded={menuOpen}
            ref={opener}
            onClick={() => setMenuOpen(true)}
          >
            <Menu />
          </button>
          <div className="league-context">
            <Shield className="league-shield" aria-hidden="true" />
            <div>
              <span className="league-name">
                Riverside Hockey League <ChevronDown size={13} />
              </span>
              <small>
                12 Teams <span>·</span> H2H Points <span>·</span>{' '}
                <b className="source-label">DEMO · SYNTHETIC DATA</b>
              </small>
            </div>
          </div>
          <label className="search">
            <Search size={18} aria-hidden="true" />
            <span className="sr-only">Search roster players or teams</span>
            <input
              type="search"
              placeholder="Search roster players or teams…"
              value={search}
              onChange={(event) => onSearch(event.target.value)}
            />
          </label>
          <Button
            className="notification-button icon-button"
            aria-label="Notifications unavailable in this prototype"
            onClick={() =>
              onNotice('Notifications are unavailable. No live services are connected.')
            }
          >
            <Bell />
            <span className="notification-dot" />
          </Button>
          <Button
            className="account-button"
            aria-label="Demo account information"
            onClick={() => onNotice('Synthetic demo session. No Yahoo account is connected.')}
          >
            JD
          </Button>
        </header>
        <main id="main-content" tabIndex={-1}>
          {children}
        </main>
      </div>
    </div>
  );
}
