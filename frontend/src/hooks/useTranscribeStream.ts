import { useEffect, useRef, useCallback, useState } from "react";
import { useCallStore } from "../stores/callStore";

const TRANSCRIBE_WS_URL = "ws://localhost:8000/ws/transcribe";
const RECONNECT_DELAY = 3000;

/**
 * Manages the WebSocket connection to /ws/transcribe.
 * Receives transcription results + battlecard triggers from the backend
 * and pushes them into the Zustand store.
 *
 * The useAudioCapture hook sends audio chunks to this WebSocket;
 * this hook handles the responses.
 */
export function useTranscribeStream() {
  const store = useCallStore();
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(false);
  const [isConnected, setIsConnected] = useState(false);

  const connect = useCallback(() => {
    if (
      wsRef.current &&
      (wsRef.current.readyState === WebSocket.OPEN ||
        wsRef.current.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }

    const ws = new WebSocket(TRANSCRIBE_WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
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
        console.error("Transcribe WS parse error:", e);
      }
    };

    ws.onerror = (e) => {
      console.error("Transcribe WS error:", e);
    };

    ws.onclose = (event) => {
      setIsConnected(false);
      wsRef.current = null;

      if (event.code !== 1000 && mountedRef.current) {
        reconnectTimerRef.current = setTimeout(() => {
          if (mountedRef.current) connect();
        }, RECONNECT_DELAY);
      }
    };
  }, []);

  function handleMessage(msg: {
    type?: string;
    text?: string;
    words?: Array<{ word: string; start: number; end: number }>;
    source?: string;
    duration_secs?: number;
    latency_ms?: number;
    backend?: string;
    battlecard?: {
      competitor: string;
      talking_points: string[];
      weaknesses: string[];
      counter_objections: Record<string, string>;
    };
    bant_updates?: Record<string, boolean>;
    error?: string;
  }) {
    if (msg.error) {
      console.warn("Transcribe backend error:", msg.error);
      return;
    }

    if (msg.type === "transcript" && msg.text) {
      store.addTranscriptEntry({
        text: msg.text,
        source: (msg.source as "mic" | "loopback") || "unknown",
        timestamp: new Date().toISOString(),
      });
    }

    // Battlecard triggered by keyword match (instant, no LLM)
    if (msg.battlecard) {
      store.setBattlecard(msg.battlecard);
    }

    // BANT updates from LLM router
    if (msg.bant_updates) {
      store.updateBANT(msg.bant_updates);
    }
  }

  useEffect(() => {
    mountedRef.current = true;
    connect();

    return () => {
      mountedRef.current = false;
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close(1000, "Component unmounted");
      }
    };
  }, [connect]);

  return {
    transcribeWs: wsRef.current,
    isTranscribeConnected: isConnected,
  };
}
