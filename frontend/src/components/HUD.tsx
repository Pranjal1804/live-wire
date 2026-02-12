import React, { useState, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useCallStore } from "../stores/callStore";
import { EmotionMeter } from "./EmotionMeter";
import { StrategyCard } from "./StrategyCard";
import { TranscriptFeed } from "./TranscriptFeed";
import { RiskAlert } from "./RiskAlert";
import { AgentStatus } from "./AgentStatus";

interface HUDProps {
  onStartCall: () => void;
  onEndCall: () => void;
}

export function HUD({ onStartCall, onEndCall }: HUDProps) {
  const { isConnected, isCallActive, riskScore, currentEmotion, activeActions } =
    useCallStore();

  const [collapsed, setCollapsed] = useState(false);
  const [showTranscript, setShowTranscript] = useState(false);

  const leaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleMouseEnter = useCallback(() => {
    if (leaveTimer.current) {
      clearTimeout(leaveTimer.current);
      leaveTimer.current = null;
    }
    (window as any).electronAPI?.setClickthrough(false);
  }, []);

  const handleMouseLeave = useCallback(() => {
    leaveTimer.current = setTimeout(() => {
      (window as any).electronAPI?.setClickthrough(true);
    }, 120);
  }, []);

  const visibleAction = activeActions.find((a) => !a.dismissed && a.priority === "critical")
    ?? activeActions.find((a) => !a.dismissed && a.priority === "high")
    ?? activeActions.find((a) => !a.dismissed && a.priority === "medium")
    ?? activeActions.find((a) => !a.dismissed);

  const handleClose = () => {
    (window as any).electronAPI?.closeApp();
  };

  return (
    <div
      className="hud-root"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <motion.div
        className="status-bar"
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.4 }}
      >
        <div className={`dot ${isConnected ? "dot-green" : "dot-red"}`} />
        <span className="status-label">
          {isConnected ? "MAESTRO ONLINE" : "OFFLINE"}
        </span>

        <button
          className="collapse-btn"
          onClick={() => setCollapsed((c) => !c)}
          title="Toggle HUD"
          style={{ marginRight: 6 }}
        >
          {collapsed ? "+" : "-"}
        </button>

        <button
          className="close-btn"
          onClick={handleClose}
          title="Close MAESTRO"
        >
          X
        </button>
      </motion.div>

      <AnimatePresence>
        {!collapsed && (
          <motion.div
            className="hud-panel"
            initial={{ opacity: 0, x: 100 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 100 }}
            transition={{ type: "spring", damping: 25, stiffness: 200 }}
          >
            <RiskAlert riskScore={riskScore} emotion={currentEmotion} />
            <EmotionMeter emotion={currentEmotion} />

            <div className="call-controls">
              {!isCallActive ? (
                <motion.button
                  className="btn btn-start"
                  onClick={onStartCall}
                  whileHover={{ scale: 1.03 }}
                  whileTap={{ scale: 0.97 }}
                >
                  START MONITORING
                </motion.button>
              ) : (
                <motion.button
                  className="btn btn-stop"
                  onClick={onEndCall}
                  whileHover={{ scale: 1.03 }}
                  whileTap={{ scale: 0.97 }}
                >
                  END CALL
                </motion.button>
              )}
            </div>

            <AnimatePresence mode="wait">
              {visibleAction && (
                <StrategyCard
                  key={visibleAction.action_id}
                  action={visibleAction}
                />
              )}
            </AnimatePresence>

            <AgentStatus />

            <motion.button
              className="transcript-toggle"
              onClick={() => setShowTranscript((s) => !s)}
              whileHover={{ scale: 1.01 }}
              whileTap={{ scale: 0.99 }}
            >
              {showTranscript ? "HIDE TRANSCRIPT" : "SHOW TRANSCRIPT"}
            </motion.button>

            <AnimatePresence>
              {showTranscript && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.25 }}
                  style={{ overflow: "hidden" }}
                >
                  <TranscriptFeed />
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
