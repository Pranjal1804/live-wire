import React from "react";
import { motion, AnimatePresence } from "framer-motion";

export interface BANTState {
  budget: boolean;
  authority: boolean;
  need: boolean;
  timeline: boolean;
}

interface BANTChecklistProps {
  bant: BANTState;
}

const BANT_ITEMS: { key: keyof BANTState; label: string; icon: string }[] = [
  { key: "budget", label: "BUDGET", icon: "$" },
  { key: "authority", label: "AUTHORITY", icon: "A" },
  { key: "need", label: "NEED", icon: "N" },
  { key: "timeline", label: "TIMELINE", icon: "T" },
];

export function BANTChecklist({ bant }: BANTChecklistProps) {
  const qualifiedCount = Object.values(bant).filter(Boolean).length;

  return (
    <div className="bant-container">
      <div className="bant-header">
        <span className="section-label">BANT QUALIFICATION</span>
        <span
          className="bant-score"
          style={{
            color:
              qualifiedCount >= 3
                ? "var(--accent-green)"
                : qualifiedCount >= 2
                  ? "var(--accent-cyan)"
                  : "var(--text-dim)",
          }}
        >
          {qualifiedCount}/4
        </span>
      </div>

      <div className="bant-grid">
        {BANT_ITEMS.map((item) => {
          const checked = bant[item.key];
          return (
            <div
              key={item.key}
              className={`bant-item ${checked ? "bant-item-checked" : ""}`}
            >
              <AnimatePresence mode="wait">
                <motion.div
                  key={checked ? "on" : "off"}
                  className="bant-icon"
                  initial={{ scale: 0.85, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  exit={{ scale: 0.85, opacity: 0 }}
                  transition={{ type: "spring", stiffness: 400, damping: 22 }}
                  style={{
                    color: checked ? "var(--accent-green)" : "var(--text-dim)",
                    borderColor: checked
                      ? "var(--accent-green)"
                      : "var(--border-dim)",
                  }}
                >
                  {checked ? "\u2713" : item.icon}
                </motion.div>
              </AnimatePresence>
              <span
                className="bant-label"
                style={{
                  color: checked ? "var(--text-primary)" : "var(--text-dim)",
                }}
              >
                {item.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
