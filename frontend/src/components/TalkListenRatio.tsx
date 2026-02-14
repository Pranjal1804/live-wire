import React from "react";
import { motion } from "framer-motion";

interface TalkListenRatioProps {
  micSecs: number;
  loopbackSecs: number;
}

export function TalkListenRatio({ micSecs, loopbackSecs }: TalkListenRatioProps) {
  const total = micSecs + loopbackSecs;
  const micPct = total > 0 ? (micSecs / total) * 100 : 50;
  const loopbackPct = total > 0 ? (loopbackSecs / total) * 100 : 50;

  // Ideal range: 40-60% talk ratio. Outside that is a warning.
  const isHealthy = micPct >= 30 && micPct <= 60;

  return (
    <div className="talk-ratio-container">
      <div className="talk-ratio-header">
        <span className="section-label">TALK : LISTEN</span>
        <span
          className="talk-ratio-badge"
          style={{
            color: isHealthy ? "var(--accent-cyan)" : "var(--accent-orange)",
          }}
        >
          {Math.round(micPct)}% : {Math.round(loopbackPct)}%
        </span>
      </div>

      <div className="talk-ratio-bar-track">
        <motion.div
          className="talk-ratio-bar-fill talk-ratio-mic"
          animate={{ width: `${micPct}%` }}
          transition={{ duration: 0.5, ease: "easeOut" }}
        />
        <motion.div
          className="talk-ratio-bar-fill talk-ratio-loopback"
          animate={{ width: `${loopbackPct}%` }}
          transition={{ duration: 0.5, ease: "easeOut" }}
        />
      </div>

      <div className="talk-ratio-labels">
        <span className="talk-ratio-label-mic">
          YOU {formatTime(micSecs)}
        </span>
        <span className="talk-ratio-label-loopback">
          CLIENT {formatTime(loopbackSecs)}
        </span>
      </div>
    </div>
  );
}

function formatTime(secs: number): string {
  const m = Math.floor(secs / 60);
  const s = Math.floor(secs % 60);
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}
