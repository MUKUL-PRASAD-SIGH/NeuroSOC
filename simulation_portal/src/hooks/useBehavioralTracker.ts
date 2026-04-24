import { useEffect, useRef, useCallback } from 'react';

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

export function useBehavioralTracker(userId: string) {
  const eventBuffer = useRef<BehavioralEvent[]>([]);
  const sessionId = useRef(Math.random().toString(36).substring(7));
  const isTracking = useRef(false);

  const flushEvents = useCallback(async () => {
    if (eventBuffer.current.length === 0) return;

    const eventsToFlush = [...eventBuffer.current];
    eventBuffer.current = [];

    try {
      await fetch('/api/behavioral', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          session_id: sessionId.current,
          events: eventsToFlush,
        }),
      });
    } catch (error) {
      console.error('Failed to flush behavioral events:', error);
      // Put events back if failed? Or just drop for simplicity in simulation
      eventBuffer.current = [...eventsToFlush, ...eventBuffer.current];
    }
  }, [userId]);

  const addEvent = useCallback((event: BehavioralEvent) => {
    if (!isTracking.current) return;
    eventBuffer.current.push(event);
  }, []);

  const startTracking = useCallback(() => {
    isTracking.current = true;
  }, []);

  const stopTracking = useCallback(() => {
    isTracking.current = false;
    flushEvents();
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
    sessionId: sessionId.current,
    eventCount: eventBuffer.current.length,
    startTracking,
    stopTracking
  };
}
