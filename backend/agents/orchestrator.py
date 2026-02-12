import asyncio
import json
import os
import uuid
import re
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional, Dict
from tools.integrations import IntegrationManager
import google.generativeai as genai

if TYPE_CHECKING:
    from api.websocket_handler import WebSocketManager
    from memory.session_store import SessionStore

genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))

EMOTION_RISK_MAP = {
    "angry": 0.9,
    "disgusted": 0.8,
    "fearful": 0.7,
    "sad": 0.6,
    "surprised": 0.3,
    "happy": 0.1,
    "neutral": 0.2,
}

class ActionType:
    SHOW_PROMPT = "show_prompt"
    SHOW_KB_RESULT = "show_kb_result"
    SHOW_RISK_ALERT = "show_risk_alert"
    ESCALATE = "escalate"
    DRAFT_EMAIL = "draft_email"
    UPDATE_CRM = "update_crm"
    SEARCH_LINKEDIN = "search_linkedin"
    SCHEDULE_FOLLOWUP = "schedule_call"
    NONE = "none"

class MaestroAgent:
    def __init__(self, session_id: str, ws_manager: "WebSocketManager", 
                 session_store: "SessionStore"):
        self.session_id = session_id
        self.ws_manager = ws_manager
        self.session_store = session_store
        
        self.gemini = genai.GenerativeModel(
            model_name=os.environ.get("GEMINI_MODEL", "gemini-1.5-flash"),
            generation_config={
                "temperature": 0.4,
                "max_output_tokens": 2048,
            }
        )
        
        self.call_id = str(uuid.uuid4())
        self.call_start_time = None
        self.call_transcript = []
        self.emotion_timeline = []
        self.actions_taken = []
        
        self._last_intervention_time = 0
        self._intervention_cooldown = 8.0
        self._last_kb_query = ""
        self.risk_score = 0.0
        self.integrations = IntegrationManager()
        
        print(f"Agent initialized for session {session_id}")
    
    async def start_call(self, metadata: dict = {}):
        self.call_start_time = datetime.now()
        self.call_id = str(uuid.uuid4())
        self.call_transcript = []
        self.emotion_timeline = []
        self.actions_taken = []
        self.risk_score = 0.0
        
        print(f"Call started: {self.call_id}")
        
        await self.ws_manager.send(self.session_id, {
            "type": "call_started",
            "call_id": self.call_id,
            "timestamp": datetime.now().isoformat()
        })
    
    async def perceive(self, perception: dict):
        transcript = perception.get("transcript", "")
        emotion = perception.get("emotion", {})
        
        if not transcript:
            return
        
        self.call_transcript.append({
            "text": transcript,
            "emotion": emotion,
            "timestamp": datetime.now().isoformat()
        })
        self.emotion_timeline.append(emotion)
        
        if len(self.call_transcript) > 50:
            self.call_transcript.pop(0)
        
        new_risk = emotion.get("risk_level", 0)
        self.risk_score = (self.risk_score * 0.7) + (new_risk * 0.3)
        
        await self.ws_manager.send(self.session_id, {
            "type": "perception_update",
            "data": {
                "transcript": transcript,
                "emotion": emotion,
                "risk_score": round(self.risk_score, 3),
                "timestamp": datetime.now().isoformat()
            }
        })
        
        await self._decide_and_act(perception)
    
    async def _decide_and_act(self, perception: dict):
        emotion = perception.get("emotion", {})
        transcript = perception.get("transcript", "")
        
        instant_action = self._instant_rules(emotion, transcript)
        if instant_action:
            await self._execute_action(instant_action)
            return
        
        now = asyncio.get_event_loop().time()
        time_since_last = now - self._last_intervention_time
        
        should_consult_gemini = (
            time_since_last >= self._intervention_cooldown and
            (
                self.risk_score > 0.4 or
                self._has_keyword_trigger(transcript) or
                len(self.call_transcript) % 10 == 0
            )
        )
        
        if should_consult_gemini:
            asyncio.create_task(self._strategic_decision(perception))
    
    def _instant_rules(self, emotion: dict, transcript: str) -> Optional[dict]:
        label = emotion.get("label", "neutral")
        risk = emotion.get("risk_level", 0)
        transcript_lower = transcript.lower()
        
        if risk > 0.85 or label == "angry" and emotion.get("score", 0) > 0.85:
            if self.risk_score > 0.75:
                return {
                    "type": ActionType.SHOW_RISK_ALERT,
                    "severity": "critical",
                    "message": "Critical: Customer extremely upset. Consider escalating.",
                    "suggestion": "Say: 'I want to make sure we resolve this fully for you. Let me get a specialist involved.'"
                }
        
        churn_words = ["cancel", "cancelling", "leaving", "switch", "competitor", 
                      "done with", "terrible", "worst", "never again"]
        if any(w in transcript_lower for w in churn_words):
            return {
                "type": ActionType.SHOW_RISK_ALERT,
                "severity": "high",
                "message": "Churn risk detected",
                "suggestion": "Try: 'I completely understand. Before you go, can I see what I can do for you personally?'"
            }
        
        price_words = ["expensive", "too much", "cheaper", "discount", "price", "cost"]
        if any(w in transcript_lower for w in price_words):
            return {
                "type": ActionType.SHOW_PROMPT,
                "priority": "medium",
                "category": "objection_handling",
                "message": "Price Objection Detected",
                "suggestion": "Focus on value not price. Ask: 'What's most important to you in solving this problem?'"
            }
        
        return None
    
    def _has_keyword_trigger(self, transcript: str) -> bool:
        trigger_words = [
            "not happy", "disappointed", "frustrated", "wait", "waited",
            "refund", "broken", "doesn't work", "problem", "issue",
            "explain", "understand", "why", "how long"
        ]
        t = transcript.lower()
        return any(w in t for w in trigger_words)
    
    async def _strategic_decision(self, perception: dict):
        try:
            self._last_intervention_time = asyncio.get_event_loop().time()
            
            recent_transcript = " | ".join(
                [t["text"] for t in self.call_transcript[-5:]]
            )
            emotion_trend = [e.get("label", "neutral") for e in self.emotion_timeline[-5:]]
            
            prompt = f"""You are MAESTRO, an AI sales coach monitoring a live customer call.

CURRENT CALL STATE:
- Recent transcript (last ~30 sec): "{recent_transcript}"
- Emotion trend: {emotion_trend}
- Current risk score: {self.risk_score:.2f}/1.0
- Call duration: {self._get_call_duration()} minutes

Analyze this situation and provide ONE tactical coaching action.
Respond ONLY with a raw JSON object. NO markdown blocks (no ```json).

{{
  "action_type": "show_prompt|show_kb_result|escalate|draft_email|search_linkedin|schedule_call|none",
  "priority": "low|medium|high|critical",
  "headline": "5 words max",
  "suggestion": "1-2 sentences exactly what the agent should say",
  "reasoning": "1 sentence logic",
  "kb_query": "null or search query"
}}

Rules:
- If customer mentions a specific problem, use "show_kb_result".
- If customer is a VIP or high-value, use "search_linkedin" to find rapport triggers.
- If customer is happy and closing, use "schedule_call" for next steps.
- Be bold but concise. Script should sound natural, not robotic.
- Match urgency to emotion intensity."""

            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.gemini.generate_content(prompt).text
            )
            
            action = self._parse_gemini_response(response)
            
            if action and action.get("action_type") != "none":
                if action.get("kb_query"):
                    kb_result = await self.query_knowledge_base(action["kb_query"])
                    action["kb_data"] = kb_result
                
                await self._execute_action(action)
                
        except Exception as e:
            print(f"Gemini strategic decision error: {e}")
    
    def _parse_gemini_response(self, response_text: str) -> Optional[dict]:
        try:
            text = response_text.strip()
            
            if "```" in text:
                match = re.search(r"(\{.*\})", text, re.DOTALL)
                if match:
                    text = match.group(1)
            
            if not text.startswith("{"):
                start = text.find("{")
                end = text.rfind("}")
                if start != -1 and end != -1:
                    text = text[start:end+1]
            
            text = text.strip()
            text = text.replace(",\n}", "\n}").replace(",}", "}")
            
            return json.loads(text)
        except json.JSONDecodeError as e:
            print(f"JSON Parse Error: {e}")
            return None
        except Exception as e:
            print(f"Failed to parse Gemini response: {e}")
            return None
    
    async def _execute_action(self, action: dict):
        action_id = str(uuid.uuid4())
        action["action_id"] = action_id
        action["timestamp"] = datetime.now().isoformat()
        
        self.actions_taken.append(action)
        
        await self.ws_manager.send(self.session_id, {
            "type": "agent_action",
            "data": action
        })
        
        if action.get("action_type") == ActionType.ESCALATE:
            asyncio.create_task(
                self.integrations.escalate_to_slack(
                    self.session_id, 
                    action.get("message", action.get("headline", "Critical Escalation")),
                    action.get("priority", "high")
                )
            )
        elif action.get("action_type") == ActionType.UPDATE_CRM:
            asyncio.create_task(self.integrations.log_to_crm(self.session_id, action))
        elif action.get("action_type") == ActionType.SEARCH_LINKEDIN:
            bg_data = await self.integrations.search_linkedin(action.get("customer_name", "Customer"))
            action["enriched_data"] = bg_data
        elif action.get("action_type") == ActionType.SCHEDULE_FOLLOWUP:
            sched_data = await self.integrations.schedule_followup(self.session_id)
            action["enriched_data"] = sched_data
        elif action.get("action_type") == ActionType.DRAFT_EMAIL:
            email_data = await self.integrations.draft_followup_email(self.session_id, action)
            action["enriched_data"] = {"draft_status": "prepared", "preview": email_data}
            
        print(f"Agent action: [{action.get('priority', '?')}] {action.get('headline', 'Action')}")
    
    async def query_knowledge_base(self, query: str) -> dict:
        try:
            from tools.kb_search import KnowledgeBase
            kb = KnowledgeBase()
            results = await kb.search(query)
            return {"query": query, "results": results, "found": len(results) > 0}
        except Exception as e:
            return {"query": query, "results": [], "found": False, "error": str(e)}
    
    async def end_call(self) -> dict:
        duration = self._get_call_duration()
        
        summary_prompt = f"""Summarize this customer service call:

Transcript highlights:
{chr(10).join([t["text"] for t in self.call_transcript[-15:]])}

Emotion journey: {[e.get("label") for e in self.emotion_timeline]}
Peak risk score: {max((e.get("risk_level", 0) for e in self.emotion_timeline), default=0):.2f}
Duration: {duration} minutes

Provide:
1. Call outcome (resolved/unresolved/escalated/churned)
2. Main issue discussed (1 sentence)
3. Customer sentiment (improved/worsened/neutral)
4. Follow-up actions needed (list max 3)
5. Draft follow-up email subject line

JSON format."""

        try:
            summary_text = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.gemini.generate_content(summary_prompt).text
            )
            summary = self._parse_gemini_response(summary_text) or {}
        except Exception:
            summary = {"outcome": "unknown"}
        
        summary.update({
            "call_id": self.call_id,
            "duration_minutes": duration,
            "total_interventions": len(self.actions_taken),
            "peak_risk": max((e.get("risk_level", 0) for e in self.emotion_timeline), default=0),
        })
        
        print(f"Call ended. Duration: {duration}m, Interventions: {len(self.actions_taken)}")
        
        if len(self.call_transcript) > 3:
            asyncio.create_task(self.integrations.log_to_crm(self.session_id, summary))
            asyncio.create_task(self.session_store.store_call(self.session_id, summary))
            
        return summary
    
    async def record_feedback(self, action_id: str, rating: int, outcome: str):
        feedback = {
            "action_id": action_id,
            "rating": rating,
            "outcome": outcome,
            "timestamp": datetime.now().isoformat()
        }
        try:
            await self.session_store.store_feedback(self.session_id, feedback)
        except Exception:
            pass
    
    def _get_call_duration(self) -> float:
        if not self.call_start_time:
            return 0.0
        delta = datetime.now() - self.call_start_time
        return round(delta.total_seconds() / 60, 1)
