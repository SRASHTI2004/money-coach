"""Insight routes: nudges, nudge explanations, monthly review."""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from .. import coach_tools, gemini, guardrails, nudges, review
from .common import ai_limited, user_id

router = APIRouter(prefix="/api")


@router.get("/nudges")
def get_nudges(uid: str = Depends(user_id)) -> list[dict]:
    """Current drift nudges and alerts, most urgent first."""
    return nudges.generate(uid)


@router.get("/nudges/explain")
def explain(id: str, uid: str = Depends(ai_limited)) -> dict[str, Any]:
    """Explain a nudge: Gemini narration of verified facts, built-in text as fallback."""
    base = coach_tools.tool_explain_nudge(uid, id)
    if "error" in base:
        raise HTTPException(404, base["error"])
    prompt = ("Explain this spending nudge to the user in 2-3 friendly sentences and give ONE concrete, low-effort "
              "action. Use only these facts; do not mention investment products.\n" + str(base))
    text = gemini.generate(prompt, system=guardrails.SYSTEM_RULES, cache_key=str(base))
    return {**base, "explanation": guardrails.sanitize_output(text) if text else base["why"], "ai": bool(text)}


@router.get("/review")
def get_review(month: str | None = None, uid: str = Depends(ai_limited)) -> dict[str, Any]:
    """Monthly review: verified facts plus Gemini narrative (template fallback)."""
    r = review.narrative(uid, month)
    if r is None:
        raise HTTPException(404, "No data yet - load the demo or upload a statement first.")
    return {**r, "months": review.months_available(uid)}
