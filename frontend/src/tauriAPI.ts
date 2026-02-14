import { invoke } from "@tauri-apps/api/core";

export interface AudioChunk {
  audio_b64: string;
  source: "mic" | "loopback";
  duration_secs: number;
  sample_count: number;
}

export interface AudioDevices {
  input: string[];
  output: string[];
}

export const tauriAPI = {
  // ── Window commands ──
  setClickthrough: (enabled: boolean) =>
    invoke("set_clickthrough", { ignore: enabled }),

  setAlwaysOnTop: (enabled: boolean) =>
    invoke("set_always_on_top", { enabled }),

  resizeWindow: (w: number, h: number) =>
    invoke("resize_window", { width: w, height: h }),

  closeApp: () => invoke("close_app"),

  // ── Audio capture commands ──
  startAudioCapture: () => invoke<string>("start_audio_capture"),

  stopAudioCapture: () => invoke<string>("stop_audio_capture"),

  /** Drains all pending VAD-sliced audio chunks from the Rust side. */
  pollAudioChunks: () => invoke<AudioChunk[]>("poll_audio_chunks"),

  /** Returns [mic_secs, loopback_secs] for talk-to-listen ratio. */
  getTalkRatio: () => invoke<[number, number]>("get_talk_ratio"),

  listAudioDevices: () => invoke<AudioDevices>("list_audio_devices"),
};
