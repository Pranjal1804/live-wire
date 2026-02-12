import json
import os
import asyncio
from typing import Any, Optional

class SessionStore:
    def __init__(self):
        self._redis = None
        self._storage_file = "./data/session_data.json"
        
        os.makedirs("./data", exist_ok=True)
        
        if os.path.exists(self._storage_file):
            try:
                with open(self._storage_file, "r") as f:
                    self._fallback = json.load(f)
            except Exception:
                self._fallback = {}
        else:
            self._fallback = {}
    
    async def _get_redis(self):
        if self._redis is None:
            try:
                import redis.asyncio as aioredis
                self._redis = aioredis.from_url(
                    os.environ.get("REDIS_URL", "redis://localhost:6379"),
                    decode_responses=True
                )
                await self._redis.ping()
            except Exception as e:
                print(f"Redis unavailable: {e}. Using in-memory store.")
                self._redis = None
        return self._redis
    
    async def set(self, key: str, value: Any, ttl: int = 3600):
        r = await self._get_redis()
        serialized = json.dumps(value)
        if r:
            await r.set(key, serialized, ex=ttl)
        else:
            self._fallback[key] = serialized
            self._save_local()
            
    def _save_local(self):
        try:
            with open(self._storage_file, "w") as f:
                json.dump(self._fallback, f)
        except Exception as e:
            print(f"Failed to save local storage: {e}")
    
    async def get(self, key: str) -> Optional[Any]:
        r = await self._get_redis()
        if r:
            val = await r.get(key)
        else:
            val = self._fallback.get(key)
        return json.loads(val) if val else None
    
    async def store_feedback(self, session_id: str, feedback: dict):
        key = f"feedback:{session_id}"
        existing = await self.get(key) or []
        existing.append(feedback)
        await self.set(key, existing)

    async def store_call(self, session_id: str, summary: dict):
        key = f"history:{session_id}"
        existing = await self.get(key) or []
        existing.append({
            "timestamp": summary.get("timestamp") or json.dumps(summary),
            **summary
        })
        await self.set(key, existing)
