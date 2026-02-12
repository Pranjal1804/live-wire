import asyncio
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

ws_manager = WebSocketManager()
session_store = SessionStore()
active_agents: Dict[str, MaestroAgent] = {}

global_pipeline: Optional[AudioPipeline] = None
global_pipeline_lock = asyncio.Lock()

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
    try:
        from models.model_manager import ModelManager
        await ModelManager.initialize()
        print("Models warm and ready")
    except Exception as e:
        print(f"Model warm-up partial: {e}")

app = FastAPI(
    title="MAESTRO Agentic Co-Pilot",
    description="Real-time sales call intelligence agent",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rest_router, prefix="/api")

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await ws_manager.connect(websocket, session_id)
    
    if session_id not in active_agents:
        active_agents[session_id] = MaestroAgent(
            session_id=session_id,
            ws_manager=ws_manager,
            session_store=session_store
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
        await ws_manager.send(session_id, {
            "type": "call_summary",
            "data": summary
        })
    elif msg_type == "feedback":
        await agent.record_feedback(
            action_id=data.get("action_id"),
            rating=data.get("rating"),
            outcome=data.get("outcome")
        )
    elif msg_type == "manual_query":
        result = await agent.query_knowledge_base(data.get("query", ""))
        await ws_manager.send(session_id, {
            "type": "kb_result",
            "data": result
        })

@app.get("/health")
async def health():
    return {
        "status": "alive",
        "active_sessions": ws_manager.active_count(),
        "models_loaded": True
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
