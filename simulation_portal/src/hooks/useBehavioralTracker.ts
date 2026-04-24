import { useCallback, useEffect, useRef } from 'react';
import { buildApiUrl } from '../lib/portalApi';

interface UseBehavioralTrackerOptions {
  userId: string;
  sessionId?: string;
  page?: string;
}

export interface BehavioralEvent {
  type: string;
  timestamp: number;
  x?: number;
  y?: number;
  key?: string;
  target?: string;
  scrollX?: number;
  scrollY?: number;
}

export function useBehavioralTracker({ userId, sessionId, page }: UseBehavioralTrackerOptions) {
  const eventBuffer = useRef<BehavioralEvent[]>([]);
  const sessionIdRef = useRef(sessionId || `portal-${Math.random().toString(36).substring(2)}`);
  const userIdRef = useRef(userId);
  const pageRef = useRef(page);
  const isTracking = useRef(false);

  useEffect(() => {
    userIdRef.current = userId || 'anonymous';
  }, [userId]);

  useEffect(() => {
    if (sessionId) {
      sessionIdRef.current = sessionId;
    }
  }, [sessionId]);

  useEffect(() => {
    pageRef.current = page;
  }, [page]);

  const flushEvents = useCallback(async () => {
    if (eventBuffer.current.length === 0) return;

    const eventsToFlush = [...eventBuffer.current];
    eventBuffer.current = [];

    try {
      await fetch(buildApiUrl('/api/behavioral'), {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userIdRef.current,
          session_id: sessionIdRef.current,
          events: eventsToFlush,
          page: pageRef.current,
        }),
      });
    } catch (error) {
      console.error('Failed to flush behavioral events:', error);
      // Put events back if failed? Or just drop for simplicity in simulation
      eventBuffer.current = [...eventsToFlush, ...eventBuffer.current];
    }
  }, []);

  const addEvent = useCallback((event: BehavioralEvent) => {
    if (!isTracking.current) return;
    eventBuffer.current.push(event);
  }, []);

  const startTracking = useCallback(() => {
    isTracking.current = true;
    if (pageRef.current) {
      eventBuffer.current.push({
        type: 'pagevisit',
        timestamp: Date.now(),
        target: pageRef.current,
      });
    }
  }, []);

  const stopTracking = useCallback(() => {
    isTracking.current = false;
    void flushEvents();
  }, [flushEvents]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const isPassword = (e.target as HTMLInputElement)?.type === 'password';
      addEvent({
        type: 'keydown',
        timestamp: Date.now(),
        key: isPassword ? '[REDACTED]' : e.key,
        target: (e.target as HTMLElement).tagName
      });
    };

    const handleKeyUp = (e: KeyboardEvent) => {
      const isPassword = (e.target as HTMLInputElement)?.type === 'password';
      addEvent({
        type: 'keyup',
        timestamp: Date.now(),
        key: isPassword ? '[REDACTED]' : e.key,
        target: (e.target as HTMLElement).tagName
      });
    };

    let lastMouseMove = 0;
    const handleMouseMove = (e: MouseEvent) => {
      const now = Date.now();
      if (now - lastMouseMove > 100) { // Throttled 100ms
        addEvent({
          type: 'mousemove',
          timestamp: now,
          x: e.clientX,
          y: e.clientY
        });
        lastMouseMove = now;
      }
    };

    const handleClick = (e: MouseEvent) => {
      addEvent({
        type: 'click',
        timestamp: Date.now(),
        x: e.clientX,
        y: e.clientY,
        target: (e.target as HTMLElement).tagName
      });
    };

    const handleScroll = () => {
      addEvent({
        type: 'scroll',
        timestamp: Date.now(),
        scrollX: window.scrollX,
        scrollY: window.scrollY
      });
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('click', handleClick);
    window.addEventListener('scroll', handleScroll);

    const interval = setInterval(flushEvents, 10000); // Flush every 10s

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('click', handleClick);
      window.removeEventListener('scroll', handleScroll);
      clearInterval(interval);
      flushEvents();
    };
  }, [addEvent, flushEvents]);

  return {
    sessionId: sessionIdRef.current,
    eventCount: eventBuffer.current.length,
    flushEvents,
    startTracking,
    stopTracking
  };
}
