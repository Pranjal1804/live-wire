# MAESTRO — Agentic Sales Co-Pilot
## Complete Build Guide for EndeavourOS

---

## ⚠️ FEASIBILITY ANALYSIS (READ FIRST)

### Critical Audio Capture Problem (And the Solution)
The single biggest challenge on Linux: **capturing audio from Zoom/Teams/Meet**.

**Why VB-Cable won't work:** VB-Cable is Windows-only.

**Linux Solution Stack:**
```
Meeting App Audio → PulseAudio/PipeWire → Virtual Sink (pavucontrol) → Python capture
```

**Real-time word capture reality check:**
- Zoom/Teams/Meet encrypt and route audio through their own sinks
- You CAN capture via PulseAudio monitor sources (loopback)
- Whisper transcription latency on CPU: ~800ms-2s per chunk (acceptable for coaching)
- On GPU (even small): ~150-300ms (excellent)

**Recommendation:** Use `sounddevice` + PulseAudio monitor source.
No VB-Cable needed on Linux — PulseAudio does this natively.

---

## PROJECT STRUCTURE

```
maestro/
├── backend/
│   ├── main.py                    # FastAPI entry point
│   ├── requirements.txt
│   ├── agents/
│   │   ├── orchestrator.py        # Central ReAct agent brain
│   │   ├── strategy_engine.py     # Adaptive conversation strategy
│   │   └── learning_loop.py       # Outcome tracking & RLHF
│   ├── audio/
│   │   ├── capture.py             # PulseAudio capture (Linux native)
│   │   ├── vad.py                 # Silero VAD voice detection
│   │   └── pipeline.py            # Audio processing pipeline
│   ├── models/
│   │   ├── emotion.py             # Wav2Vec2 ONNX emotion detection
│   │   ├── transcription.py       # Faster-Whisper transcription
│   │   └── model_manager.py       # Model loading & caching
│   ├── tools/
│   │   ├── kb_search.py           # ChromaDB knowledge base RAG
│   │   ├── crm_logger.py          # CRM auto-logging
│   │   ├── email_drafter.py       # Post-call email generation
│   │   └── escalation.py          # Slack/supervisor alerts
│   ├── memory/
│   │   ├── session_store.py       # Redis session state
│   │   ├── vector_store.py        # ChromaDB vector memory
│   │   └── call_history.py        # Persistent call history
│   └── api/
│       ├── websocket_handler.py   # Real-time WS streaming
│       └── rest_routes.py         # REST endpoints
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── electron.config.js
│   ├── src/
│   │   ├── main.ts                # Electron main process
│   │   ├── preload.ts             # Electron preload bridge
│   │   ├── renderer.tsx           # React entry
│   │   ├── App.tsx                # Root component
│   │   ├── components/
│   │   │   ├── HUD.tsx            # Main heads-up display
│   │   │   ├── EmotionMeter.tsx   # Real-time emotion bars
│   │   │   ├── StrategyCard.tsx   # AI coaching cards
│   │   │   ├── TranscriptFeed.tsx # Live transcript scroll
│   │   │   ├── RiskAlert.tsx      # Call risk indicator
│   │   │   └── AgentStatus.tsx    # Agent action log
│   │   ├── hooks/
│   │   │   ├── useWebSocket.ts    # WS connection hook
│   │   │   └── useAgentStream.ts  # Agent event streaming
│   │   └── stores/
│   │       └── callStore.ts       # Zustand state store
│   └── public/
│       └── index.html
├── scripts/
│   ├── setup_endeavouros.sh       # Full system setup script
│   ├── setup_audio.sh             # PulseAudio virtual sink setup
│   ├── download_models.py         # Download AI models
│   └── test_audio_capture.py      # Test audio pipeline
├── config/
│   ├── agent_config.yaml          # Agent behavior config
│   └── prompts.yaml               # System prompts
└── .env.example
```

---

## PHASE 1: SYSTEM SETUP (EndeavourOS)

Run: `bash scripts/setup_endeavouros.sh`

---

## PHASE 2: AUDIO SETUP

Run: `bash scripts/setup_audio.sh`

In pavucontrol:
1. Go to "Recording" tab
2. Set your app to capture from "Monitor of [your output]"

---

## PHASE 3: BACKEND

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python ../scripts/download_models.py
uvicorn main:app --reload --port 8000
```

---

## PHASE 4: FRONTEND

```bash
cd frontend
npm install
npm run dev          # Development
npm run electron     # Full desktop app
npm run build        # Production build
```

---

## ENVIRONMENT VARIABLES

Copy `.env.example` to `.env` and fill:
- `GEMINI_API_KEY` — from Google AI Studio (free)
- `SLACK_BOT_TOKEN` — optional, for escalations
- `REDIS_URL` — default: redis://localhost:6379
