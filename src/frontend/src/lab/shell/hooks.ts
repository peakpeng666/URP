import { useEffect, useRef } from 'react';
import { events } from '../api';

/** Reload (debounced) whenever one of the SSE event types arrives. */
export function useEventReload(types: string[], reload: () => void, delayMs = 350) {
  const reloadRef = useRef(reload);
  reloadRef.current = reload;
  const key = types.join(',');
  useEffect(() => {
    const wanted = new Set(key.split(','));
    let timer: number | undefined;
    const off = events.subscribe((type) => {
      if (!wanted.has(type)) return;
      window.clearTimeout(timer);
      timer = window.setTimeout(() => reloadRef.current(), delayMs);
    });
    return () => {
      off();
      window.clearTimeout(timer);
    };
  }, [key, delayMs]);
}

/** Runs `reload` once when the gateway event stream reconnects. */
export function useReconnectReload(connected: boolean, reload: () => void) {
  const reloadRef = useRef(reload);
  reloadRef.current = reload;
  const was = useRef(connected);
  useEffect(() => {
    if (connected && !was.current) reloadRef.current();
    was.current = connected;
  }, [connected]);
}

/** Poll interval used while the event stream is down (SSE is the primary channel). */
export const fallbackPoll = (connected: boolean, ms = 5000) => (connected ? undefined : ms);
