import React from "react";
import { motion } from "framer-motion";
import { useCallStore, type AgentAction } from "../stores/callStore";

const PRIORITY_STYLES = {
  critical: { border: "#FF3B3B", glow: "#FF3B3B50", label: "CRITICAL" },
  high: { border: "#FF8C00", glow: "#FF8C0040", label: "HIGH" },
  medium: { border: "#FFB800", glow: "#FFB80030", label: "MEDIUM" },
  low: { border: "#8B8B8B", glow: "#8B8B8B20", label: "INFO" },
};

interface StrategyCardProps {
  action: AgentAction;
}

export function StrategyCard({ action }: StrategyCardProps) {
  const { dismissAction, sendFeedback } = useCallStore();
  const style = PRIORITY_STYLES[action.priority] ?? PRIORITY_STYLES.low;

  const handleFeedback = (rating: number) => {
    sendFeedback(action.action_id, rating);
    dismissAction(action.action_id);
  };

  return (
    <motion.div
      className="strategy-card"
      style={{
        borderColor: style.border,
        boxShadow: `0 0 20px ${style.glow}, inset 0 0 20px ${style.glow}`,
      }}
      initial={{ opacity: 0, y: -20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 20, scale: 0.95 }}
      transition={{ type: "spring", damping: 20 }}
    >
      <div className="card-header">
        <span className="priority-badge" style={{ color: style.border }}>
          {style.label}
        </span>
        <button
          className="dismiss-btn"
          onClick={() => dismissAction(action.action_id)}
        >
          X
        </button>
      </div>

      <div className="card-headline">{action.headline}</div>

      <div className="card-suggestion">
        <div className="suggestion-label">SAY THIS:</div>
        <div className="suggestion-text">"{action.suggestion}"</div>
      </div>

      {action.kb_data?.results?.length ? (
        <div className="card-kb">
          <div className="kb-label">KNOWLEDGE BASE:</div>
          {action.kb_data.results.slice(0, 1).map((r, i) => (
            <div key={i} className="kb-item">
              <div className="kb-title">{r.title}</div>
              <div className="kb-content">
                {r.content.substring(0, 120)}...
              </div>
            </div>
          ))}
        </div>
      ) : null}

      {action.reasoning && (
        <div className="card-reasoning">
          REASONING: {action.reasoning}
        </div>
      )}

      <div className="card-feedback">
        <span className="feedback-label">Was this helpful?</span>
        <div className="feedback-btns">
          {[1, 2, 3, 4, 5].map((rating) => (
            <button
              key={rating}
              className="feedback-star"
              onClick={() => handleFeedback(rating)}
              title={`Rate ${rating}/5`}
            >
              {rating}
            </button>
          ))}
        </div>
      </div>
    </motion.div>
  );
}
