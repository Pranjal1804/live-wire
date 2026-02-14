import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useCallStore, type EmotionData } from "../stores/callStore";

interface RiskAlertProps {
  riskScore: number;
  emotion: EmotionData | null;
}

export function RiskAlert({ riskScore, emotion }: RiskAlertProps) {
  const pct = Math.round(riskScore * 100);

  const getRiskColor = () => {
    if (pct >= 75) return "#CD6060";
    if (pct >= 50) return "#D4A054";
    if (pct >= 25) return "#B8956D";
    return "#6BC77C";
  };

  const getRiskLabel = () => {
    if (pct >= 75) return "CRITICAL";
    if (pct >= 50) return "HIGH RISK";
    if (pct >= 25) return "MODERATE";
    return "STABLE";
  };

  const color = getRiskColor();

  return (
    <div className="risk-container">
      <div className="section-label">CALL RISK</div>
      <div className="risk-bar-container">
        <motion.div
          className="risk-bar"
          animate={{ width: `${pct}%`, backgroundColor: color }}
          transition={{ duration: 0.6, ease: "easeOut" }}
        />
      </div>
      <div className="risk-info">
        <motion.span
          className="risk-label"
          animate={{ color }}
          transition={{ duration: 0.4 }}
        >
          {getRiskLabel()}
        </motion.span>
        <span className="risk-pct">{pct}%</span>
      </div>
      <AnimatePresence>
        {pct >= 75 && (
          <motion.div
            className="critical-pulse"
            initial={{ opacity: 0 }}
            animate={{ opacity: [0.6, 1, 0.6] }}
            exit={{ opacity: 0 }}
            transition={{ duration: 2.5, repeat: Infinity, ease: "easeInOut" }}
          >
            ESCALATION RISK
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export function TranscriptFeed() {
  const { transcript, isCallActive, isConnected } = useCallStore();
  const recent = transcript.slice(-10).reverse();

  if (!isConnected) {
    return (
      <div className="transcript-feed">
        <div className="section-label">LIVE TRANSCRIPT</div>
        <div className="transcript-empty">
          <div className="empty-text">BACKEND OFFLINE</div>
          <div className="empty-sub">Connection lost</div>
        </div>
      </div>
    );
  }

  if (!isCallActive) {
    return (
      <div className="transcript-feed">
        <div className="section-label">LIVE TRANSCRIPT</div>
        <div className="transcript-empty">
          <div className="empty-text">NOT MONITORING</div>
          <div className="empty-sub">Press start to begin</div>
        </div>
      </div>
    );
  }

  if (recent.length === 0) {
    return (
      <div className="transcript-feed">
        <div className="section-label">LIVE TRANSCRIPT</div>
        <div className="transcript-empty">
          <motion.div
            className="empty-icon"
            animate={{ opacity: [1, 0.35, 1] }}
            transition={{ duration: 2.2, repeat: Infinity, ease: "easeInOut" }}
          >
            LIVE
          </motion.div>
          <div className="empty-text">LISTENING</div>
          <div className="empty-sub">Waiting for speech</div>
        </div>
      </div>
    );
  }

  return (
    <div className="transcript-feed">
      <div className="section-label">LIVE TRANSCRIPT</div>
      <div className="transcript-list">
        <AnimatePresence mode="popLayout">
          {recent.map((entry, i) => {
            const emotion = entry.emotion;
            const dotColor = emotion
              ? emotion.label === "angry"
                ? "var(--accent-red)"
                : emotion.label === "happy"
                  ? "var(--accent-green)"
                  : emotion.label === "sad"
                    ? "#6B8FBF"
                    : "var(--accent-blue)"
              : entry.source === "mic"
                ? "var(--accent-cyan)"
                : "var(--accent-orange)";

            return (
              <motion.div
                key={entry.timestamp}
                className={`transcript-entry ${emotion?.is_negative ? "entry-negative" : ""
                  }`}
                initial={{ opacity: 0, y: 6 }}
                animate={{
                  opacity: Math.max(1 - i * 0.07, 0.35),
                  y: 0,
                }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.18, ease: [0.25, 0.1, 0.25, 1] }}
                layout
              >
                <div
                  className="entry-dot"
                  style={{ background: dotColor }}
                />
                <span className="entry-text">{entry.text}</span>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </div>
  );
}

export function AgentStatus() {
  const { activeActions, isConnected, isCallActive } = useCallStore();
  const pendingCount = activeActions.filter((a) => !a.dismissed).length;

  const getStatusText = () => {
    if (!isConnected) return "DISCONNECTED";
    if (!isCallActive) return "STANDBY";
    return "MONITORING";
  };

  const getStatusColor = () => {
    if (!isConnected) return "var(--accent-red)";
    if (!isCallActive) return "var(--text-dim)";
    return "var(--accent-cyan)";
  };

  return (
    <div className="agent-status">
      <div className="status-row">
        <span className="agent-label">MAESTRO AGENT</span>
        <motion.span
          style={{
            fontFamily: "var(--font-sans)",
            fontSize: 10.5,
            letterSpacing: 0.5,
            fontWeight: 500,
            color: getStatusColor(),
          }}
          animate={{ color: getStatusColor() }}
          transition={{ duration: 0.3 }}
        >
          {getStatusText()}
        </motion.span>
        <div
          className={`agent-dot ${isConnected && isCallActive ? "pulsing" : ""}`}
          style={{ background: getStatusColor(), marginLeft: 8 }}
        />
      </div>

      {pendingCount > 0 && (
        <motion.div
          className="pending-label"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          {pendingCount} ACTIVE SUGGESTION{pendingCount !== 1 ? "S" : ""}
        </motion.div>
      )}
    </div>
  );
}
