"""Shared API helpers: anonymous user id, per-user rate limiting."""
import re
import time
from collections import defaultdict, deque

from fastapi import Depends, Header, HTTPException

from ..config import AI_REQUESTS_PER_MINUTE

_UID_CHARS = re.compile(r"[^A-Za-z0-9_-]")
_WINDOW_SECONDS = 60
_hits: dict[str, deque[float]] = defaultdict(deque)


def user_id(x_user: str | None = Header(None)) -> str:
    """Anonymous per-browser id from the X-User header (sanitised, max 64 chars)."""
    return _UID_CHARS.sub("", x_user or "demo")[:64] or "demo"


def ai_limited(uid: str = Depends(user_id)) -> str:
    """Dependency for endpoints that may call Gemini: sliding-window rate limit per user."""
    now = time.time()
    q = _hits[uid]
    while q and now - q[0] > _WINDOW_SECONDS:
        q.popleft()
    if len(q) >= AI_REQUESTS_PER_MINUTE:
        raise HTTPException(429, "Too many requests - please wait a few seconds and try again.")
    q.append(now)
    return uid
