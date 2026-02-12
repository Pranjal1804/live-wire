from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class KBDocument(BaseModel):
    title: str
    content: str
    category: str = "general"

@router.post("/kb/add")
async def add_kb_document(doc: KBDocument):
    from tools.kb_search import KnowledgeBase
    kb = KnowledgeBase()
    await kb.add_document(doc.title, doc.content, doc.category)
    return {"status": "added", "title": doc.title}

@router.get("/kb/search")
async def search_kb(q: str):
    from tools.kb_search import KnowledgeBase
    kb = KnowledgeBase()
    results = await kb.search(q)
    return {"results": results}

@router.get("/sessions/{session_id}/history")
async def get_session_history(session_id: str):
    from main import session_store
    history = await session_store.get(f"history:{session_id}") or []
    return {"session_id": session_id, "calls": history}

@router.get("/health")
async def health():
    return {"status": "ok"}
