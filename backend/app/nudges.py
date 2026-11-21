"""Drift nudges: deterministic comparison of this month's pace against the plan (budgets, goals, subscriptions)."""
import calendar

from . import analytics as an
from . import planner
from .config import DRIFT_TOLERANCE, MANDATE_CHANGE_RUPEES, MIN_DAY_FOR_PACE, MIN_SPIKE_BASE, SPIKE_RATIO

FRONT_LOADED = {"Subscriptions", "Rent", "Utilities", "EMI & Loans", "Insurance"}  # bills land on fixed dates
NO_SPIKE = FRONT_LOADED | {"Other", "Education", "Health", "Savings & Investments"}


def budget_drift(spent, budget, day, dim, prorate=True):
    """-> None | dict(level, projected). level 'over' if already past budget, 'drift' if pace will exceed by >10%."""
    if budget <= 0:
        return None
    if spent > budget:
        return {"level": "over", "projected": spent / max(day, 1) * dim}
    if prorate and day >= MIN_DAY_FOR_PACE and day < dim:
        proj = spent / day * dim
        if proj > budget * DRIFT_TOLERANCE:
            return {"level": "drift", "projected": proj}
    return None


def generate(uid):
    txns = an.get_txns(uid)
    if not txns:
        return []
    ao = an.as_of(uid, txns)
    dim = calendar.monthrange(ao.year, ao.month)[1]
    cur = ao.strftime("%Y-%m")
    mon = an.monthly(txns).get(cur, {"by_cat": {}, "spend": 0})
    prof = planner.get_profile(uid)
    base = an.baseline(uid, txns)
    out = []
    left = dim - ao.day
    for cat, budget in sorted(prof["budgets"].items()):
        spent = mon["by_cat"].get(cat, 0.0)
        d = budget_drift(spent, budget, ao.day, dim, prorate=cat not in FRONT_LOADED)
        if not d:
            continue
        proj = d["projected"]
        if d["level"] == "over":
            title = f"{cat} is over budget"
            body = (f"You've spent {an.inr(spent)} on {cat} against a {an.inr(budget)} budget "
                    f"({spent / budget * 100:.0f}%) with {left} day(s) left. ")
            body += f"At this pace the month ends near {an.inr(proj)}."
            sev = "alert"
        else:
            allowed = max(budget - spent, 0)
            title = f"{cat} is drifting above plan"
            body = (f"{an.inr(spent)} spent on {cat} by day {ao.day}; at this pace you'll reach ~{an.inr(proj)} vs a "
                    f"{an.inr(budget)} budget. Staying within budget means about {an.inr(allowed / left) if left else an.inr(0)}/day "
                    f"for the remaining {left} days.")
            sev = "warn"
        usual = base["by_cat"].get(cat)
        if usual:
            body += f" Your usual month is {an.inr(usual)}."
        out.append({"id": f"budget:{cat}", "kind": "budget", "severity": sev, "title": title, "body": body,
                    "category": cat, "data": {"spent": round(spent), "budget": budget, "projected": round(proj),
                                              "days_left": left}})
    # unbudgeted categories running well above their usual month
    for cat, spent in mon["by_cat"].items():
        if cat in prof["budgets"] or cat in NO_SPIKE or ao.day < 7:
            continue
        usual = base["by_cat"].get(cat, 0)
        proj = spent / ao.day * dim
        if usual >= MIN_SPIKE_BASE and proj > usual * SPIKE_RATIO:
            out.append({"id": f"spike:{cat}", "kind": "spike", "severity": "info", "category": cat,
                        "title": f"{cat} is running high this month",
                        "body": f"{cat} is on pace for ~{an.inr(proj)} vs your usual {an.inr(usual)}. "
                                f"Set a budget for it to get tracked nudges.",
                        "data": {"spent": round(spent), "usual": round(usual), "projected": round(proj)}})
    snap = planner.snapshot(uid)
    for g in snap["goals"]["items"]:
        if g["remaining"] > 0 and not g["on_track"] and g["kind"] == "goal":
            out.append({"id": f"goal:{g['id']}", "kind": "goal", "severity": "warn",
                        "title": f"{g['name']} is behind schedule",
                        "body": f"To hit {g['target_date']} you'd need {an.inr(g['required_monthly'])}/month; your plan "
                                f"funds {an.inr(g['contribution'])}. Gap: {an.inr(g['gap'])}/month. "
                                f"Try the what-if simulator to close it.",
                        "data": {"goal_id": g["id"], "gap": g["gap"]}})
    ef = snap["emergency_months"]
    tgt = prof["emergency_target_months"]
    if ef is not None and tgt and ef < tgt:
        out.append({"id": "emergency", "kind": "emergency", "severity": "info" if ef >= 3 else "warn",
                    "title": "Emergency fund below target",
                    "body": f"Your fund covers {ef} months of essential spending; the target is {tgt:.0f}.",
                    "data": {"months": ef, "target": tgt}})
    for r in an.detect_recurring(uid, txns):
        for a in r["alerts"]:
            if a["type"] in ("price_change", "unused"):
                out.append({"id": f"sub:{r['merchant']}:{a['type']}", "kind": "subscription",
                            "severity": a["severity"], "title": f"{r['merchant'].title()}: "
                            f"{'price change' if a['type'] == 'price_change' else 'looks unused'}",
                            "body": a["message"], "data": {"merchant": r["merchant"]}})
    from . import db
    for m in db.kv_get(uid, "mandates", {}).values():
        cur = next((r for r in an.detect_recurring(uid, txns) if r["merchant"] == m["merchant"]), None)
        if cur and abs(cur["amount"] - m["amount"]) > MANDATE_CHANGE_RUPEES:
            out.append({"id": f"mandate:{m['merchant']}", "kind": "subscription", "severity": "warn",
                        "title": f"UPI AutoPay: {m['merchant'].title()} is about to cost more",
                        "body": f"Your UPI AutoPay mandate will debit {an.inr(m['amount'])} on {m['date']}, up from "
                                f"{an.inr(cur['amount'])}. Review or revoke it in your UPI app before the debit.",
                        "data": {"merchant": m["merchant"]}})
    order = {"alert": 0, "warn": 1, "info": 2}
    out.sort(key=lambda n: order[n["severity"]])
    return out
