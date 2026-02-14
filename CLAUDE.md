# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MAESTRO is an AI-powered real-time sales call coaching platform. It captures audio directly from OS audio APIs (no virtual cables), transcribes with NVIDIA Parakeet-TDT on GPU, and displays coaching suggestions through a transparent Tauri v2 overlay (HUD). Target platform is Linux (any distribution with PipeWire or PulseAudio). GPU transcription requires an NVIDIA GPU (tested on RTX 4060); CPU fallback (Faster-Whisper) works without one.

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
bash scripts/setup_linux.sh              # System deps (auto-detects distro)
bash scripts/setup_audio.sh             # Create PipeWire virtual audio sink
python scripts/download_models.py       # Download AI models (~400MB)
python scripts/test_audio_capture.py    # Verify audio capture works
```

There is no test suite, linter config, or CI/CD pipeline.

## Architecture

### Data Flow

```
OS Audio APIs (cpal: WASAPI/CoreAudio/PipeWire)
  -> Rust AudioCapture (mic + loopback, dual stream)
    -> Energy-based VAD (silence slicing in Rust)
      -> base64 PCM chunks via WebSocket /ws/transcribe
        -> Parakeet-TDT GPU transcription (word timestamps + punctuation)
          -> Keyword battlecard scan (instant regex, no LLM)
          -> MaestroAgent.perceive() for coaching decisions
            |-- Instant rules (churn keywords, anger threshold)
            |-- Strategic: Gemini LLM (if risk > 0.4)
              -> Actions broadcast via WebSocket to Tauri HUD

Parallel: Talk-to-listen ratio tracked in Rust, polled by React every 1s
Parallel: BANT auto-tick from LLM structured JSON output
```

### Backend (`backend/`, Python, FastAPI, async)

- **`main.py`** -- FastAPI app. Two WebSocket endpoints: `/ws/transcribe` (audio chunks in, transcripts out) and `/ws/{session_id}` (agent orchestration). REST routes for KB, BANT analysis, session history. Lifespan warms Parakeet model.
- **`models/parakeet.py`** -- Parakeet-TDT transcription engine. Loads `nvidia/parakeet-tdt-0.6b-v3` via NeMo on GPU, falls back to Faster-Whisper on CPU. Async singleton with word-level timestamps. Decodes base64 PCM from frontend.
- **`tools/battlecards.py`** -- Compiled regex matcher for competitor names (Salesforce, HubSpot, Gong, Chorus, Outreach). Returns pre-built battlecard arrays instantly without LLM. Add competitors to the `BATTLECARDS` dict.
- **`agents/orchestrator.py`** -- `MaestroAgent`: dual-path decision engine. `perceive()` ingests transcripts/emotions, `_decide_and_act()` runs instant rules vs. Gemini LLM, 8-second cooldown, EMA risk score.
- **`audio/pipeline.py`** -- Legacy `AudioPipeline` (Python sounddevice). Being replaced by Rust cpal capture in Tauri. Kept for backward compatibility.
- **`models/model_manager.py`** -- Legacy Faster-Whisper + Wav2Vec2 emotion loaders. Emotion model still used; transcription migrating to `parakeet.py`.
- **`tools/kb_search.py`** -- ChromaDB vector store for RAG. 5 seed documents. 0.3 cosine similarity threshold.
- **`tools/integrations.py`** -- Webhook-based integrations (Slack, CRM, email, LinkedIn). Optional.
- **`memory/session_store.py`** -- Redis-backed session persistence with JSON file fallback.

### Frontend (`frontend/`, React 18, TypeScript, Tauri v2)

- **`src-tauri/src/audio.rs`** -- Rust audio capture using cpal. Dual-stream: default input (mic) + loopback (WASAPI output / PipeWire monitor). Energy-based VAD slices speech into chunks, converts to 16kHz mono, base64-encodes. Platform-aware loopback device finder.
- **`src-tauri/src/lib.rs`** -- Tauri commands: 4 window commands + 5 audio commands (`start_audio_capture`, `stop_audio_capture`, `poll_audio_chunks`, `get_talk_ratio`, `list_audio_devices`). Setup hook positions overlay at right screen edge.
- **`src-tauri/tauri.conf.json`** -- Tauri window config (transparent, frameless, always-on-top, skip-taskbar). CSP allows `ws://localhost:8000`.
- **`src/tauriAPI.ts`** -- TypeScript wrapper around all Tauri `invoke()` calls with typed interfaces.
- **`src/stores/callStore.ts`** -- Zustand store. Call state, transcript, risk, emotions, actions, talk ratio, BANT state, active battlecard.
- **`src/hooks/useAgentStream.ts`** -- WebSocket to `/ws/{session_id}` for agent orchestration messages.
- **`src/hooks/useTranscribeStream.ts`** -- WebSocket to `/ws/transcribe` for real-time transcription results + battlecard triggers.
- **`src/hooks/useAudioCapture.ts`** -- Polls Rust for VAD-sliced audio chunks (250ms interval), forwards to transcribe WS. Polls talk ratio (1s interval).
- **`src/components/HUD.tsx`** -- Main overlay. Risk meter, emotion, call controls, strategy cards, transcript toggle.
- **`src/components/TalkListenRatio.tsx`** -- Progress bar showing mic vs. loopback speaking time ratio.
- **`src/components/BANTChecklist.tsx`** -- Budget/Authority/Need/Timeline checklist, auto-ticked from LLM JSON.
- **`src/components/BattlecardPanel.tsx`** -- Competitor battlecard display (talking points, weaknesses, counter-objections).
- **`src/components/`** -- RiskAlert, StrategyCard, EmotionMeter, TranscriptFeed, AgentStatus. Framer Motion animations.

### Configuration

- **`config/agent_config.yaml`** -- All tunable parameters: risk thresholds, Whisper model selection, VAD sensitivity, audio chunk size, Gemini model/temperature.
- **`config/audio_device.txt`** -- Auto-populated by setup scripts. Selected PipeWire/PulseAudio source.
- **`.env`** -- `GEMINI_API_KEY` (required), optional: `SLACK_WEBHOOK_URL`, `CRM_WEBHOOK_URL`, `REDIS_URL`.

## Key Design Decisions

- **No virtual audio cables**: Audio capture moved to Rust (cpal) in the Tauri process, hooking OS native APIs directly. WASAPI loopback on Windows, PipeWire monitor sources on Linux, CoreAudio on macOS.
- **Client-side VAD**: Energy-based voice activity detection runs in Rust. Only speech chunks are sent to the backend -- dead air is never transmitted. Reduces bandwidth and GPU waste.
- **Parakeet-TDT over Whisper**: nvidia/parakeet-tdt-0.6b-v3 runs on the RTX 4060 for sub-300ms inference. Token-and-Duration Transducer predicts word timestamps natively (no forced alignment). Falls back to Faster-Whisper CPU if NeMo is not installed.
- **Instant battlecards**: Compiled regex scans every transcript for competitor mentions before the LLM sees it. Battlecard data is pre-built in `tools/battlecards.py` -- zero latency.
- **BANT auto-tick**: LLM router sends transcript to a structured prompt that returns `{"bant_updates": {...}}` JSON. Frontend Zustand store merges updates incrementally.
- **Dual WebSocket architecture**: `/ws/transcribe` handles audio->text (stateless, high-throughput). `/ws/{session_id}` handles agent orchestration (stateful, per-session). Separation prevents transcription latency from blocking coaching decisions.
- **Per-session isolation**: each agent WebSocket gets its own `MaestroAgent` instance. No shared mutable state between sessions.
- **Cooldown system**: 8-second minimum between coaching suggestions. Urgency level can override.
- **Wayland compatibility**: Tauri uses WebKitGTK which has better Wayland support than Electron, but transparent overlays may still require X11 or XWayland on some compositors.
