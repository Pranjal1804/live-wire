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
    if (pct >= 75) return "#FF3E3E";
    if (pct >= 50) return "#FF9D00";
    if (pct >= 25) return "#FFD600";
    return "#00FFA3";
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
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: [0.5, 1, 0.5], scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 1.5, repeat: Infinity }}
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
            animate={{ opacity: [1, 0.3, 1] }}
            transition={{ duration: 1.5, repeat: Infinity }}
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
                    ? "#6B9FFF"
                    : "var(--accent-blue)"
              : entry.source === "mic"
                ? "var(--accent-cyan)"
                : "var(--accent-orange, #ff9d00)";

            return (
              <motion.div
                key={entry.timestamp}
                className={`transcript-entry ${emotion?.is_negative ? "entry-negative" : ""
                  }`}
                initial={{ opacity: 0, x: 20 }}
                animate={{
                  opacity: Math.max(1 - i * 0.08, 0.3),
                  x: 0,
                  scale: 1 - i * 0.015,
                }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ duration: 0.2 }}
                layout
              >
                <div
                  className="entry-dot"
                  style={{
                    background: dotColor,
                    boxShadow: `0 0 6px ${dotColor}60`,
                  }}
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
            fontFamily: "var(--font-mono)",
            fontSize: 9,
            letterSpacing: 2,
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
