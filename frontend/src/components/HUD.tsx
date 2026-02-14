import React, { useState, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useCallStore } from "../stores/callStore";
import { tauriAPI } from "../tauriAPI";
import { EmotionMeter } from "./EmotionMeter";
import { StrategyCard } from "./StrategyCard";
import { TranscriptFeed } from "./TranscriptFeed";
import { RiskAlert } from "./RiskAlert";
import { AgentStatus } from "./AgentStatus";
import { TalkListenRatio } from "./TalkListenRatio";
import { BANTChecklist } from "./BANTChecklist";
import { BattlecardPanel } from "./BattlecardPanel";

const tap = { type: "spring" as const, stiffness: 500, damping: 30 };

const panelVariants = {
  hidden: { opacity: 0, x: 40 },
  visible: {
    opacity: 1,
    x: 0,
    transition: {
      type: "spring",
      damping: 28,
      stiffness: 220,
      staggerChildren: 0.045,
      delayChildren: 0.06,
    },
  },
  exit: {
    opacity: 0,
    x: 40,
    transition: { duration: 0.2, ease: "easeIn" },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 8 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { type: "spring", damping: 26, stiffness: 300 },
  },
};

interface HUDProps {
  onStartCall: () => void;
  onEndCall: () => void;
}

export function HUD({ onStartCall, onEndCall }: HUDProps) {
  const {
    isConnected,
    isCallActive,
    riskScore,
    currentEmotion,
    activeActions,
    micSecs,
    loopbackSecs,
    bant,
    activeBattlecard,
    setBattlecard,
  } = useCallStore();

  const [collapsed, setCollapsed] = useState(false);
  const [showTranscript, setShowTranscript] = useState(false);

  const leaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleMouseEnter = useCallback(() => {
    if (leaveTimer.current) {
      clearTimeout(leaveTimer.current);
      leaveTimer.current = null;
    }
    tauriAPI.setClickthrough(false);
  }, []);

  const handleMouseLeave = useCallback(() => {
    leaveTimer.current = setTimeout(() => {
      tauriAPI.setClickthrough(true);
    }, 120);
  }, []);

  const visibleAction = activeActions.find((a) => !a.dismissed && a.priority === "critical")
    ?? activeActions.find((a) => !a.dismissed && a.priority === "high")
    ?? activeActions.find((a) => !a.dismissed && a.priority === "medium")
    ?? activeActions.find((a) => !a.dismissed);

  const handleClose = () => {
    tauriAPI.closeApp();
  };

  return (
    <div
      className="hud-root"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <motion.div
        className="status-bar"
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, ease: [0.25, 0.1, 0.25, 1] }}
      >
        <div className={`dot ${isConnected ? "dot-green" : "dot-red"}`} />
        <span className="status-label">
          {isConnected ? "MAESTRO ONLINE" : "OFFLINE"}
        </span>

        <motion.button
          className="collapse-btn"
          onClick={() => setCollapsed((c) => !c)}
          title="Toggle HUD"
          style={{ marginRight: 6 }}
          whileTap={{ scale: 0.92 }}
          transition={tap}
        >
          {collapsed ? "+" : "-"}
        </motion.button>

        <motion.button
          className="close-btn"
          onClick={handleClose}
          title="Close MAESTRO"
          whileTap={{ scale: 0.92 }}
          transition={tap}
        >
          X
        </motion.button>
      </motion.div>

      <AnimatePresence mode="wait">
        {!collapsed && (
          <motion.div
            className="hud-panel"
            variants={panelVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
          >
            <motion.div variants={itemVariants}>
              <RiskAlert riskScore={riskScore} emotion={currentEmotion} />
            </motion.div>

            <motion.div variants={itemVariants}>
              <EmotionMeter emotion={currentEmotion} />
            </motion.div>

            {isCallActive && (
              <motion.div variants={itemVariants}>
                <TalkListenRatio micSecs={micSecs} loopbackSecs={loopbackSecs} />
              </motion.div>
            )}

            {isCallActive && (
              <motion.div variants={itemVariants}>
                <BANTChecklist bant={bant} />
              </motion.div>
            )}

            <motion.div variants={itemVariants} className="call-controls">
              {!isCallActive ? (
                <motion.button
                  className="btn btn-start"
                  onClick={onStartCall}
                  whileTap={{ scale: 0.97 }}
                  transition={tap}
                >
                  START MONITORING
                </motion.button>
              ) : (
                <motion.button
                  className="btn btn-stop"
                  onClick={onEndCall}
                  whileTap={{ scale: 0.97 }}
                  transition={tap}
                >
                  END CALL
                </motion.button>
              )}
            </motion.div>

            <motion.div variants={itemVariants}>
              <BattlecardPanel
                battlecard={activeBattlecard}
                onDismiss={() => setBattlecard(null)}
              />
            </motion.div>

            <AnimatePresence mode="wait">
              {visibleAction && (
                <motion.div variants={itemVariants}>
                  <StrategyCard
                    key={visibleAction.action_id}
                    action={visibleAction}
                  />
                </motion.div>
              )}
            </AnimatePresence>

            <motion.div variants={itemVariants}>
              <AgentStatus />
            </motion.div>

            <motion.div variants={itemVariants}>
              <motion.button
                className="transcript-toggle"
                onClick={() => setShowTranscript((s) => !s)}
                whileTap={{ scale: 0.98 }}
                transition={tap}
              >
                {showTranscript ? "HIDE TRANSCRIPT" : "SHOW TRANSCRIPT"}
              </motion.button>
            </motion.div>

            <AnimatePresence>
              {showTranscript && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2, ease: [0.25, 0.1, 0.25, 1] }}
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
