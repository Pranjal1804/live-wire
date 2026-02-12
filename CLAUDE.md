# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MAESTRO is an AI-powered real-time sales call coaching platform. It captures audio from calls (via PipeWire/PulseAudio virtual sinks), transcribes and analyzes it in real time, then displays coaching suggestions through a transparent Tauri v2 overlay (HUD). Target platform is EndeavourOS/Arch Linux.

## Commands

### Backend (from project root)
```bash
source backend/venv/bin/activate
uvicorn backend.main:app --reload --port 8000       # Dev server
# Or from backend/:
cd backend && source venv/bin/activate && uvicorn main:app --reload --port 8000
```

### Frontend (from frontend/)
```bash
pnpm dev                 # Vite dev server on port 5173
pnpm tauri dev           # Vite + Tauri window (main dev workflow)
pnpm tauri build         # Package with Tauri bundler (deb, appimage)
pnpm build               # TypeScript check + Vite production build
```

### Setup Scripts (from project root)
```bash
bash scripts/setup_endeavouros.sh       # System deps (pacman + yay)
bash scripts/setup_audio.sh             # Create PipeWire virtual audio sink
python scripts/download_models.py       # Download AI models (~400MB)
python scripts/test_audio_capture.py    # Verify audio capture works
```

There is no test suite, linter config, or CI/CD pipeline.

## Architecture

### Data Flow

```
Audio Device (PipeWire monitor source)
  -> AudioCapture (sounddevice, 16kHz mono)
    -> VAD (Silero, with energy-based fallback)
      -> Parallel: Whisper transcription + Wav2Vec2 emotion detection
        -> MaestroAgent.perceive() stores transcript + emotion
          -> _decide_and_act(): dual-path decision
            |-- Instant rules (churn keywords, anger threshold)
            |-- Strategic: Gemini LLM consultation (if risk > 0.4 or keywords detected)
              -> Actions broadcast via WebSocket to Tauri HUD
```

### Backend (`backend/`, Python, FastAPI, async)

- **`main.py`** -- FastAPI app entry point. Lifespan event warms up models. WebSocket endpoint `/ws/{session_id}` creates per-session agent + audio pipeline. REST routes for KB and session history.
- **`agents/orchestrator.py`** -- `MaestroAgent`: the decision engine. `perceive()` ingests transcripts/emotions, `_decide_and_act()` runs dual-path evaluation (instant regex rules vs. Gemini LLM), manages 8-second cooldown between interventions, exponential moving average for risk score (`0.7 * old + 0.3 * new`).
- **`audio/pipeline.py`** -- `AudioPipeline`: orchestrates capture -> VAD -> transcription -> emotion in 2-second chunks with 0.3s overlap. Global asyncio.Lock prevents concurrent device access.
- **`audio/capture.py`** -- SoundDevice wrapper. Resamples on-the-fly if native rate != 16kHz (scipy).
- **`audio/vad.py`** -- Silero VAD wrapper with energy-based fallback.
- **`models/model_manager.py`** -- Singleton loaders for Faster-Whisper, Wav2Vec2 emotion model, Silero VAD. CPU by default, GPU-ready.
- **`tools/kb_search.py`** -- ChromaDB vector store for RAG. 5 seed documents (refund policy, de-escalation, etc.). Relevance threshold: 0.3 cosine similarity.
- **`tools/integrations.py`** -- Webhook-based integrations (Slack, CRM, email, LinkedIn). All optional, configured via env vars.
- **`memory/session_store.py`** -- Redis-backed session persistence with JSON file fallback.

### Frontend (`frontend/`, React 18, TypeScript, Tauri v2)

- **`src-tauri/src/lib.rs`** -- Tauri Rust backend. Creates 380px-wide transparent overlay window, always-on-top, positioned at right screen edge. Exposes 4 commands: `set_clickthrough`, `close_app`, `set_always_on_top`, `resize_window`.
- **`src-tauri/tauri.conf.json`** -- Tauri window config (transparent, frameless, always-on-top, skip-taskbar). CSP allows WebSocket to backend.
- **`src-tauri/capabilities/default.json`** -- Tauri v2 permission grants for window manipulation and process exit.
- **`src/tauriAPI.ts`** -- TypeScript wrapper around Tauri `invoke()` calls (replaces Electron preload bridge).
- **`src/stores/callStore.ts`** -- Zustand store. Single source of truth for call state, transcript, risk, emotions, suggestions.
- **`src/hooks/useAgentStream.ts`** -- WebSocket connection to backend. Handles message types: transcript, action, emotion, call_summary.
- **`src/components/HUD.tsx`** -- Main overlay component. Start/stop monitoring, risk meter, coaching cards.
- **`src/components/`** -- RiskAlert, StrategyCard, EmotionMeter, TranscriptFeed, AgentStatus. Framer Motion animations.

### Configuration

- **`config/agent_config.yaml`** -- All tunable parameters: risk thresholds, Whisper model selection, VAD sensitivity, audio chunk size, Gemini model/temperature.
- **`config/audio_device.txt`** -- Auto-populated by setup scripts. Selected PipeWire/PulseAudio source.
- **`.env`** -- `GEMINI_API_KEY` (required), optional: `SLACK_WEBHOOK_URL`, `CRM_WEBHOOK_URL`, `REDIS_URL`.

## Key Design Decisions

- **Per-session isolation**: each WebSocket connection gets its own `MaestroAgent` instance and exclusive audio device lock. No shared mutable state between sessions.
- **Dual-path decision making**: instant regex/threshold rules fire immediately for high-confidence triggers (churn keywords, anger > 0.7); Gemini LLM consulted for nuanced situations. This keeps latency low for obvious cases.
- **Cooldown system**: 8-second minimum between coaching suggestions to prevent agent spam. Urgency level can override cooldown.
- **Gemini JSON parsing**: responses are cleaned with regex (strip markdown backticks, fix trailing commas, multiple extraction fallbacks). Expect Gemini to sometimes return malformed JSON.
- **Audio overlap**: 300ms overlap between 2-second chunks prevents words being cut at boundaries. `condition_on_previous_text=True` in Whisper maintains cross-chunk context.
- **Wayland compatibility**: Tauri uses WebKitGTK which has better Wayland support than Electron, but transparent overlays may still require X11 or XWayland on some compositors.
