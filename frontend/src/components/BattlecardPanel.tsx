import React from "react";
import { motion, AnimatePresence } from "framer-motion";

const tap = { type: "spring" as const, stiffness: 500, damping: 30 };

export interface Battlecard {
  competitor: string;
  talking_points: string[];
  weaknesses: string[];
  counter_objections: Record<string, string>;
}

interface BattlecardPanelProps {
  battlecard: Battlecard | null;
  onDismiss: () => void;
}

export function BattlecardPanel({ battlecard, onDismiss }: BattlecardPanelProps) {
  return (
    <AnimatePresence>
      {battlecard && (
        <motion.div
          className="battlecard-container"
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -6 }}
          transition={{ type: "spring", damping: 26, stiffness: 300 }}
        >
          <div className="battlecard-header">
            <span className="battlecard-badge">BATTLECARD</span>
            <span className="battlecard-competitor">
              vs. {battlecard.competitor}
            </span>
            <motion.button
              className="battlecard-dismiss"
              onClick={onDismiss}
              whileTap={{ scale: 0.9 }}
              transition={tap}
            >
              X
            </motion.button>
          </div>

          {battlecard.talking_points.length > 0 && (
            <div className="battlecard-section">
              <span className="battlecard-section-label">TALKING POINTS</span>
              <ul className="battlecard-list">
                {battlecard.talking_points.map((point, i) => (
                  <li key={i} className="battlecard-point">
                    {point}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {battlecard.weaknesses.length > 0 && (
            <div className="battlecard-section">
              <span className="battlecard-section-label">THEIR WEAKNESSES</span>
              <ul className="battlecard-list battlecard-list-weak">
                {battlecard.weaknesses.map((w, i) => (
                  <li key={i} className="battlecard-point battlecard-weakness">
                    {w}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {Object.keys(battlecard.counter_objections).length > 0 && (
            <div className="battlecard-section">
              <span className="battlecard-section-label">COUNTER OBJECTIONS</span>
              {Object.entries(battlecard.counter_objections).map(([key, val]) => (
                <div key={key} className="battlecard-objection">
                  <span className="battlecard-objection-key">{key}:</span>{" "}
                  {val}
                </div>
              ))}
            </div>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
