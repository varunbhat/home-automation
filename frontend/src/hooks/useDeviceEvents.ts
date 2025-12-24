// React hook for Server-Sent Events (SSE) from ManeYantra API
// Implements robust reconnection with exponential backoff

import { useEffect, useState, useCallback, useRef } from "react";
import { api } from "../lib/api";
import type { SSEEvent, SSEEventType } from "../types/api";

interface UseDeviceEventsOptions {
  deviceId?: string;
  eventType?: SSEEventType;
  onEvent?: (event: SSEEvent) => void;
  autoConnect?: boolean;
  maxReconnectAttempts?: number;
  initialReconnectDelay?: number;
}

interface UseDeviceEventsReturn {
  events: SSEEvent[];
  connected: boolean;
  error: string | null;
  reconnectAttempts: number;
  connect: () => void;
  disconnect: () => void;
  clearEvents: () => void;
}

export function useDeviceEvents(
  options: UseDeviceEventsOptions = {}
): UseDeviceEventsReturn {
  const {
    deviceId,
    eventType,
    onEvent,
    autoConnect = true,
    maxReconnectAttempts = 5,
    initialReconnectDelay = 1000, // Start with 1 second
  } = options;

  const [events, setEvents] = useState<SSEEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);

  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const shouldConnectRef = useRef(autoConnect);
  const reconnectAttemptsRef = useRef(0);
  const mountedRef = useRef(true);

  const clearReconnectTimeout = useCallback(() => {
    if (reconnectTimeoutRef.current !== null) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
  }, []);

  const disconnect = useCallback(() => {
    shouldConnectRef.current = false;
    clearReconnectTimeout();

    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
      setConnected(false);
    }
  }, [clearReconnectTimeout]);

  const scheduleReconnect = useCallback(() => {
    if (!shouldConnectRef.current || !mountedRef.current) {
      return;
    }

    if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
      console.error(
        `[SSE] Max reconnection attempts (${maxReconnectAttempts}) reached. Giving up.`
      );
      setError(`Failed to connect after ${maxReconnectAttempts} attempts`);
      return;
    }

    // Exponential backoff: 1s, 2s, 4s, 8s, 16s
    const delay = initialReconnectDelay * Math.pow(2, reconnectAttemptsRef.current);
    const jitter = Math.random() * 1000; // Add 0-1s jitter to prevent thundering herd
    const totalDelay = Math.min(delay + jitter, 30000); // Cap at 30 seconds

    console.log(
      `[SSE] Scheduling reconnect attempt ${reconnectAttemptsRef.current + 1}/${maxReconnectAttempts} in ${Math.round(totalDelay / 1000)}s`
    );

    clearReconnectTimeout();
    reconnectTimeoutRef.current = window.setTimeout(() => {
      if (shouldConnectRef.current && mountedRef.current) {
        reconnectAttemptsRef.current++;
        setReconnectAttempts(reconnectAttemptsRef.current);
        connect();
      }
    }, totalDelay);
  }, [maxReconnectAttempts, initialReconnectDelay, clearReconnectTimeout]);

  const connect = useCallback(() => {
    // Clean up existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    clearReconnectTimeout();
    shouldConnectRef.current = true;
    setError(null);

    // Get SSE URL
    const url = deviceId
      ? api.getDeviceEventStreamURL(deviceId)
      : api.getEventStreamURL({ event_type: eventType });

    console.log(
      `[SSE] Connecting to: ${url} (attempt ${reconnectAttemptsRef.current + 1})`
    );

    const eventSource = new EventSource(url);
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      if (!mountedRef.current) return;

      console.log("[SSE] Connection opened successfully", {
        deviceId,
        eventType,
        url,
      });

      setConnected(true);
      setError(null);

      // Reset reconnection attempts on successful connection
      reconnectAttemptsRef.current = 0;
      setReconnectAttempts(0);
    };

    eventSource.onerror = (err) => {
      if (!mountedRef.current) return;

      console.error("[SSE] Connection error:", err);

      // EventSource will automatically try to reconnect by default
      // We need to handle our own reconnection logic
      const readyState = eventSource.readyState;

      if (readyState === EventSource.CLOSED) {
        console.warn("[SSE] Connection closed by server");
        setError("Connection closed");
        setConnected(false);

        // Close and schedule reconnect with backoff
        eventSource.close();
        eventSourceRef.current = null;
        scheduleReconnect();
      } else if (readyState === EventSource.CONNECTING) {
        console.log("[SSE] Connection in progress...");
        setError("Connecting...");
      }
    };

    // Handle specific event types
    const eventTypes: SSEEventType[] = [
      "connected",
      "state",
      "discovery",
      "available",
      "error",
      "system",
      "heartbeat",
    ];

    eventTypes.forEach((type) => {
      eventSource.addEventListener(type, (event) => {
        if (!mountedRef.current) return;

        try {
          const eventData = (event as MessageEvent).data;

          // Check for undefined/empty data
          if (!eventData || eventData === "undefined" || eventData === "null") {
            console.warn(`[SSE] Received ${type} event with no data, skipping`);
            return;
          }

          const data = JSON.parse(eventData);
          const sseEvent: SSEEvent = {
            type,
            timestamp: new Date().toISOString(),
            ...data,
          };

          // Only log state and available events to reduce noise
          if (type === "state" || type === "available") {
            console.log(`[SSE] Received ${type} event:`, sseEvent);
          }

          setEvents((prev) => [sseEvent, ...prev].slice(0, 100)); // Keep last 100 events

          if (onEvent) {
            onEvent(sseEvent);
          }
        } catch (err) {
          console.error(`[SSE] Error parsing ${type} event:`, err);
        }
      });
    });

    // Handle generic messages
    eventSource.onmessage = (event) => {
      if (!mountedRef.current) return;

      try {
        const eventData = event.data;

        // Check for undefined/empty data
        if (!eventData || eventData === "undefined" || eventData === "null") {
          console.warn("[SSE] Received message with no data, skipping");
          return;
        }

        const data = JSON.parse(eventData);
        const sseEvent: SSEEvent = {
          type: "system",
          timestamp: new Date().toISOString(),
          ...data,
        };

        setEvents((prev) => [sseEvent, ...prev].slice(0, 100));

        if (onEvent) {
          onEvent(sseEvent);
        }
      } catch (err) {
        console.error("[SSE] Error parsing message:", err);
      }
    };
  }, [deviceId, eventType, onEvent, clearReconnectTimeout, scheduleReconnect]);

  const clearEvents = useCallback(() => {
    setEvents([]);
  }, []);

  // Auto-connect on mount if enabled
  useEffect(() => {
    mountedRef.current = true;

    if (autoConnect) {
      connect();
    }

    // Cleanup on unmount
    return () => {
      mountedRef.current = false;
      disconnect();
    };
  }, [autoConnect, connect, disconnect]);

  return {
    events,
    connected,
    error,
    reconnectAttempts,
    connect,
    disconnect,
    clearEvents,
  };
}
