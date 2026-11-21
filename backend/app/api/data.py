"""Data routes: demo, ingestion, transactions, categorisation rules, dashboard summary."""
import os
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from .. import analytics as an
from .. import categorize, db, ingest, planner, seed, timeline
from ..config import ALLOWED_UPLOAD_EXT, MAX_UPLOAD_BYTES
from .common import ai_limited, user_id
from .schemas import CategoryPatch, PasteIn

router = APIRouter(prefix="/api")
MAX_LIST = 1000
MAX_SEARCH_CHARS = 60


@router.post("/demo/load")
def demo_load(uid: str = Depends(ai_limited)) -> dict[str, Any]:
    """Reset this user and load the bundled sample CSV, PDF and SMS plus profile, goals and history."""
    return {"loaded": seed.load_demo(uid)}


@router.post("/reset")
def reset(uid: str = Depends(user_id)) -> dict[str, bool]:
    """Delete everything stored for this user."""
    db.wipe_user(uid)
    return {"ok": True}


@router.post("/upload")
async def upload(file: UploadFile = File(...), uid: str = Depends(ai_limited)) -> dict[str, Any]:
    """Ingest a bank CSV/PDF/text file (type and size limited)."""
    name = file.filename or "upload"
    if os.path.splitext(name)[1].lower() not in ALLOWED_UPLOAD_EXT:
        raise HTTPException(415, "Unsupported file type. Upload a .csv, .pdf or .txt bank statement.")
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"File too large ({MAX_UPLOAD_BYTES // 1_000_000} MB max).")
    if name.lower().endswith(".pdf") and not data.startswith(b"%PDF"):
        raise HTTPException(415, "That file is not a valid PDF.")
    return ingest.ingest(uid, name, data)


@router.post("/paste")
def paste(body: PasteIn, uid: str = Depends(ai_limited)) -> dict[str, Any]:
    """Ingest pasted bank SMS or CSV text."""
    return ingest.ingest(uid, "paste.txt", body.text.encode(), force_kind=body.kind)


@router.get("/transactions")
def transactions(uid: str = Depends(user_id), month: str | None = None, category: str | None = None,
                 q: str | None = None, limit: int = 500) -> list[dict]:
    """List transactions with optional month / category / text filters."""
    sql, args = "SELECT * FROM transactions WHERE uid=?", [uid]
    if month:
        sql += " AND date LIKE ?"
        args.append(month[:7] + "%")
    if category:
        sql += " AND category=?"
        args.append(category)
    if q:
        sql += " AND (description LIKE ? OR merchant LIKE ?)"
        args += [f"%{q[:MAX_SEARCH_CHARS]}%"] * 2
    return db.rows(sql + " ORDER BY date DESC, id DESC LIMIT ?", (*args, max(1, min(limit, MAX_LIST))))


@router.patch("/transactions/{tx_id}")
def fix_category(tx_id: int, body: CategoryPatch, uid: str = Depends(user_id)) -> dict[str, Any]:
    """Correct a category: learns a merchant rule and re-labels similar transactions."""
    if body.category not in categorize.CATEGORIES:
        raise HTTPException(400, "Unknown category")
    res = categorize.learn_rule(uid, tx_id, body.category)
    if res is None:
        raise HTTPException(404, "Transaction not found")
    if res.get("rule_created"):
        timeline.log(uid, "rule", f"Learned rule: {res['merchant']} -> {body.category}",
                     f"{res['also_updated']} other transaction(s) re-labelled",
                     "You corrected a category; the coach now applies it to future transactions.")
    return res


@router.get("/categories")
def categories() -> list[str]:
    """All allowed spending categories."""
    return categorize.CATEGORIES


@router.get("/rules")
def rules(uid: str = Depends(user_id)) -> list[dict]:
    """Rules the user has taught the coach."""
    return categorize.get_rules(uid)


@router.delete("/rules/{rid}")
def delete_rule(rid: int, uid: str = Depends(user_id)) -> dict[str, bool]:
    """Forget a learned rule."""
    db.run("DELETE FROM rules WHERE id=? AND uid=?", (rid, uid))
    return {"ok": True}


@router.get("/summary")
def summary(uid: str = Depends(user_id)) -> dict[str, Any]:
    """Dashboard payload: monthly totals, current snapshot and profile (or an empty marker)."""
    txns = an.get_txns(uid)
    if not txns:
        return {"empty": True}
    mon = an.monthly(txns)
    return {
        "empty": False, "as_of": an.as_of(uid, txns).isoformat(),
        "months": [{"month": k, **{x: round(v[x]) for x in ("income", "spend", "invested")},
                    "by_cat": {c: round(a) for c, a in v["by_cat"].items()}} for k, v in sorted(mon.items())],
        "snapshot": planner.snapshot(uid), "profile": planner.get_profile(uid), "tx_count": len(txns),
        "uncategorized": sum(1 for t in txns if t["category"] == "Other"),
    }
