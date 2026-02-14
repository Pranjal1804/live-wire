"""
Keyword-driven battlecard matcher.

Runs a fast regex scan on each transcript before it reaches the LLM,
so competitor mentions trigger instant UI updates without any API latency.
"""

import re
from typing import Optional

# ── Battlecard database ──
# Add/remove competitors and their talking points here.
# Each entry maps a regex pattern to a battlecard payload.

BATTLECARDS: dict[str, dict] = {
    "salesforce": {
        "competitor": "Salesforce",
        "talking_points": [
            "Our onboarding is 3x faster -- no 6-month implementation cycle",
            "We include AI coaching at no extra cost; Salesforce Einstein is a paid add-on",
            "Our per-seat pricing is 40% lower at comparable tiers",
            "Real-time call analytics vs. Salesforce's batch reporting",
        ],
        "weaknesses": [
            "Complex admin overhead -- average customer needs a dedicated Salesforce admin",
            "Einstein AI accuracy criticized in Gartner peer reviews (2024)",
        ],
        "counter_objections": {
            "ecosystem": "We integrate with 50+ tools via native webhooks; no AppExchange lock-in",
            "market_leader": "Market share does not equal best fit -- ask about their churn rate",
        },
    },
    "hubspot": {
        "competitor": "HubSpot",
        "talking_points": [
            "HubSpot's free tier lacks call recording and analytics",
            "Our AI coaching works in real-time during the call, not post-call",
            "HubSpot Sales Hub Enterprise is $150/seat/mo vs. our $89/seat/mo",
        ],
        "weaknesses": [
            "Limited customization on workflows without Operations Hub",
            "Call transcription is post-call only with no word-level timestamps",
        ],
        "counter_objections": {
            "all_in_one": "Bundling CRM + marketing inflates cost; best-of-breed is more flexible",
        },
    },
    "gong": {
        "competitor": "Gong",
        "talking_points": [
            "Gong is $100+/seat/mo with annual contracts; we offer monthly billing",
            "Our processing is 100% local -- no audio leaves your network",
            "Real-time coaching during the call vs. Gong's post-call analysis",
        ],
        "weaknesses": [
            "Gong requires uploading all call recordings to their cloud",
            "Privacy concerns -- GDPR compliance requires additional configuration",
        ],
        "counter_objections": {
            "proven": "We offer a free pilot with ROI measurement built in",
        },
    },
    "chorus": {
        "competitor": "Chorus (ZoomInfo)",
        "talking_points": [
            "Chorus was acquired by ZoomInfo -- product direction is uncertain",
            "Our standalone focus means faster feature iteration",
            "No bundling tax -- you pay only for what you use",
        ],
        "weaknesses": [
            "Integration depth with ZoomInfo data is limited post-acquisition",
        ],
        "counter_objections": {},
    },
    "outreach": {
        "competitor": "Outreach",
        "talking_points": [
            "Outreach focuses on sequencing; we focus on live call intelligence",
            "Complementary, not competitive -- but our analytics replace their call features",
        ],
        "weaknesses": [
            "Call analytics is a secondary feature, not their core product",
        ],
        "counter_objections": {},
    },
}

# Pre-compile a single regex that matches any competitor keyword.
# Word boundaries ensure "sales" alone does not match "salesforce".
_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in BATTLECARDS.keys()) + r")\b",
    re.IGNORECASE,
)


def scan_transcript(text: str) -> Optional[dict]:
    """
    Scan transcript text for competitor mentions.

    Returns the first matching battlecard, or None if no competitor is found.
    This is deliberately fast (single regex pass) and returns immediately
    without any LLM call.
    """
    match = _PATTERN.search(text)
    if match:
        key = match.group(1).lower()
        return BATTLECARDS.get(key)
    return None


def scan_all_matches(text: str) -> list[dict]:
    """
    Return all unique competitor battlecards mentioned in the text.
    """
    seen = set()
    results = []
    for match in _PATTERN.finditer(text):
        key = match.group(1).lower()
        if key not in seen:
            seen.add(key)
            card = BATTLECARDS.get(key)
            if card:
                results.append(card)
    return results
