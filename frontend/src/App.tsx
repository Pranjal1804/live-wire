import React from "react";
import { useAgentStream } from "./hooks/useAgentStream";
import { HUD } from "./components/HUD";
import "./index.css";

export default function App() {
  const { startCall, endCall } = useAgentStream();

  return <HUD onStartCall={startCall} onEndCall={endCall} />;
}
