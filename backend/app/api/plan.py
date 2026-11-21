"""Plan routes: profile, goals, subscriptions, what-if, life events, timeline."""
from typing import Any

from fastapi import APIRouter, Depends

from .. import analytics as an
from .. import db, lifeevents, planner, timeline
from ..config import MANDATE_CHANGE_RUPEES
from .common import ai_limited, user_id
from .schemas import GoalIn, LifeIn, ProfileIn, SimIn, UsedIn

router = APIRouter(prefix="/api")
MAX_MERCHANT_CHARS = 60


@router.get("/profile")
def get_profile(uid: str = Depends(user_id)) -> dict[str, Any]:
    """The persistent financial profile."""
    return planner.get_profile(uid)


@router.put("/profile")
def put_profile(body: ProfileIn, uid: str = Depends(user_id)) -> dict[str, Any]:
    """Update the profile and record what changed on the timeline."""
    old = planner.get_profile(uid)
    new = planner.save_profile(uid, body.model_dump(exclude_unset=True))
    timeline.log_profile_change(uid, old, new)
    return new


@router.get("/goals")
def goals(uid: str = Depends(user_id)) -> dict[str, Any]:
    """Goals with projected dates, funding and on-track status."""
    snap = planner.snapshot(uid)
    g = snap["goals"]
    return {"items": g["items"], "free_cash": snap["free_cash"], "planned_total": g["planned_total"], "scale": g["scale"]}


@router.post("/goals")
def add_goal(body: GoalIn, uid: str = Depends(user_id)) -> dict[str, int]:
    """Create a goal."""
    d = body.target_date.isoformat()
    gid = db.run("INSERT INTO goals(uid,name,target_amount,saved,target_date,monthly_contrib) VALUES(?,?,?,?,?,?)",
                 (uid, body.name, body.target_amount, body.saved, d, body.monthly_contrib))
    timeline.log(uid, "goal", f"New goal: {body.name} {an.inr(body.target_amount)} by {d}",
                 f"{an.inr(body.monthly_contrib)}/month planned", "Added in Plan")
    return {"id": gid}


@router.put("/goals/{gid}")
def edit_goal(gid: int, body: GoalIn, uid: str = Depends(user_id)) -> dict[str, bool]:
    """Edit a goal; a changed monthly plan is recorded on the timeline."""
    old = db.one("SELECT * FROM goals WHERE id=? AND uid=?", (gid, uid))
    db.run("UPDATE goals SET name=?,target_amount=?,saved=?,target_date=?,monthly_contrib=? WHERE id=? AND uid=?",
           (body.name, body.target_amount, body.saved, body.target_date.isoformat(), body.monthly_contrib, gid, uid))
    if old and old["monthly_contrib"] != body.monthly_contrib:
        timeline.log(uid, "goal", f"{body.name}: monthly plan {an.inr(old['monthly_contrib'])} -> "
                     f"{an.inr(body.monthly_contrib)}", "", "Edited in Plan")
    return {"ok": True}


@router.delete("/goals/{gid}")
def del_goal(gid: int, uid: str = Depends(user_id)) -> dict[str, bool]:
    """Delete a goal."""
    g = db.one("SELECT name FROM goals WHERE id=? AND uid=?", (gid, uid))
    db.run("DELETE FROM goals WHERE id=? AND uid=?", (gid, uid))
    if g:
        timeline.log(uid, "goal", f"Goal removed: {g['name']}", "", "Deleted in Plan")
    return {"ok": True}


@router.get("/subscriptions")
def subscriptions(uid: str = Depends(user_id)) -> dict[str, Any]:
    """Recurring payments with alerts, plus upcoming UPI AutoPay mandates."""
    subs = an.detect_recurring(uid)
    mand = []
    for m in db.kv_get(uid, "mandates", {}).values():
        cur = next((s for s in subs if s["merchant"] == m["merchant"]), None)
        mand.append({**m, "current_amount": cur["amount"] if cur else None,
                     "changed": bool(cur and abs(cur["amount"] - m["amount"]) > MANDATE_CHANGE_RUPEES)})
    total = round(sum(s["monthly_cost"] for s in subs if s["kind"] == "subscription"))
    return {"items": subs, "mandates": mand, "monthly_total": total}


@router.put("/subscriptions/{merchant}/used")
def mark_used(merchant: str, body: UsedIn, uid: str = Depends(user_id)) -> dict[str, Any]:
    """Record that a subscription was used recently (clears the seems-unused alert)."""
    d = (body.last_used or an.as_of(uid)).isoformat()
    db.run("INSERT OR REPLACE INTO sub_meta(uid,merchant,last_used) VALUES(?,?,?)", (uid, merchant[:MAX_MERCHANT_CHARS], d))
    timeline.log(uid, "subscription", f"Marked {merchant.title()} as used", "", "Resets the seems-unused alert.")
    return {"ok": True, "last_used": d}


@router.post("/simulate")
def simulate(body: SimIn, uid: str = Depends(user_id)) -> dict[str, Any]:
    """One-shot what-if on category / income changes."""
    adjs = [a.model_dump(exclude_none=True) for a in body.adjustments if a.percent is not None or a.amount is not None]
    sim = planner.simulate(uid, adjs)
    sim["summary"] = planner.summarize_sim(sim)
    return sim


@router.post("/life-events")
def life_events(body: LifeIn, uid: str = Depends(user_id)) -> dict[str, Any]:
    """Month-by-month life event simulation (deterministic)."""
    return lifeevents.simulate(uid, body.as_dicts())


@router.post("/life-events/narrate")
def life_narrate(body: LifeIn, uid: str = Depends(ai_limited)) -> dict[str, Any]:
    """Gemini explanation of a life event simulation (cached; deterministic summary as fallback)."""
    return lifeevents.narrate(uid, body.as_dicts())


@router.get("/timeline")
def get_timeline(uid: str = Depends(user_id)) -> list[dict]:
    """The living money model timeline."""
    return timeline.build(uid)
