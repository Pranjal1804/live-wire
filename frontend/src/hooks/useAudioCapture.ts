import { useEffect, useRef, useCallback, useState } from "react";
import { tauriAPI, AudioChunk } from "../tauriAPI";

const POLL_INTERVAL_MS = 250; // poll Rust for VAD-sliced chunks every 250ms
const TALK_RATIO_INTERVAL_MS = 1000; // update talk ratio every second

interface UseAudioCaptureOptions {
  /** WebSocket to send audio chunks to the backend transcription service. */
  transcribeWs: WebSocket | null;
  /** Called whenever the talk ratio updates. */
  onTalkRatioUpdate?: (micSecs: number, loopbackSecs: number) => void;
}

export function useAudioCapture({
  transcribeWs,
  onTalkRatioUpdate,
}: UseAudioCaptureOptions) {
  const [isCapturing, setIsCapturing] = useState(false);
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const ratioTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const startCapture = useCallback(async () => {
    try {
      await tauriAPI.startAudioCapture();
      setIsCapturing(true);
    } catch (err) {
      console.error("Failed to start audio capture:", err);
    }
  }, []);

  const stopCapture = useCallback(async () => {
    try {
      await tauriAPI.stopAudioCapture();
    } catch (err) {
      console.error("Failed to stop audio capture:", err);
    }
    setIsCapturing(false);
  }, []);

  // Poll Rust for VAD-sliced chunks and forward to backend
  useEffect(() => {
    if (!isCapturing) {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
      return;
    }

    pollTimerRef.current = setInterval(async () => {
      try {
        const chunks: AudioChunk[] = await tauriAPI.pollAudioChunks();
        if (
          chunks.length > 0 &&
          transcribeWs &&
          transcribeWs.readyState === WebSocket.OPEN
        ) {
          for (const chunk of chunks) {
            transcribeWs.send(JSON.stringify(chunk));
          }
        }
      } catch (err) {
        console.error("Audio poll error:", err);
      }
    }, POLL_INTERVAL_MS);

    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    };
  }, [isCapturing, transcribeWs]);

  // Poll talk ratio
  useEffect(() => {
    if (!isCapturing || !onTalkRatioUpdate) {
      if (ratioTimerRef.current) {
        clearInterval(ratioTimerRef.current);
        ratioTimerRef.current = null;
      }
      return;
    }

    ratioTimerRef.current = setInterval(async () => {
      try {
        const [micSecs, loopbackSecs] = await tauriAPI.getTalkRatio();
        onTalkRatioUpdate(micSecs, loopbackSecs);
      } catch (err) {
        console.error("Talk ratio poll error:", err);
      }
    }, TALK_RATIO_INTERVAL_MS);

    return () => {
      if (ratioTimerRef.current) {
        clearInterval(ratioTimerRef.current);
        ratioTimerRef.current = null;
      }
    };
  }, [isCapturing, onTalkRatioUpdate]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (isCapturing) {
        tauriAPI.stopAudioCapture().catch(() => {});
      }
    };
  }, []);

  return { isCapturing, startCapture, stopCapture };
}
