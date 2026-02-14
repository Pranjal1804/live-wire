import asyncio
import json
import os
from typing import Dict, Optional
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from api.websocket_handler import WebSocketManager
from api.rest_routes import router as rest_router
from agents.orchestrator import MaestroAgent
from audio.pipeline import AudioPipeline
from memory.session_store import SessionStore
from models.parakeet import get_model, decode_audio_chunk, transcribe
from tools.battlecards import scan_transcript

ws_manager = WebSocketManager()
session_store = SessionStore()
active_agents: Dict[str, MaestroAgent] = {}

global_pipeline: Optional[AudioPipeline] = None
global_pipeline_lock = asyncio.Lock()


# ── BANT prompt template for LLM router ──
BANT_SYSTEM_PROMPT = """You are analyzing a sales call transcript. Extract any BANT qualification signals.
Return ONLY valid JSON with this exact structure (no markdown, no explanation):
{"bant_updates": {"budget": true/false, "authority": true/false, "need": true/false, "timeline": true/false}}
Set a field to true ONLY if the transcript contains clear evidence:
- budget: prospect discussed pricing, budget, cost, affordability, or willingness to pay
- authority: prospect is the decision-maker or confirmed they can approve the purchase
- need: prospect described a pain point, requirement, or problem our product solves
- timeline: prospect mentioned a deadline, urgency, implementation date, or buying timeframe
If no evidence for a field, set it to false."""


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("MAESTRO Agent starting up...")
    asyncio.create_task(warm_up_models())
    yield
    print("MAESTRO shutting down...")
    if global_pipeline:
        await global_pipeline.stop()
    await ws_manager.broadcast({"type": "shutdown"})


async def warm_up_models():
    """Warm up transcription model (Parakeet or Whisper fallback)."""
    try:
        model = await get_model()
        if model is not None:
            print("Transcription model warm and ready")
        else:
            print("WARNING: No transcription model available")
    except Exception as e:
        print(f"Model warm-up error: {e}")

    # Also warm existing emotion model if present
    try:
        from models.model_manager import ModelManager
        await ModelManager.initialize()
        print("Emotion model ready")
    except Exception as e:
        print(f"Emotion model warm-up partial: {e}")


app = FastAPI(
    title="MAESTRO Agentic Co-Pilot",
    description="Real-time sales call intelligence agent",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rest_router, prefix="/api")


# ── New: Transcription WebSocket endpoint ──
# Receives VAD-sliced base64 audio chunks from the Tauri frontend,
# transcribes them with Parakeet-TDT (or Whisper fallback),
# scans for competitor keywords, and returns structured JSON.

@app.websocket("/ws/transcribe")
async def transcribe_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("Transcribe WS connected")

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                chunk = json.loads(raw)
            except Exception:
                await websocket.send_json({"error": "Invalid JSON"})
                continue

            audio_b64 = chunk.get("audio_b64")
            source = chunk.get("source", "unknown")

            if not audio_b64:
                await websocket.send_json({"error": "Missing audio_b64 field"})
                continue

            # Decode base64 PCM to float32 numpy array
            try:
                audio = decode_audio_chunk(audio_b64)
            except Exception as e:
                await websocket.send_json({"error": f"Audio decode failed: {e}"})
                continue

            # Skip very short chunks (< 200ms)
            if len(audio) < 3200:
                continue

            # Transcribe with Parakeet-TDT (GPU) or Whisper (CPU fallback)
            result = await transcribe(audio, source=source)

            text = result.get("text", "")
            if not text.strip():
                continue

            # Keyword battlecard scan (instant, no LLM)
            battlecard = scan_transcript(text)

            response = {
                "type": "transcript",
                "text": text,
                "words": result.get("words", []),
                "source": source,
                "duration_secs": result.get("duration_secs", 0),
                "latency_ms": result.get("latency_ms", 0),
                "backend": result.get("backend", "unknown"),
            }

            if battlecard:
                response["battlecard"] = battlecard

            await websocket.send_json(response)

    except WebSocketDisconnect:
        print("Transcribe WS disconnected")
    except Exception as e:
        print(f"Transcribe WS error: {e}")


# ── Existing: Agent/orchestrator WebSocket endpoint ──

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await ws_manager.connect(websocket, session_id)

    if session_id not in active_agents:
        active_agents[session_id] = MaestroAgent(
            session_id=session_id,
            ws_manager=ws_manager,
            session_store=session_store,
        )

    agent = active_agents[session_id]

    global global_pipeline

    async with global_pipeline_lock:
        if global_pipeline:
            print("Stopping existing audio pipeline to release device...")
            await global_pipeline.stop()
            await asyncio.sleep(0.5)

        try:
            print(f"Initializing audio pipeline for session {session_id}")
            global_pipeline = AudioPipeline(agent=agent, session_id=session_id)
            asyncio.create_task(global_pipeline.start())
        except Exception as e:
            print(f"Failed to start pipeline: {e}")

    try:
        while True:
            data = await websocket.receive_json()
            await handle_frontend_message(data, agent, session_id)

    except WebSocketDisconnect:
        await ws_manager.disconnect(session_id)
        print(f"Session {session_id} disconnected")
    except Exception as e:
        print(f"WebSocket error in {session_id}: {e}")
        await ws_manager.disconnect(session_id)


async def handle_frontend_message(data: dict, agent: MaestroAgent, session_id: str):
    msg_type = data.get("type")

    if msg_type == "call_start":
        await agent.start_call(data.get("call_metadata", {}))
    elif msg_type == "call_end":
        summary = await agent.end_call()
        await ws_manager.send(
            session_id, {"type": "call_summary", "data": summary}
        )
    elif msg_type == "feedback":
        await agent.record_feedback(
            action_id=data.get("action_id"),
            rating=data.get("rating"),
            outcome=data.get("outcome"),
        )
    elif msg_type == "manual_query":
        result = await agent.query_knowledge_base(data.get("query", ""))
        await ws_manager.send(
            session_id, {"type": "kb_result", "data": result}
        )


@app.get("/health")
async def health():
    from models.parakeet import _backend

    return {
        "status": "alive",
        "active_sessions": ws_manager.active_count(),
        "transcription_backend": _backend or "loading",
    }


# ── BANT analysis endpoint (called by LLM router or frontend) ──

@app.post("/api/bant/analyze")
async def analyze_bant(payload: dict):
    """
    Accepts {"transcript": "..."} and returns BANT qualification signals.
    This is a helper for the LLM router -- call it with recent transcript
    text and it returns the structured JSON for auto-ticking BANT boxes.
    """
    return {
        "bant_prompt": BANT_SYSTEM_PROMPT,
        "transcript": payload.get("transcript", ""),
        "instruction": "Send this prompt + transcript to your LLM. "
        "The LLM should return: "
        '{"bant_updates": {"budget": bool, "authority": bool, "need": bool, "timeline": bool}}',
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
