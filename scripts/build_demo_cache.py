"""Pre-computes every Gemini result the demo needs (categorisation, monthly reviews, nudge explanations,
life-event narrations, coach answers) and stores them in backend/app/gemini_cache.json, so the demo is instant
and never shows 'AI busy'. Live Gemini still runs for anything new. Needs a working GEMINI_API_KEY.

Run:  python scripts/build_demo_cache.py
"""
import json
import os
import sys
import tempfile

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "cachebuild.db")
os.environ["COACH_CACHE_WRITE"] = "1"
os.environ["GEMINI_NO_BREAKER"] = "1"
os.environ.setdefault("GEMINI_TIMEOUT_MS", "60000")
sys.path.insert(0, os.path.join(ROOT, "backend"))

from fastapi.testclient import TestClient  # noqa: E402

from app import db, gemini  # noqa: E402
from app.main import app  # noqa: E402

c = TestClient(app, raise_server_exceptions=True)
H = {"X-User": "cachebuild"}


def get(path):
    r = c.get(path, headers=H)
    r.raise_for_status()
    return r.json()


def post(path, body=None):
    r = c.post(path, json=body, headers=H)
    r.raise_for_status()
    return r.json()


def main():
    db.wipe_user("cachebuild")
    print("1/5 loading demo (Gemini categorises unknown merchants)...", flush=True)
    res = post("/api/demo/load")
    print("   categorised_by:", [x["categorized_by"] for x in res["loaded"]], flush=True)

    print("2/5 monthly reviews...", flush=True)
    for m in get("/api/review")["months"]:
        r = get(f"/api/review?month={m}")
        print("  ", m, "ai" if r["ai"] else "FALLBACK", flush=True)

    print("3/5 nudge explanations...", flush=True)
    for n in get("/api/nudges"):
        r = get("/api/nudges/explain?id=" + n["id"].replace(":", "%3A").replace(" ", "%20").replace("&", "%26"))
        print("  ", n["id"], "ai" if r["ai"] else "FALLBACK", flush=True)

    print("4/5 life-event narrations...", flush=True)
    presets = [
        [{"type": "job_loss", "start": 2, "months": 3, "cut_pct": 30}],
        [{"type": "salary_change", "start": 2, "percent": 15}],
        [{"type": "job_loss", "start": 2, "months": 3, "cut_pct": 30}, {"type": "new_emi", "start": 5, "amount": 8000, "months": 36}],
        [{"type": "rent_increase", "start": 2, "amount": 6000}, {"type": "salary_change", "start": 4, "percent": 20}],
    ]
    for ev in presets:
        r = post("/api/life-events/narrate", {"events": ev})
        print("  ", [e["type"] for e in ev], "ai" if r["ai"] else "FALLBACK", flush=True)

    print("5/5 coach answers...", flush=True)
    for q in ["What if I cut dining out by 30%?", "Why am I over budget on dining?", "Which subscriptions should I look at?",
              "Am I on track for my goals?", "What if my rent goes up by 3000?", "Set my dining budget to 4000 and explain why"]:
        r = post("/api/chat", {"message": q})
        print("  ", q, "->", "ai" if r["ai"] else "FALLBACK", [t["tool"] for t in r["tools"]], flush=True)
        for p in r["proposals"]:  # leave nothing pending between questions
            post(f"/api/proposals/{p['id']}/reject")

    rows = db.rows("SELECT h, v FROM cache")
    out = os.path.join(ROOT, "backend", "app", "gemini_cache.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"note": "Pre-computed Gemini results for the bundled demo data. Regenerate: scripts/build_demo_cache.py",
               "cache": {r["h"]: r["v"] for r in rows}}, f, ensure_ascii=False, indent=0)
    print(f"wrote {len(rows)} entries to {out}; gemini calls={gemini.status['calls']}", flush=True)


if __name__ == "__main__":
    main()
