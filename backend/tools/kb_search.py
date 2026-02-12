import asyncio
import os
from typing import List, Optional
import chromadb
from chromadb.config import Settings

class KnowledgeBase:
    _client = None
    _collection = None
    
    def __init__(self):
        if KnowledgeBase._client is None:
            KnowledgeBase._client = chromadb.PersistentClient(
                path="./data/chroma_kb",
                settings=Settings(anonymized_telemetry=False)
            )
        
        if KnowledgeBase._collection is None:
            KnowledgeBase._collection = KnowledgeBase._client.get_or_create_collection(
                name="maestro_kb",
                metadata={"hnsw:space": "cosine"}
            )
            
            if KnowledgeBase._collection.count() == 0:
                self._seed_default_knowledge()
    
    def _seed_default_knowledge(self):
        default_docs = [
            {
                "id": "refund_policy",
                "title": "Refund Policy",
                "content": "Full refunds available within 30 days of purchase. Partial refunds (50%) available 30-60 days. No refunds after 60 days except for defective products. Process: collect order number, verify purchase, initiate refund within 3-5 business days.",
                "category": "policy"
            },
            {
                "id": "cancel_retention",
                "title": "Cancellation Retention Script",
                "content": "When customer wants to cancel: 1) Acknowledge their concern, 2) Ask 'Can I ask what's prompting you to cancel today?' 3) If price: offer 20% discount for 3 months 4) If features: schedule demo of features they're missing 5) If competitor: ask what they're looking for that we don't offer 6) Last resort: offer pause subscription for 1 month",
                "category": "script"
            },
            {
                "id": "angry_customer",
                "title": "De-escalation Techniques",
                "content": "For angry customers: 1) Let them finish speaking completely 2) Validate: 'I completely understand why you're frustrated' 3) Apologize for experience (not for policy) 4) Focus on what you CAN do, not can't 5) Give them a choice between 2 options 6) Follow up within 24h. NEVER: argue, interrupt, say 'that's our policy', transfer without warning.",
                "category": "script"
            },
            {
                "id": "pricing_objection",
                "title": "Handling Price Objections",
                "content": "Price objection scripts: 1) 'What would make this feel like good value to you?' 2) 'Let me show you the ROI our customers typically see...' 3) Offer annual billing (saves 20%) 4) Compare cost-per-day ('That's less than a coffee a day') 5) Highlight specific features they've mentioned needing. Discounts available: 10% for annual, 15% for referrals, 20% retention offer.",
                "category": "script"
            },
            {
                "id": "tech_support_escalation",
                "title": "When to Escalate to Tier 2",
                "content": "Escalate to Tier 2 when: bug confirmed for 3+ users, data loss or corruption, security concerns, issue unresolved after 15 min, customer explicitly requests manager, account value > $500/month. Escalation phrase: 'I want to make sure you get the fastest resolution. Let me connect you with our specialist team who can resolve this immediately.'",
                "category": "policy"
            }
        ]
        
        for doc in default_docs:
            self._collection.add(
                documents=[doc["content"]],
                metadatas=[{"title": doc["title"], "category": doc["category"]}],
                ids=[doc["id"]]
            )
        
        print(f"Knowledge base seeded with {len(default_docs)} documents")
    
    async def search(self, query: str, n_results: int = 3) -> List[dict]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._search_sync, query, n_results)
    
    def _search_sync(self, query: str, n_results: int) -> List[dict]:
        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=min(n_results, self._collection.count())
            )
            
            documents = results.get("documents", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]
            
            return [
                {
                    "content": doc,
                    "title": meta.get("title", ""),
                    "category": meta.get("category", ""),
                    "relevance": round(1 - dist, 3)
                }
                for doc, meta, dist in zip(documents, metadatas, distances)
                if (1 - dist) > 0.3
            ]
            
        except Exception as e:
            print(f"KB search error: {e}")
            return []
    
    async def add_document(self, title: str, content: str, category: str = "general"):
        import hashlib
        doc_id = hashlib.md5(f"{title}{content}".encode()).hexdigest()[:12]
        
        self._collection.upsert(
            documents=[content],
            metadatas=[{"title": title, "category": category}],
            ids=[doc_id]
        )
