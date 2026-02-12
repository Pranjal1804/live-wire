import { create } from "zustand";

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
  emotion: EmotionData;
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
  setConnected: (v: boolean) => void;
  setCallActive: (v: boolean) => void;
  updatePerception: (data: { transcript: string; emotion: EmotionData; risk_score: number; timestamp: string }) => void;
  addAgentAction: (action: AgentAction) => void;
  dismissAction: (id: string) => void;
  sendFeedback: (actionId: string, rating: number) => void;
  setRiskScore: (v: number) => void;
  ws: WebSocket | null;
  setWs: (ws: WebSocket | null) => void;
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

  setConnected: (v) => set({ isConnected: v }),
  setCallActive: (v) => set({ isCallActive: v }),
  setRiskScore: (v) => set({ riskScore: v }),

  updatePerception: (data) =>
    set((state) => ({
      currentEmotion: data.emotion,
      riskScore: data.risk_score,
      transcript: [
        ...state.transcript.slice(-49),
        { text: data.transcript, emotion: data.emotion, timestamp: data.timestamp },
      ],
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
}));
