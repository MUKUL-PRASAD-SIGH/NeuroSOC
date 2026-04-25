import { useRef, useEffect, useCallback } from 'react';
import { postBehavioral } from '../../lib/portalApi';

interface BehavioralEvent {
  type: 'keydown' | 'keyup' | 'mousemove' | 'click' | 'scroll';
  timestamp: number;
  key?: string;
  x?: number;
  y?: number;
  target?: string;
}

interface BehavioralData {
  user_id: string;
  session_id: string;
  events: BehavioralEvent[];
}

export function useBehavioralTracker(userId: string = 'anonymous') {
  const sessionId = useRef(`session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`);
  const eventBuffer = useRef<BehavioralEvent[]>([]);
  const lastMouseMove = useRef<number>(0);
  const flushInterval = useRef<ReturnType<typeof setInterval> | null>(null);
  const isTracking = useRef(false);

  const flushEvents = useCallback(async () => {
    if (eventBuffer.current.length === 0) return;

    const data: BehavioralData = {
      user_id: userId,
      session_id: sessionId.current,
      events: [...eventBuffer.current]
    };

    try {
      await postBehavioral({
        userId: data.user_id,
        sessionId: data.session_id,
        events: data.events,
      });
      eventBuffer.current = [];
    } catch (error) {
      console.error('Failed to send behavioral data:', error);
    }
  }, [userId]);

  const addEvent = useCallback((event: BehavioralEvent) => {
    eventBuffer.current.push(event);
  }, []);

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    const target = e.target as HTMLElement;
    const isPasswordField = target instanceof HTMLInputElement && target.type === 'password';

    addEvent({
      type: 'keydown',
      timestamp: Date.now(),
      key: isPasswordField ? '[REDACTED]' : e.key,
      target: target.tagName.toLowerCase()
    });
  }, [addEvent]);

  const handleKeyUp = useCallback((e: KeyboardEvent) => {
    const target = e.target as HTMLElement;
    const isPasswordField = target instanceof HTMLInputElement && target.type === 'password';

    addEvent({
      type: 'keyup',
      timestamp: Date.now(),
      key: isPasswordField ? '[REDACTED]' : e.key,
      target: target.tagName.toLowerCase()
    });
  }, [addEvent]);

  const handleMouseMove = useCallback((e: MouseEvent) => {
    const now = Date.now();
    if (now - lastMouseMove.current < 100) return; // Throttle to 100ms
    lastMouseMove.current = now;

    addEvent({
      type: 'mousemove',
      timestamp: now,
      x: e.clientX,
      y: e.clientY
    });
  }, [addEvent]);

  const handleClick = useCallback((e: MouseEvent) => {
    const target = e.target as HTMLElement;
    addEvent({
      type: 'click',
      timestamp: Date.now(),
      x: e.clientX,
      y: e.clientY,
      target: target.tagName.toLowerCase()
    });
  }, [addEvent]);

  const handleScroll = useCallback(() => {
    addEvent({
      type: 'scroll',
      timestamp: Date.now(),
      y: window.scrollY
    });
  }, [addEvent]);

  const startTracking = useCallback(() => {
    if (isTracking.current) return;

    isTracking.current = true;
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('click', handleClick);
    window.addEventListener('scroll', handleScroll);

    // Flush events every 10 seconds
    flushInterval.current = setInterval(flushEvents, 10000);
  }, [handleKeyDown, handleKeyUp, handleMouseMove, handleClick, handleScroll, flushEvents]);

  const stopTracking = useCallback(() => {
    if (!isTracking.current) return;

    isTracking.current = false;
    window.removeEventListener('keydown', handleKeyDown);
    window.removeEventListener('keyup', handleKeyUp);
    window.removeEventListener('mousemove', handleMouseMove);
    window.removeEventListener('click', handleClick);
    window.removeEventListener('scroll', handleScroll);

    if (flushInterval.current) {
      clearInterval(flushInterval.current);
      flushInterval.current = null;
    }

    // Final flush
    flushEvents();
  }, [handleKeyDown, handleKeyUp, handleMouseMove, handleClick, handleScroll, flushEvents]);

  useEffect(() => {
    return () => {
      stopTracking();
    };
  }, [stopTracking]);

  return {
    sessionId: sessionId.current,
    eventCount: eventBuffer.current.length,
    flushEvents,
    startTracking,
    stopTracking
  };
}
