"""FastAPI app: JSON API under /api, React build served from the same service."""
import os

from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import analytics as an
from . import categorize, coach, db, gemini, guardrails, ingest, nudges, planner, review, seed

app = FastAPI(title="Money Coach")
db.init()


def uid_of(x_user: str | None) -> str:
    u = "".join(ch for ch in (x_user or "demo") if ch.isalnum() or ch in "-_")[:64]
    return u or "demo"


class CategoryPatch(BaseModel):
    category: str


class TextIn(BaseModel):
    text: str
    kind: str | None = None


class ProfileIn(BaseModel):
    monthly_income: float | None = None
    fixed_costs: list[dict] | None = None
    emergency_fund: float | None = None
    emergency_target_months: float | None = None
    emergency_monthly: float | None = None
    budgets: dict[str, float] | None = None


class GoalIn(BaseModel):
    name: str
    target_amount: float
    saved: float = 0
    target_date: str
    monthly_contrib: float = 0


class SimIn(BaseModel):
    adjustments: list[dict]


class ChatIn(BaseModel):
    message: str


class UsedIn(BaseModel):
    last_used: str | None = None


@app.get("/api/health")
def health():
    return {"ok": True, "ai_enabled": gemini.enabled(), "ai": gemini.status, "disclaimer": guardrails.DISCLAIMER}


@app.post("/api/demo/load")
def demo_load(x_user: str | None = Header(None)):
    return {"loaded": seed.load_demo(uid_of(x_user))}


@app.post("/api/reset")
def reset(x_user: str | None = Header(None)):
    db.wipe_user(uid_of(x_user))
    return {"ok": True}


# ---- ingestion & transactions
@app.post("/api/upload")
async def upload(file: UploadFile = File(...), x_user: str | None = Header(None)):
    data = await file.read()
    if len(data) > 8_000_000:
        raise HTTPException(413, "File too large (8 MB max)")
    return ingest.ingest(uid_of(x_user), file.filename or "upload", data)


@app.post("/api/paste")
def paste(body: TextIn, x_user: str | None = Header(None)):
    return ingest.ingest(uid_of(x_user), "paste.txt", body.text.encode(), force_kind=body.kind)


@app.get("/api/transactions")
def transactions(x_user: str | None = Header(None), month: str | None = None, category: str | None = None,
                 q: str | None = None, limit: int = 500):
    sql, args = "SELECT * FROM transactions WHERE uid=?", [uid_of(x_user)]
    if month:
        sql += " AND date LIKE ?"
        args.append(month + "%")
    if category:
        sql += " AND category=?"
        args.append(category)
    if q:
        sql += " AND (description LIKE ? OR merchant LIKE ?)"
        args += [f"%{q}%", f"%{q}%"]
    return db.rows(sql + " ORDER BY date DESC, id DESC LIMIT ?", (*args, limit))


@app.patch("/api/transactions/{tx_id}")
def fix_category(tx_id: int, body: CategoryPatch, x_user: str | None = Header(None)):
    if body.category not in categorize.CATEGORIES:
        raise HTTPException(400, "Unknown category")
    res = categorize.learn_rule(uid_of(x_user), tx_id, body.category)
    if res is None:
        raise HTTPException(404, "Transaction not found")
    return res


@app.get("/api/categories")
def categories():
    return categorize.CATEGORIES


@app.get("/api/rules")
def rules(x_user: str | None = Header(None)):
    return categorize.get_rules(uid_of(x_user))


@app.delete("/api/rules/{rid}")
def delete_rule(rid: int, x_user: str | None = Header(None)):
    db.run("DELETE FROM rules WHERE id=? AND uid=?", (rid, uid_of(x_user)))
    return {"ok": True}


# ---- dashboard
@app.get("/api/summary")
def summary(x_user: str | None = Header(None)):
    uid = uid_of(x_user)
    txns = an.get_txns(uid)
    if not txns:
        return {"empty": True}
    mon = an.monthly(txns)
    ao = an.as_of(uid, txns)
    snap = planner.snapshot(uid)
    return {"empty": False, "as_of": ao.isoformat(), "months": [{"month": k, **{x: round(v[x]) for x in ("income", "spend", "invested")},
            "by_cat": {c: round(a) for c, a in v["by_cat"].items()}} for k, v in sorted(mon.items())],
            "snapshot": snap, "profile": planner.get_profile(uid), "tx_count": len(txns),
            "uncategorized": sum(1 for t in txns if t["category"] == "Other")}


# ---- profile & goals
@app.get("/api/profile")
def get_profile(x_user: str | None = Header(None)):
    return planner.get_profile(uid_of(x_user))


@app.put("/api/profile")
def put_profile(body: ProfileIn, x_user: str | None = Header(None)):
    return planner.save_profile(uid_of(x_user), body.model_dump(exclude_unset=True))


@app.get("/api/goals")
def goals(x_user: str | None = Header(None)):
    uid = uid_of(x_user)
    snap = planner.snapshot(uid)
    return {"items": snap["goals"]["items"], "free_cash": snap["free_cash"], "planned_total": snap["goals"]["planned_total"],
            "scale": snap["goals"]["scale"]}


@app.post("/api/goals")
def add_goal(body: GoalIn, x_user: str | None = Header(None)):
    gid = db.run("INSERT INTO goals(uid,name,target_amount,saved,target_date,monthly_contrib) VALUES(?,?,?,?,?,?)",
                 (uid_of(x_user), body.name, body.target_amount, body.saved, body.target_date, body.monthly_contrib))
    return {"id": gid}


@app.put("/api/goals/{gid}")
def edit_goal(gid: int, body: GoalIn, x_user: str | None = Header(None)):
    db.run("UPDATE goals SET name=?,target_amount=?,saved=?,target_date=?,monthly_contrib=? WHERE id=? AND uid=?",
           (body.name, body.target_amount, body.saved, body.target_date, body.monthly_contrib, gid, uid_of(x_user)))
    return {"ok": True}


@app.delete("/api/goals/{gid}")
def del_goal(gid: int, x_user: str | None = Header(None)):
    db.run("DELETE FROM goals WHERE id=? AND uid=?", (gid, uid_of(x_user)))
    return {"ok": True}


# ---- subscriptions, simulator, nudges, review
@app.get("/api/subscriptions")
def subscriptions(x_user: str | None = Header(None)):
    subs = an.detect_recurring(uid_of(x_user))
    return {"items": subs, "monthly_total": round(sum(s["monthly_cost"] for s in subs if s["kind"] == "subscription"))}


@app.put("/api/subscriptions/{merchant}/used")
def mark_used(merchant: str, body: UsedIn, x_user: str | None = Header(None)):
    uid = uid_of(x_user)
    d = body.last_used or an.as_of(uid).isoformat()
    db.run("INSERT OR REPLACE INTO sub_meta(uid,merchant,last_used) VALUES(?,?,?)", (uid, merchant, d))
    return {"ok": True, "last_used": d}


@app.post("/api/simulate")
def simulate(body: SimIn, x_user: str | None = Header(None)):
    adjs = []
    for a in body.adjustments:
        if a.get("category") and (a.get("percent") is not None or a.get("amount") is not None):
            adjs.append({"category": a["category"], **{k: float(a[k]) for k in ("percent", "amount") if a.get(k) is not None}})
    sim = planner.simulate(uid_of(x_user), adjs)
    sim["summary"] = planner.summarize_sim(sim)
    return sim


@app.get("/api/nudges")
def get_nudges(x_user: str | None = Header(None)):
    return nudges.generate(uid_of(x_user))


@app.get("/api/nudges/explain")
def explain(id: str, x_user: str | None = Header(None)):
    uid = uid_of(x_user)
    base = coach.tool_explain_nudge(uid, id)
    if "error" in base:
        raise HTTPException(404, base["error"])
    prompt = ("Explain this spending nudge to the user in 2-3 friendly sentences and give ONE concrete, low-effort "
              "action. Use only these facts; do not mention investment products.\n" + str(base))
    text = gemini.generate(prompt, system=guardrails.SYSTEM_RULES, cache_key=str(base))
    return {**base, "explanation": guardrails.sanitize_output(text) if text else base["why"], "ai": bool(text)}


@app.get("/api/review")
def get_review(month: str | None = None, x_user: str | None = Header(None)):
    r = review.narrative(uid_of(x_user), month)
    if r is None:
        raise HTTPException(404, "No data yet")
    return {**r, "months": review.months_available(uid_of(x_user))}


# ---- coach
@app.post("/api/chat")
def chat(body: ChatIn, x_user: str | None = Header(None)):
    if not body.message.strip():
        raise HTTPException(400, "Empty message")
    return coach.chat(uid_of(x_user), body.message.strip()[:1000])


@app.get("/api/chat/history")
def chat_history(x_user: str | None = Header(None)):
    uid = uid_of(x_user)
    return {"messages": db.rows("SELECT role,text FROM chat WHERE uid=? ORDER BY id", (uid,))[-40:],
            "proposals": coach.pending(uid)}


@app.post("/api/proposals/{pid}/confirm")
def confirm(pid: int, x_user: str | None = Header(None)):
    r = coach.apply_proposal(uid_of(x_user), pid)
    if r is None:
        raise HTTPException(404, "Proposal not found")
    return r


@app.post("/api/proposals/{pid}/reject")
def reject(pid: int, x_user: str | None = Header(None)):
    return coach.reject_proposal(uid_of(x_user), pid)


# ---- frontend (built by Vite into frontend/dist)
DIST = os.environ.get("FRONTEND_DIST", os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))
if os.path.isdir(DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(DIST, "assets")), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        f = os.path.join(DIST, path)
        if path and os.path.isfile(f) and ".." not in path:
            return FileResponse(f)
        return FileResponse(os.path.join(DIST, "index.html"))
