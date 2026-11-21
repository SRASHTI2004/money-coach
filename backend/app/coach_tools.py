"""Coach tools: deterministic functions the agent can call, plus the propose -> confirm mechanism.
Every number a coach answer contains comes from here; proposals are stored pending and applied only on Confirm."""
import json
import re
from collections.abc import Callable
from datetime import date
from typing import Any

from . import analytics as an
from . import db, nudges, planner, review, timeline
from .categorize import CATEGORIES

PROPOSAL_KINDS = {"set_budget", "update_goal", "create_goal", "update_profile"}
CAT_WORDS = {
    "Dining": r"dining|eating out|restaurants?|food delivery|takeaway|swiggy|zomato|cafe",
    "Groceries": r"groceries|grocery|supermarket|vegetables",
    "Rent": r"\brent\b",
    "Transport": r"transport|cabs?|commute|travel to work|fuel|petrol|uber|ola",
    "Shopping": r"shopping|clothes|online shopping|amazon",
    "Subscriptions": r"subscriptions?|streaming|ott",
    "Entertainment": r"entertainment|movies?|outings?",
    "Utilities": r"utilit(?:y|ies)|electricity|bills?|broadband",
    "Health": r"health|medical|pharmacy",
    "EMI & Loans": r"\bemi\b|loans?",
}


def find_category(text):
    low = text.lower()
    for cat, rx in CAT_WORDS.items():
        if re.search(rx, low):
            return cat
    return None


# ------------------------------------------------------------------ tools (deterministic)
def tool_get_profile(uid, **_):
    p = planner.get_profile(uid)
    snap = planner.snapshot(uid)
    return {"profile": p, "monthly_income": snap["income"], "avg_monthly_spend": snap["spend"],
            "free_cash_per_month": snap["free_cash"], "spend_by_category": snap["by_cat"],
            "emergency_months_covered": snap["emergency_months"], "as_of": snap["as_of"],
            "goals": [{k: g[k] for k in ("id", "name", "target", "saved", "target_date", "contribution",
                                          "required_monthly", "projected_date", "on_track")}
                      for g in snap["goals"]["items"]]}


def tool_run_what_if(uid, adjustments=None, **_):
    adjs = []
    for a in adjustments or []:
        a = dict(a)
        c = a.get("category", "")
        cat = "Income" if str(c).lower() == "income" else (find_category(str(c)) or c)
        adjs.append({"category": cat, **{k: float(a[k]) for k in ("percent", "amount") if a.get(k) is not None}})
    sim = planner.simulate(uid, adjs)
    return {"summary": planner.summarize_sim(sim), "applied": sim["after"]["applied"],
            "free_cash_before": sim["before"]["free_cash"], "free_cash_after": sim["after"]["free_cash"],
            "delta_per_month": sim["delta_free_cash"], "delta_per_year": sim["delta_yearly"],
            "goal_changes": sim["goal_changes"]}


def tool_list_subscriptions(uid, **_):
    return [{"merchant": s["merchant"], "amount": s["amount"], "cadence": s["cadence"], "kind": s["kind"],
             "monthly_cost": s["monthly_cost"], "next_date": s["next_date"], "last_used": s["last_used"],
             "alerts": [a["message"] for a in s["alerts"]]} for s in an.detect_recurring(uid)]


def tool_list_nudges(uid, **_):
    return [{"id": n["id"], "severity": n["severity"], "title": n["title"], "body": n["body"]}
            for n in nudges.generate(uid)]


def tool_explain_nudge(uid, nudge_id=None, **_):
    allv = nudges.generate(uid)
    n = next((x for x in allv if x["id"] == nudge_id or x["title"].lower() == str(nudge_id).lower()), None)
    if not n:
        return {"error": "nudge not found", "available": [x["id"] for x in allv]}
    out = {"nudge": n, "why": n["body"]}
    if n["kind"] == "budget":
        cat = n["category"]
        sim = tool_run_what_if(uid, [{"category": cat, "percent": -15}])
        out["if_you_trim_15pct_of_usual"] = sim["summary"]
    return out


def tool_get_spending_summary(uid, month=None, **_):
    f = review.build(uid, month)
    return f or {"error": "no data"}


def tool_propose_change(uid, kind=None, reason="", **p):
    """Validates and stores a pending proposal; NEVER applies it."""
    if kind not in PROPOSAL_KINDS:
        return {"error": f"kind must be one of {sorted(PROPOSAL_KINDS)}"}
    payload = {}
    try:
        if kind == "set_budget":
            cat = find_category(str(p.get("category", ""))) or p.get("category")
            if cat not in CATEGORIES:
                return {"error": "unknown category"}
            payload = {"category": cat, "amount": float(p["amount"])}
        elif kind == "update_goal":
            g = find_goal(uid, p.get("goal_name"))
            if not g:
                return {"error": "goal not found", "goals": [x["name"] for x in planner.list_goals(uid)]}
            payload = {"goal_id": g["id"], "goal_name": g["name"]}
            for k in ("monthly_contrib", "target_amount"):
                if p.get(k) is not None:
                    payload[k] = float(p[k])
            if p.get("target_date"):
                payload["target_date"] = date.fromisoformat(str(p["target_date"])).isoformat()
        elif kind == "create_goal":
            payload = {"name": str(p["name"]), "target_amount": float(p["target_amount"]),
                       "target_date": date.fromisoformat(str(p["target_date"])).isoformat(),
                       "saved": float(p.get("saved") or 0), "monthly_contrib": float(p.get("monthly_contrib") or 0)}
        elif kind == "update_profile":
            if p.get("field") not in ("monthly_income", "emergency_fund", "emergency_monthly", "emergency_target_months"):
                return {"error": "field not allowed"}
            payload = {"field": p["field"], "value": float(p["value"])}
    except (KeyError, ValueError, TypeError) as e:
        return {"error": f"bad arguments: {e}"}
    pid = db.run("INSERT INTO proposals(uid,kind,payload,reason) VALUES(?,?,?,?)",
                 (uid, kind, json.dumps(payload), reason))
    return {"proposal_id": pid, "status": "pending_user_confirmation", "payload": payload,
            "note": "Not applied. The user must click Confirm."}


def find_goal(uid, name):
    goals = planner.list_goals(uid)
    low = str(name or "").lower()
    return next((g for g in goals if g["name"].lower() == low), None) or \
        next((g for g in goals if low and (low in g["name"].lower() or g["name"].lower() in low)), None)


TOOLS: dict[str, Callable[..., Any]] = {"get_profile": tool_get_profile, "run_what_if": tool_run_what_if,
         "list_subscriptions": tool_list_subscriptions, "list_nudges": tool_list_nudges,
         "explain_nudge": tool_explain_nudge, "get_spending_summary": tool_get_spending_summary,
         "propose_change": tool_propose_change}


def apply_proposal(uid, pid):
    pr = db.one("SELECT * FROM proposals WHERE id=? AND uid=?", (pid, uid))
    if not pr:
        return None
    if pr["status"] != "pending":
        return {"status": pr["status"]}
    p = json.loads(pr["payload"])
    k = pr["kind"]
    if k == "set_budget":
        prof = planner.get_profile(uid)
        prof["budgets"][p["category"]] = p["amount"]
        planner.save_profile(uid, {"budgets": prof["budgets"]})
    elif k == "update_goal":
        for col in ("monthly_contrib", "target_amount", "target_date"):
            if col in p:
                db.run(f"UPDATE goals SET {col}=? WHERE id=? AND uid=?", (p[col], p["goal_id"], uid))
    elif k == "create_goal":
        db.run("INSERT INTO goals(uid,name,target_amount,saved,target_date,monthly_contrib) VALUES(?,?,?,?,?,?)",
               (uid, p["name"], p["target_amount"], p["saved"], p["target_date"], p["monthly_contrib"]))
    elif k == "update_profile":
        planner.save_profile(uid, {p["field"]: p["value"]})
    db.run("UPDATE proposals SET status='applied' WHERE id=?", (pid,))
    timeline.log(uid, "budget" if k == "set_budget" else "goal" if "goal" in k else "income",
                 describe_proposal(pr), pr["reason"] or "", "Proposed by the coach, confirmed by you.")
    return {"status": "applied", "kind": k, "payload": p}


def reject_proposal(uid, pid):
    db.run("UPDATE proposals SET status='rejected' WHERE id=? AND uid=? AND status='pending'", (pid, uid))
    return {"status": "rejected"}


def describe_proposal(pr):
    p = pr["payload"] if isinstance(pr["payload"], dict) else json.loads(pr["payload"])
    k = pr["kind"]
    if k == "set_budget":
        return f"Set {p['category']} budget to {an.inr(p['amount'])}/month"
    if k == "update_goal":
        bits = []
        if "monthly_contrib" in p:
            bits.append(f"monthly contribution {an.inr(p['monthly_contrib'])}")
        if "target_amount" in p:
            bits.append(f"target {an.inr(p['target_amount'])}")
        if "target_date" in p:
            bits.append(f"target date {p['target_date']}")
        return f"Update goal '{p['goal_name']}': " + ", ".join(bits)
    if k == "create_goal":
        return f"Create goal '{p['name']}': {an.inr(p['target_amount'])} by {p['target_date']}"
    return f"Set {p['field'].replace('_', ' ')} to {an.inr(p['value'])}"


def pending(uid, ids=None):
    rows = db.rows("SELECT * FROM proposals WHERE uid=? AND status='pending' ORDER BY id", (uid,))
    out = []
    for r in rows:
        if ids is None or r["id"] in ids:
            out.append({"id": r["id"], "kind": r["kind"], "payload": json.loads(r["payload"]), "reason": r["reason"],
                        "description": describe_proposal(r)})
    return out


def brief(name, result):
    """One-line, human-readable result of a tool call, shown in the UI as a visible 'step'."""
    try:
        if name == "run_what_if":
            return result["summary"]
        if name == "list_subscriptions":
            return f"{len(result)} recurring payments found"
        if name == "list_nudges":
            return f"{len(result)} nudges active"
        if name == "explain_nudge":
            return result.get("nudge", {}).get("title", result.get("error", "nudge"))
        if name == "get_profile":
            return f"income {an.inr(result['monthly_income'])}, free cash {an.inr(result['free_cash_per_month'])}/month"
        if name == "get_spending_summary":
            return f"{result.get('month')}: spent {an.inr(result.get('spend', 0))}"
        if name == "propose_change":
            return "proposal created - waiting for your Confirm" if "proposal_id" in result else result.get("error", "")
    except Exception:
        pass
    return ""
