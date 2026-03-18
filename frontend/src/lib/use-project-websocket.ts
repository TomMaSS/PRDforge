"use client";

import { useEffect, useRef, useState, useCallback } from "react";

interface WSEvent {
  type: string;
  data: Record<string, unknown>;
}

interface PresenceUser {
  id: string;
  name: string;
  activeSection?: string;
}

interface UseProjectWebSocketOptions {
  projectSlug: string;
  userId: string;
  enabled?: boolean;
  onEvent?: (event: WSEvent) => void;
}

export function useProjectWebSocket({
  projectSlug,
  userId,
  enabled = true,
  onEvent,
}: UseProjectWebSocketOptions) {
  const [connected, setConnected] = useState(false);
  const [presence, setPresence] = useState<PresenceUser[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const retryRef = useRef(0);
  const maxRetries = 10;

  const connect = useCallback(async () => {
    if (!enabled || !projectSlug || !userId) return;

    try {
      // Get WS token
      const res = await fetch("/api/ws-token", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, project_slug: projectSlug }),
      });
      if (!res.ok) return;
      const { token } = await res.json();

      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const ws = new WebSocket(
        `${protocol}//${window.location.host}/ws/projects/${projectSlug}?token=${token}`
      );

      ws.onopen = () => {
        setConnected(true);
        retryRef.current = 0;
      };

      ws.onmessage = (e) => {
        try {
          const event: WSEvent = JSON.parse(e.data);
          if (event.type === "presence_update") {
            setPresence(event.data.users as PresenceUser[]);
          }
          onEvent?.(event);
        } catch {
          // ignore malformed messages
        }
      };

      ws.onclose = () => {
        setConnected(false);
        wsRef.current = null;
        // Exponential backoff with jitter
        if (retryRef.current < maxRetries) {
          const delay = Math.min(
            1000 * Math.pow(2, retryRef.current),
            30000
          );
          const jitter = Math.random() * 1000 - 500;
          retryRef.current++;
          setTimeout(connect, delay + jitter);
        }
      };

      ws.onerror = () => {
        ws.close();
      };

      wsRef.current = ws;
    } catch {
      // token fetch failed, retry
      if (retryRef.current < maxRetries) {
        retryRef.current++;
        setTimeout(connect, 3000);
      }
    }
  }, [projectSlug, userId, enabled, onEvent]);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
    };
  }, [connect]);

  return { connected, presence };
}
