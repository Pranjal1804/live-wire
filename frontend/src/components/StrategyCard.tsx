import React from "react";
import { motion } from "framer-motion";
import { useCallStore, type AgentAction } from "../stores/callStore";

const tap = { type: "spring" as const, stiffness: 500, damping: 30 };

const PRIORITY_STYLES = {
  critical: { border: "#CD6060", label: "CRITICAL" },
  high: { border: "#D4A054", label: "HIGH" },
  medium: { border: "#B8956D", label: "MEDIUM" },
  low: { border: "#6E6E78", label: "INFO" },
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
        borderColor: `${style.border}40`,
      }}
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 8 }}
      transition={{ type: "spring", damping: 26, stiffness: 280 }}
    >
      <div className="card-header">
        <span className="priority-badge" style={{ color: style.border }}>
          {style.label}
        </span>
        <motion.button
          className="dismiss-btn"
          onClick={() => dismissAction(action.action_id)}
          whileTap={{ scale: 0.92 }}
          transition={tap}
        >
          X
        </motion.button>
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
            <motion.button
              key={rating}
              className="feedback-star"
              onClick={() => handleFeedback(rating)}
              title={`Rate ${rating}/5`}
              whileTap={{ scale: 0.88 }}
              transition={tap}
            >
              {rating}
            </motion.button>
          ))}
        </div>
      </div>
    </motion.div>
  );
}
