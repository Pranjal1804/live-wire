import os
import json
import httpx
import asyncio
from typing import Optional

class IntegrationManager:
    def __init__(self):
        self.slack_webhook = os.environ.get("SLACK_WEBHOOK_URL")
        self.crm_webhook = os.environ.get("CRM_WEBHOOK_URL")
        self.client = httpx.AsyncClient(timeout=10.0)

    async def escalate_to_slack(self, session_id: str, message: str, priority: str = "high"):
        if not self.slack_webhook:
            print(f"Slack webhook not configured. Escalation log: {message}")
            return False
            
        payload = {
            "text": f"MAESTRO ESCALATION [{priority.upper()}]\nSession: {session_id}\nAlert: {message}",
            "username": "Maestro Bot"
        }
        
        try:
            resp = await self.client.post(self.slack_webhook, json=payload)
            return resp.status_code == 200
        except Exception as e:
            print(f"Slack notification failed: {e}")
            return False

    async def log_to_crm(self, session_id: str, summary: dict):
        if not self.crm_webhook:
            print(f"CRM webhook not configured. Mocking CRM log for session {session_id}")
            return True
            
        try:
            resp = await self.client.post(self.crm_webhook, json=summary)
            return resp.status_code == 200
        except Exception as e:
            print(f"CRM logging failed: {e}")
            return False

    async def draft_followup_email(self, session_id: str, summary: dict) -> str:
        return f"Email drafted for session {session_id}."

    async def search_linkedin(self, name: str) -> dict:
        return {
            "name": name or "Customer",
            "title": "Director of Operations",
            "company": "Enterprise Corp",
            "recent_post": "Passionate about scaling customer success teams through AI.",
            "common_interests": ["AI Ethics", "Mountain Biking"]
        }

    async def schedule_followup(self, session_id: str, suggested_time: str = "Tomorrow 10am"):
        return {
            "status": "scheduled",
            "time": suggested_time,
            "calendar_link": "https://calendly.com/maestro-demo/followup"
        }

    async def close(self):
        await self.client.aclose()
