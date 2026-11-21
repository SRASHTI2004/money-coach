"""Persistent financial profile, goals, and the deterministic what-if simulator."""
import math
from datetime import date

from . import analytics as an
from . import db
from .categorize import ESSENTIAL

DEFAULT_PROFILE = {"monthly_income": None, "fixed_costs": [], "emergency_fund": 0.0,
                   "emergency_target_months": 6, "emergency_monthly": 0.0, "budgets": {}}


def get_profile(uid):
    p = dict(DEFAULT_PROFILE)
    p.update(db.kv_get(uid, "profile", {}) or {})
    return p


def save_profile(uid, patch: dict):
    p = get_profile(uid)
    for k in DEFAULT_PROFILE:
        if k in patch:
            p[k] = patch[k]
    p["budgets"] = {k: float(v) for k, v in (p.get("budgets") or {}).items() if v not in (None, "")}
    p["fixed_costs"] = [{"name": str(f["name"]), "amount": float(f["amount"])} for f in p.get("fixed_costs") or []]
    p["monthly_income"] = float(p["monthly_income"]) if p.get("monthly_income") else None
    for k in ("emergency_fund", "emergency_monthly", "emergency_target_months"):
        p[k] = float(p[k] or 0)
    db.kv_set(uid, "profile", p)
    return p


def list_goals(uid):
    return db.rows("SELECT * FROM goals WHERE uid=? ORDER BY target_date", (uid,))


def effective_income(uid, base, prof):
    return float(prof["monthly_income"]) if prof.get("monthly_income") else base["income"]


# ------------------------------------------------------------------ projection
def project_goals(goals, prof, free_cash, monthly_spend, today):
    """Allocate free cash to planned contributions (scaled down pro-rata if short) and project each goal."""
    items = []
    for g in goals:
        items.append({"id": g["id"], "name": g["name"], "kind": "goal", "target": g["target_amount"],
                      "saved": g["saved"], "target_date": g["target_date"], "planned": g["monthly_contrib"]})
    if prof["emergency_target_months"] and monthly_spend > 0:
        items.append({"id": "ef", "name": "Emergency fund", "kind": "emergency",
                      "target": round(prof["emergency_target_months"] * monthly_spend),
                      "saved": prof["emergency_fund"], "target_date": None, "planned": prof["emergency_monthly"]})
    total = sum(i["planned"] for i in items)
    scale = 1.0 if total <= 0 else min(1.0, max(free_cash, 0) / total)
    for i in items:
        i["remaining"] = round(max(0.0, i["target"] - i["saved"]), 2)
        i["contribution"] = i["planned"] * scale
        i["pct"] = round(min(100, i["saved"] / i["target"] * 100), 1) if i["target"] else 100
        if i["target_date"]:
            ml = max(an.months_between(today, an.parse_d(i["target_date"])), 0.0)
            i["required_monthly"] = i["remaining"] / ml if ml > 0.1 else i["remaining"]
        else:
            i["required_monthly"] = None
    # Surplus beyond the plan is routed to dated goals that are behind (largest gap first, pro-rata, capped at gap).
    extra = max(0.0, free_cash - total) if total > 0 else max(0.0, free_cash)
    gaps = {i["id"]: max(0.0, i["required_monthly"] - i["contribution"]) for i in items
            if i["kind"] == "goal" and i["required_monthly"] and i["remaining"] > 0}
    gsum = sum(gaps.values())
    routed = 0.0
    if extra > 0 and gsum > 0:
        for i in items:
            if i["id"] in gaps:
                add = min(gaps[i["id"]], extra * gaps[i["id"]] / gsum)
                i["contribution"] += add
                routed += add
    for i in items:
        remaining, contrib = i["remaining"], i["contribution"]
        i["contribution"] = round(contrib, 2)
        if remaining == 0:
            i.update(months_to_go=0, projected_date=today.isoformat(), on_track=True, required_monthly=0.0, gap=0.0)
            continue
        months = math.ceil(remaining / contrib) if contrib > 0 else None
        i["months_to_go"] = months
        i["projected_date"] = an.add_months(today, months).isoformat() if months is not None else None
        if i["target_date"]:
            i["required_monthly"] = round(i["required_monthly"], 2)
            i["gap"] = round(max(0.0, i["required_monthly"] - contrib), 2)
            i["on_track"] = bool(months is not None and an.parse_d(i["projected_date"]) <= an.parse_d(i["target_date"]))
        else:
            i["gap"] = 0.0
            i["on_track"] = months is not None
    return {"items": items, "planned_total": round(total, 2), "scale": round(scale, 3), "routed_extra": round(routed, 2),
            "unallocated": round(max(0.0, extra - routed), 2)}


def snapshot(uid, adjustments=None, today=None):
    """Baseline model; with adjustments applies them deterministically.
    adjustment = {category, percent?, amount?}: percent>0 raises, <0 cuts; amount = monthly rupee delta.
    category 'Income' adjusts income; any other name not in history is a new monthly expense."""
    txns = an.get_txns(uid)
    base = an.baseline(uid, txns)
    prof = get_profile(uid)
    today = today or an.as_of(uid, txns)
    income = effective_income(uid, base, prof)
    cats = dict(base["by_cat"])
    applied = []
    for adj in adjustments or []:
        c = adj.get("category")
        pct, amt = adj.get("percent"), adj.get("amount")
        if c == "Income":
            old = income
            income = max(0.0, income * (1 + pct / 100) if pct is not None else income + (amt or 0))
            applied.append({"category": c, "from": round(old), "to": round(income)})
            continue
        key = next((k for k in cats if k.lower() == str(c).lower()), c)
        old = cats.get(key, 0.0)
        new = old * (1 + pct / 100) if pct is not None else old + (amt or 0)
        cats[key] = max(0.0, new)
        applied.append({"category": key, "from": round(old), "to": round(cats[key])})
    spend = sum(cats.values())
    free = income - spend - base["invested"]  # after existing SIP/investment outflows
    ess = sum(v for k, v in cats.items() if k in ESSENTIAL)
    proj = project_goals(list_goals(uid), prof, free, ess, today)
    ef_months = round(prof["emergency_fund"] / ess, 1) if ess > 0 else None
    return {"as_of": today.isoformat(), "income": round(income, 2), "spend": round(spend, 2), "free_cash": round(free, 2),
            "invested": round(base["invested"], 2), "essential_spend": round(ess, 2), "by_cat": {k: round(v, 2) for k, v in cats.items()},
            "emergency_months": ef_months, "goals": proj, "applied": applied}


def simulate(uid, adjustments):
    before = snapshot(uid)
    after = snapshot(uid, adjustments)
    changes = []
    bg = {g["id"]: g for g in before["goals"]["items"]}
    for g in after["goals"]["items"]:
        b = bg.get(g["id"], {})
        shift = None
        if g.get("projected_date") and b.get("projected_date"):
            shift = round(an.months_between(an.parse_d(b["projected_date"]), an.parse_d(g["projected_date"])), 1)
        changes.append({"id": g["id"], "name": g["name"], "before_date": b.get("projected_date"),
                        "after_date": g.get("projected_date"), "shift_months": shift,
                        "before_on_track": b.get("on_track"), "after_on_track": g["on_track"],
                        "target_date": g["target_date"], "gap_after": g["gap"]})
    return {"before": before, "after": after, "delta_free_cash": round(after["free_cash"] - before["free_cash"], 2),
            "delta_yearly": round((after["free_cash"] - before["free_cash"]) * 12, 2), "goal_changes": changes}


def summarize_sim(sim):
    """Plain-language deterministic summary (also the non-AI fallback)."""
    d = sim["delta_free_cash"]
    parts = [f"Monthly free cash goes from {an.inr(sim['before']['free_cash'])} to {an.inr(sim['after']['free_cash'])} "
             f"({an.inr(d, sign=True)}/month, {an.inr(sim['delta_yearly'], sign=True)}/year)."]
    for g in sim["goal_changes"]:
        if g["shift_months"] and abs(g["shift_months"]) >= 0.5:
            parts.append(f"{g['name']}: {'later' if g['shift_months'] > 0 else 'sooner'} by {abs(g['shift_months']):.0f} month(s)"
                         f"{'' if g['after_on_track'] else ' - no longer on track for its target date'}.")
        elif g["before_on_track"] != g["after_on_track"]:
            parts.append(f"{g['name']}: {'now on track' if g['after_on_track'] else 'falls off track'}.")
    return " ".join(parts)
