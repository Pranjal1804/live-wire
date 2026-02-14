import { create } from "zustand";
import type { BANTState } from "../components/BANTChecklist";
import type { Battlecard } from "../components/BattlecardPanel";

export type EmotionLabel =
  | "angry"
  | "disgusted"
  | "fearful"
  | "sad"
  | "neutral"
  | "happy"
  | "surprised";

export interface EmotionData {
  label: EmotionLabel;
  score: number;
  risk_level: number;
  is_negative: boolean;
  all_scores?: Record<string, number>;
}

export interface AgentAction {
  action_id: string;
  type: string;
  priority: "low" | "medium" | "high" | "critical";
  headline: string;
  suggestion: string;
  reasoning?: string;
  kb_data?: { results: Array<{ title: string; content: string; relevance: number }> };
  timestamp: string;
  dismissed?: boolean;
}

export interface TranscriptEntry {
  text: string;
  source: "mic" | "loopback" | "unknown";
  emotion?: EmotionData;
  timestamp: string;
}

interface CallState {
  isConnected: boolean;
  sessionId: string;
  isCallActive: boolean;
  callDuration: number;
  riskScore: number;
  currentEmotion: EmotionData | null;
  transcript: TranscriptEntry[];
  activeActions: AgentAction[];
  ws: WebSocket | null;

  // New: audio capture state
  micSecs: number;
  loopbackSecs: number;
  bant: BANTState;
  activeBattlecard: Battlecard | null;
  clickthroughLocked: boolean;

  // Actions
  setConnected: (v: boolean) => void;
  setCallActive: (v: boolean) => void;
  updatePerception: (data: { transcript: string; emotion: EmotionData; risk_score: number; timestamp: string }) => void;
  addAgentAction: (action: AgentAction) => void;
  dismissAction: (id: string) => void;
  sendFeedback: (actionId: string, rating: number) => void;
  setRiskScore: (v: number) => void;
  setWs: (ws: WebSocket | null) => void;

  // New actions
  addTranscriptEntry: (entry: TranscriptEntry) => void;
  setTalkRatio: (micSecs: number, loopbackSecs: number) => void;
  updateBANT: (updates: Partial<BANTState>) => void;
  setBattlecard: (card: Battlecard | null) => void;
  setClickthroughLocked: (v: boolean) => void;
  resetCallState: () => void;
}

export const useCallStore = create<CallState>((set, get) => ({
  isConnected: false,
  sessionId: `session_${Date.now()}`,
  isCallActive: false,
  callDuration: 0,
  riskScore: 0,
  currentEmotion: null,
  transcript: [],
  activeActions: [],
  ws: null,

  micSecs: 0,
  loopbackSecs: 0,
  bant: { budget: false, authority: false, need: false, timeline: false },
  activeBattlecard: null,
  clickthroughLocked: false,

  setConnected: (v) => set({ isConnected: v }),
  setCallActive: (v) => set({ isCallActive: v }),
  setRiskScore: (v) => set({ riskScore: v }),

  updatePerception: (data) =>
    set((state) => ({
      currentEmotion: data.emotion,
      riskScore: data.risk_score,
      transcript: [
        ...state.transcript.slice(-49),
        {
          text: data.transcript,
          source: "unknown" as const,
          emotion: data.emotion,
          timestamp: data.timestamp,
        },
      ],
    })),

  addTranscriptEntry: (entry) =>
    set((state) => ({
      transcript: [...state.transcript.slice(-49), entry],
    })),

  addAgentAction: (action) =>
    set((state) => ({
      activeActions: [action, ...state.activeActions].slice(0, 5),
    })),

  dismissAction: (id) =>
    set((state) => ({
      activeActions: state.activeActions.map((a) =>
        a.action_id === id ? { ...a, dismissed: true } : a
      ),
    })),

  sendFeedback: (actionId, rating) => {
    const { ws, sessionId } = get();
    ws?.send(
      JSON.stringify({
        type: "feedback",
        action_id: actionId,
        rating,
        session_id: sessionId,
      })
    );
  },

  setWs: (ws) => set({ ws }),

  setTalkRatio: (micSecs, loopbackSecs) => set({ micSecs, loopbackSecs }),

  updateBANT: (updates) =>
    set((state) => ({
      bant: { ...state.bant, ...updates },
    })),

  setBattlecard: (card) => set({ activeBattlecard: card }),

  setClickthroughLocked: (v) => set({ clickthroughLocked: v }),

  resetCallState: () =>
    set({
      transcript: [],
      activeActions: [],
      riskScore: 0,
      currentEmotion: null,
      micSecs: 0,
      loopbackSecs: 0,
      bant: { budget: false, authority: false, need: false, timeline: false },
      activeBattlecard: null,
      clickthroughLocked: false,
    }),
}));
