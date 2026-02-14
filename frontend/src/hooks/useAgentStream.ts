import { useEffect, useRef, useCallback } from "react";
import { useCallStore } from "../stores/callStore";
import { tauriAPI } from "../tauriAPI";

const WS_URL = "ws://localhost:8000/ws";
const RECONNECT_DELAY = 3000;

export function useAgentStream() {
  const store = useCallStore();
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(false);
  const agentTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    if (
      wsRef.current &&
      (wsRef.current.readyState === WebSocket.OPEN ||
        wsRef.current.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }

    const sessionId = store.sessionId;
    const ws = new WebSocket(`${WS_URL}/${sessionId}`);
    wsRef.current = ws;
    store.setWs(ws);

    ws.onopen = () => {
      store.setConnected(true);
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        handleMessage(msg);
      } catch (e) {
        console.error("WS parse error:", e);
      }
    };

    ws.onerror = (e) => {
      console.error("WS error:", e);
    };

    ws.onclose = (event) => {
      store.setConnected(false);
      store.setWs(null);
      wsRef.current = null;

      if (event.code !== 1000 && mountedRef.current) {
        reconnectTimerRef.current = setTimeout(() => {
          if (mountedRef.current) connect();
        }, RECONNECT_DELAY);
      }
    };
  }, []);

  function handleMessage(msg: { type: string; data?: any }) {
    switch (msg.type) {
      case "connected":
        break;
      case "call_started":
        store.setCallActive(true);
        break;
      case "call_ended":
      case "call_summary":
        store.setCallActive(false);
        break;
      case "perception_update":
        if (store.isCallActive) {
          store.updatePerception(msg.data);
        }
        break;
      case "agent_action":
        store.addAgentAction(msg.data);
        // Clear any previous agent timeout to prevent race conditions
        if (agentTimerRef.current) {
          clearTimeout(agentTimerRef.current);
        }
        tauriAPI.setClickthrough(false);
        store.setClickthroughLocked(true);
        agentTimerRef.current = setTimeout(() => {
          store.setClickthroughLocked(false);
          tauriAPI.setClickthrough(true);
          agentTimerRef.current = null;
        }, 10000);
        break;
      case "shutdown":
        store.setConnected(false);
        store.setCallActive(false);
        break;
      default:
        break;
    }
  }

  useEffect(() => {
    mountedRef.current = true;
    connect();

    return () => {
      mountedRef.current = false;
      if (agentTimerRef.current) {
        clearTimeout(agentTimerRef.current);
      }
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close(1000, "Component unmounted");
      }
    };
  }, [connect]);

  const startCall = useCallback(() => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      return;
    }
    ws.send(JSON.stringify({ type: "call_start", call_metadata: {} }));
  }, []);

  const endCall = useCallback(() => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      store.setCallActive(false);
      return;
    }
    ws.send(JSON.stringify({ type: "call_end" }));
    store.setCallActive(false);
  }, []);

  return { startCall, endCall };
}
