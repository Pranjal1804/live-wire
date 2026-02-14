import React from "react";
import { motion } from "framer-motion";
import type { EmotionData } from "../stores/callStore";

const EMOTION_COLORS: Record<string, string> = {
  angry: "#CD6060",
  disgusted: "#B8956D",
  fearful: "#D4A054",
  sad: "#6B8FBF",
  neutral: "#6E6E78",
  happy: "#6BC77C",
  surprised: "#9B8AC4",
};

interface EmotionMeterProps {
  emotion: EmotionData | null;
}

export function EmotionMeter({ emotion }: EmotionMeterProps) {
  const label = emotion?.label ?? "neutral";
  const score = emotion?.score ?? 0;
  const color = EMOTION_COLORS[label] ?? "#8B8B8B";

  const allScores = emotion?.all_scores ?? {};
  const sortedEmotions = Object.entries(allScores)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 4);

  return (
    <div className="emotion-meter">
      <div className="section-label">EMOTION ANALYSIS</div>
      <div className="emotion-main">
        <motion.div
          className="emotion-badge"
          style={{ borderColor: `${color}40` }}
          animate={{ borderColor: color }}
          transition={{ duration: 0.5 }}
        >
          <span className="emotion-label" style={{ color }}>
            {label.toUpperCase()}
          </span>
          <span className="emotion-score">{Math.round(score * 100)}%</span>
        </motion.div>
      </div>
      {sortedEmotions.length > 0 && (
        <div className="emotion-bars">
          {sortedEmotions.map(([emo, val]) => (
            <div key={emo} className="emotion-bar-row">
              <span className="bar-label">{emo}</span>
              <div className="bar-track">
                <motion.div
                  className="bar-fill"
                  style={{ backgroundColor: EMOTION_COLORS[emo] ?? "#8B8B8B" }}
                  initial={{ width: 0 }}
                  animate={{ width: `${val * 100}%` }}
                  transition={{ duration: 0.4, ease: "easeOut" }}
                />
              </div>
              <span className="bar-pct">{Math.round(val * 100)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
