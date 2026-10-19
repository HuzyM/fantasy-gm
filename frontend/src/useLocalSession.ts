import { useEffect, useRef, useState } from 'react';
import { parseView } from './api';
import type { LocalView } from './api';

export interface LocalSession {
  private?: boolean;
  view: LocalView | null;
  state: 'offline' | 'loading' | 'demo' | 'private' | 'public' | 'locked';
  disconnect: () => Promise<void>;
}
/** Capability and observations live in this mounted page only. Never expose them through storage. */
export function useLocalSession(): LocalSession {
  const capability = useRef<string | null>(null);
  const privateMode = useRef(false);
  const observedMode = useRef(false);
  const [initialPrivate] = useState(() => {
    if (!window.location.hash.startsWith('#access=')) return false;
    const candidate = window.location.hash.slice(8);
    capability.current = /^[A-Za-z0-9_-]{32,128}$/.test(candidate) ? candidate : null;
    privateMode.current = true;
    window.history.replaceState(null, '', `${window.location.pathname}#overview`);
    return true;
  });
  const [view, setView] = useState<LocalView | null>(null);
  const [state, setState] = useState<LocalSession['state']>(initialPrivate ? 'loading' : 'offline');
  function clear() {
    capability.current = null;
    setView(null);
    setState('locked');
  }
  useEffect(() => {
    const controller = new AbortController();
    const options = {
      cache: 'no-store' as const,
      credentials: 'omit' as const,
      mode: 'same-origin' as const,
      referrerPolicy: 'no-referrer' as const,
      signal: controller.signal,
    };
    let generation = 0;
    async function load() {
      const requestedGeneration = ++generation;
      try {
        const response = await fetch('/api/status', options);
        if (!response.ok) throw new Error();
        const status: unknown = await response.json();
        if (controller.signal.aborted || requestedGeneration !== generation) return;
        if (
          !status ||
          typeof status !== 'object' ||
          !('mode' in status) ||
          !['private', 'synthetic'].includes(String(status.mode))
        )
          throw new Error();
        const isPrivate = status.mode === 'private';
        if (isPrivate) privateMode.current = true;
        if (
          privateMode.current &&
          (!isPrivate || !('yahoo' in status) || status.yahoo !== 'loaded' || !capability.current)
        ) {
          if (!controller.signal.aborted) clear();
          return;
        }
        // Re-read local memory so a restarted server cannot leave a stale display.
        // This also authenticates private capabilities; no provider is invoked.
        const requestCapability = capability.current;
        const data = await fetch('/api/view', {
          ...options,
          headers: capability.current ? { Authorization: `Bearer ${capability.current}` } : {},
        });
        if (!data.ok) throw new Error();
        const parsed = parseView(await data.json());
        if (isPrivate !== (parsed.mode === 'private')) throw new Error();
        if (controller.signal.aborted || requestedGeneration !== generation) return;
        if (privateMode.current && (!requestCapability || requestCapability !== capability.current))
          return;
        observedMode.current = parsed.source !== 'synthetic';
        setView(parsed);
        setState(isPrivate ? 'private' : parsed.source === 'puckapi' ? 'public' : 'demo');
      } catch {
        if (controller.signal.aborted || requestedGeneration !== generation) return;
        if (privateMode.current || observedMode.current) clear();
        else {
          setView(null);
          setState('offline');
        }
      }
    }
    void load();
    const timer = window.setInterval(() => void load(), 15000);
    const expire = window.setTimeout(
      () => {
        if (privateMode.current) clear();
      },
      20 * 60 * 1000,
    );
    const focus = () => void load();
    const pagehide = () => {
      if (privateMode.current) clear();
    };
    window.addEventListener('focus', focus);
    window.addEventListener('pagehide', pagehide);
    return () => {
      controller.abort();
      window.clearInterval(timer);
      window.clearTimeout(expire);
      window.removeEventListener('focus', focus);
      window.removeEventListener('pagehide', pagehide);
    };
  }, []);
  async function disconnect() {
    const access = capability.current;
    clear();
    if (!access) return;
    try {
      await fetch('/api/disconnect', {
        method: 'POST',
        headers: { Authorization: `Bearer ${access}` },
        credentials: 'omit',
        mode: 'same-origin',
        cache: 'no-store',
        referrerPolicy: 'no-referrer',
      });
    } catch {
      /* Local display stays cleared; server expiry remains bounded. */
    }
  }
  return { view, state, disconnect, private: privateMode.current };
}
