"""Coach routes: chat, history, confirm/reject proposals."""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from .. import coach, coach_tools, db
from .common import ai_limited, user_id
from .schemas import ChatIn

router = APIRouter(prefix="/api")
HISTORY_LIMIT = 40


@router.post("/chat")
def chat(body: ChatIn, uid: str = Depends(ai_limited)) -> dict[str, Any]:
    """Ask the coach (tools + guardrails); may return pending proposals."""
    return coach.chat(uid, body.message)


@router.get("/chat/history")
def chat_history(uid: str = Depends(user_id)) -> dict[str, Any]:
    """Recent messages and any pending proposals."""
    msgs = db.rows("SELECT role,text FROM chat WHERE uid=? ORDER BY id", (uid,))[-HISTORY_LIMIT:]
    return {"messages": msgs, "proposals": coach_tools.pending(uid)}


@router.post("/proposals/{pid}/confirm")
def confirm(pid: int, uid: str = Depends(user_id)) -> dict[str, Any]:
    """Apply a pending proposal (the only way coach suggestions change anything)."""
    r = coach_tools.apply_proposal(uid, pid)
    if r is None:
        raise HTTPException(404, "Proposal not found")
    return r


@router.post("/proposals/{pid}/reject")
def reject(pid: int, uid: str = Depends(user_id)) -> dict[str, str]:
    """Dismiss a pending proposal."""
    return coach_tools.reject_proposal(uid, pid)
