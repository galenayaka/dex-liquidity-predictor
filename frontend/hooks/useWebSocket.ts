"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { WSMessage } from "@/lib/types";

export type ConnectionStatus = "connecting" | "open" | "closed" | "error";

const DEFAULT_URL =
  process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws";
const MAX_MESSAGES = 200;

export interface UseWebSocketResult {
  /** Current WebSocket connection state. */
  status: ConnectionStatus;
  /** Most recent parsed message, or null before the first frame arrives. */
  lastMessage: WSMessage | null;
  /** Bounded history of parsed messages (newest last). */
  messages: WSMessage[];
  /** Send a JSON-serialisable message to the server (optional utility). */
  send: (message: unknown) => void;
}

/**
 * Subscribe to the FastAPI `/ws` real-time stream.
 *
 * Reconnects automatically with exponential backoff and keeps the most
 * recent messages in memory so the UI can derive snapshots, events and
 * alerts without extra state management.
 */
export function useWebSocket(url: string = DEFAULT_URL): UseWebSocketResult {
  const [status, setStatus] = useState<ConnectionStatus>("connecting");
  const [lastMessage, setLastMessage] = useState<WSMessage | null>(null);
  const [messages, setMessages] = useState<WSMessage[]>([]);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let disposed = false;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;
    let retryDelay = 1000;

    const connect = () => {
      if (disposed) return;
      setStatus("connecting");

      const socket = new WebSocket(url);
      socketRef.current = socket;

      socket.onopen = () => {
        if (disposed) return;
        retryDelay = 1000;
        setStatus("open");
      };

      socket.onmessage = (event: MessageEvent<string>) => {
        if (disposed) return;
        try {
          const parsed = JSON.parse(event.data) as WSMessage;
          setLastMessage(parsed);
          setMessages((prev) => [...prev.slice(-(MAX_MESSAGES - 1)), parsed]);
        } catch {
          // Ignore malformed / non-JSON frames.
        }
      };

      socket.onerror = () => {
        if (!disposed) setStatus("error");
      };

      socket.onclose = () => {
        if (disposed) return;
        socketRef.current = null;
        setStatus("closed");
        retryTimer = setTimeout(connect, retryDelay);
        retryDelay = Math.min(retryDelay * 2, 15_000);
      };
    };

    connect();

    return () => {
      disposed = true;
      if (retryTimer) clearTimeout(retryTimer);
      socketRef.current?.close();
      socketRef.current = null;
    };
  }, [url]);

  const send = useCallback((message: unknown) => {
    const socket = socketRef.current;
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(typeof message === "string" ? message : JSON.stringify(message));
    }
  }, []);

  return { status, lastMessage, messages, send };
}
