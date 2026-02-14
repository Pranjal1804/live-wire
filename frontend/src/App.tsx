import React, { useCallback } from "react";
import { useAgentStream } from "./hooks/useAgentStream";
import { useTranscribeStream } from "./hooks/useTranscribeStream";
import { useAudioCapture } from "./hooks/useAudioCapture";
import { useCallStore } from "./stores/callStore";
import { HUD } from "./components/HUD";
import "./index.css";

export default function App() {
  const { startCall, endCall } = useAgentStream();
  const { transcribeWs } = useTranscribeStream();
  const setTalkRatio = useCallStore((s) => s.setTalkRatio);

  const onTalkRatioUpdate = useCallback(
    (micSecs: number, loopbackSecs: number) => {
      setTalkRatio(micSecs, loopbackSecs);
    },
    [setTalkRatio]
  );

  const { isCapturing, startCapture, stopCapture } = useAudioCapture({
    transcribeWs,
    onTalkRatioUpdate,
  });

  const handleStartCall = useCallback(async () => {
    await startCapture();
    startCall();
  }, [startCapture, startCall]);

  const handleEndCall = useCallback(async () => {
    endCall();
    await stopCapture();
  }, [endCall, stopCapture]);

  return <HUD onStartCall={handleStartCall} onEndCall={handleEndCall} />;
}
