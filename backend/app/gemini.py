"""Gemini wrapper: primary + fallback model, result cache by content hash, graceful None on failure."""
import hashlib
import json
import os
import time

from . import db

PRIMARY = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")
FALLBACK = os.environ.get("GEMINI_FALLBACK_MODEL", "gemini-3.5-flash-lite")
_client = None
_down_until = 0.0
status = {"available": None, "last_error": None, "model": None, "calls": 0, "cache_hits": 0}


def _key():
    k = os.environ.get("GEMINI_API_KEY")
    if k:
        return k
    p = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            if line.startswith("GEMINI_API_KEY="):
                return line.split("=", 1)[1].strip()
    return None


def client():
    global _client
    if _client is None:
        from google import genai
        k = _key()
        if not k:
            return None
        from google.genai import types as _t
        _client = genai.Client(api_key=k, http_options=_t.HttpOptions(timeout=20000))
    return _client


def file_hash(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode()
    return hashlib.sha256(data).hexdigest()


def enabled():
    return os.environ.get("DISABLE_AI") != "1" and _key() is not None


def _models():
    return [PRIMARY, FALLBACK]


def generate(prompt, system=None, json_mode=False, cache_key=None, tools=None, contents=None, raw=False):
    """Returns text (or parsed JSON when json_mode), or None when AI is unavailable.
    With raw=True returns the full response object (used by the tool loop; never cached)."""
    if not enabled():
        status.update(available=False, last_error="AI disabled or no API key")
        return None
    h = None
    if cache_key and not raw:
        h = file_hash(f"{json_mode}|{system}|{cache_key}")
        hit = db.one("SELECT v FROM cache WHERE h=?", (h,))
        if hit:
            status["cache_hits"] += 1
            v = hit["v"]
            return json.loads(v) if json_mode else v
    global _down_until
    if time.time() < _down_until:  # circuit breaker: recent failure -> skip AI, use non-AI fallbacks instantly
        return None
    from google.genai import types
    cfg = {}
    if system:
        cfg["system_instruction"] = system
    if json_mode:
        cfg["response_mode"] = None
        cfg["response_mime_type"] = "application/json"
    if tools:
        cfg["tools"] = tools
        cfg["automatic_function_calling"] = types.AutomaticFunctionCallingConfig(disable=True)
    cfg = {k: v for k, v in cfg.items() if v is not None}
    last = None
    for model in _models():
        for attempt in range(1):
            try:
                status["calls"] += 1
                r = client().models.generate_content(
                    model=model, contents=contents if contents is not None else prompt,
                    config=types.GenerateContentConfig(**cfg))
                status.update(available=True, last_error=None, model=model)
                if raw:
                    return r
                text = (r.text or "").strip()
                if json_mode:
                    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                    val = json.loads(text)
                else:
                    val = text
                if h:
                    db.run("INSERT OR REPLACE INTO cache(h,v) VALUES(?,?)",
                           (h, json.dumps(val) if json_mode else val))
                return val
            except Exception as e:  # quota, 503, bad JSON...
                last = e
                time.sleep(0.6 * (attempt + 1))
                msg = str(e)
                if "429" in msg or "RESOURCE_EXHAUSTED" in msg or "404" in msg:
                    break
    status.update(available=False, last_error=str(last)[:200])
    _down_until = time.time() + 45
    return None
