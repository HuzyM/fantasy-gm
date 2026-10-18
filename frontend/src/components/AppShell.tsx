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

const navigation = [
  ['Overview', House],
  ['Schedule Planner', CalendarDays],
  ['My Roster', Users],
  ['Compare Players', ChartNoAxesColumnIncreasing],
  ['League', Trophy],
  ['Connections', Link],
  ['Settings', Settings],
] as const;

export function AppShell({
  children,
  search,
  onSearch,
  onNotice,
}: {
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
    <div className="app-shell">
      <a className="skip-link" href="#overview">
        Skip to Overview
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
          {navigation.map(([name, Icon], index) => (
            <button
              key={name}
              className={`nav-item ${index === 0 ? 'selected' : ''}`}
              aria-current={index === 0 ? 'page' : undefined}
              aria-disabled={index !== 0}
              title={index ? `${name} is outside the Overview milestone` : undefined}
              onClick={() => {
                if (index) onNotice(`${name} is planned for a later milestone.`);
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
        <main id="overview" tabIndex={-1}>
          {children}
        </main>
      </div>
    </div>
  );
}
