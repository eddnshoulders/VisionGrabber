import { useEffect, useRef, useCallback } from "react";
import { WsMessage } from "../types/messages";

const WS_URL = `ws://${window.location.host}/ws`;
const RECONNECT_DELAY_MS = 3000;

type MessageHandler = (msg: WsMessage) => void;

/**
 * useWebSocket
 *
 * Maintains a persistent WebSocket connection to the backend.
 * Automatically reconnects on disconnect.
 * Calls onMessage for every received message.
 */
export function useWebSocket(onMessage: MessageHandler) {
  const wsRef           = useRef<WebSocket | null>(null);
  const onMessageRef    = useRef<MessageHandler>(onMessage);
  const reconnectTimer  = useRef<ReturnType<typeof setTimeout> | null>(null);
  const unmountedRef    = useRef(false);

  // Keep onMessage ref current without triggering reconnect
  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  const connect = useCallback(() => {
    if (unmountedRef.current) return;

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log("[WS] Connected");
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current);
        reconnectTimer.current = null;
      }
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data) as WsMessage;
        onMessageRef.current(msg);
      } catch (e) {
        console.warn("[WS] Failed to parse message:", event.data, e);
      }
    };

    ws.onclose = () => {
      console.log("[WS] Disconnected - reconnecting in", RECONNECT_DELAY_MS, "ms");
      wsRef.current = null;
      if (!unmountedRef.current) {
        reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY_MS);
      }
    };

    ws.onerror = (err) => {
      console.error("[WS] Error:", err);
      ws.close();
    };
  }, []);

  useEffect(() => {
    unmountedRef.current = false;
    connect();
    return () => {
      unmountedRef.current = true;
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);
}
