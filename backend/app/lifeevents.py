"""Life event simulator: month-by-month projection of free cash, emergency fund and goals under combined
scenarios (salary change, job loss, rent increase, new EMI). Deterministic - no AI in the maths.

Event types (all offsets are months from the data's 'as of' month; start defaults to 1 = next month):
  salary_change {percent, start}
  job_loss      {months, start, cut_pct (discretionary cut while unemployed, default 0)}
  rent_increase {amount, start}          (any ongoing monthly expense increase)
  new_emi       {amount, start, months}  (default 36 months)
During a job loss income is zero, SIPs are paused, goal contributions stop and the emergency fund pays the deficit.
"""
import json

from . import analytics as an
from . import gemini, guardrails, planner
from .categorize import ESSENTIAL

HORIZON = 48


def _active(ev, t):
    s = int(ev.get("start", 1))
    if t < s:
        return False
    d = ev.get("months")
    return d is None or t < s + int(d)


def _model(uid):
    txns = an.get_txns(uid)
    base = an.baseline(uid, txns)
    prof = planner.get_profile(uid)
    today = an.as_of(uid, txns)
    income = planner.effective_income(uid, base, prof)
    ess = sum(v for k, v in base["by_cat"].items() if k in ESSENTIAL)
    items = []
    for g in planner.list_goals(uid):
        items.append({"id": g["id"], "name": g["name"], "kind": "goal", "target": g["target_amount"],
                      "saved": g["saved"], "target_date": g["target_date"], "planned": g["monthly_contrib"]})
    ef_target = round(prof["emergency_target_months"] * ess) if prof["emergency_target_months"] and ess else 0
    return base, prof, today, income, ess, items, ef_target


def run(uid, events, horizon=HORIZON):
    base, prof, today, income0, ess, items, ef_target = _model(uid)
    spend0, invested0 = base["spend"], base["invested"]
    disc0 = sum(v for k, v in base["by_cat"].items() if k not in ESSENTIAL)
    ef = float(prof["emergency_fund"])
    ef_planned = float(prof["emergency_monthly"])
    saved = {i["id"]: float(i["saved"]) for i in items}
    done = {}
    ef_series, goals_series, free_series = [round(ef)], [round(sum(saved.values()))], []
    depleted = None
    for t in range(1, horizon + 1):
        income, spend, invested, jobloss = income0, spend0, invested0, False
        for ev in events:
            if not _active(ev, t):
                continue
            k = ev["type"]
            if k == "salary_change":
                income *= 1 + float(ev.get("percent", 0)) / 100
            elif k == "job_loss":
                jobloss = True
                income = 0.0
                invested = 0.0
                spend -= disc0 * float(ev.get("cut_pct", 0)) / 100
            elif k in ("rent_increase", "new_emi", "expense"):
                spend += float(ev.get("amount", 0))
        free = income - spend - invested
        free_series.append(round(free))
        if free < 0:
            ef += free  # emergency fund pays the deficit
            if ef <= 0:
                ef = 0.0
                depleted = depleted or t
        else:
            active = [i for i in items if saved[i["id"]] < i["target"]]
            ef_active = ef_target and ef < ef_target
            planned = {i["id"]: i["planned"] for i in active}
            tot = sum(planned.values()) + (ef_planned if ef_active else 0)
            scale = 1.0 if tot <= 0 else min(1.0, free / tot)
            contrib = {i: p * scale for i, p in planned.items()}
            ef_add = ef_planned * scale if ef_active else 0.0
            extra = max(0.0, free - tot) if tot > 0 else free
            needs = {}
            for i in active:
                if i["target_date"]:
                    left = max(an.months_between(an.add_months(today, t - 1), an.parse_d(i["target_date"])), 0.5)
                    needs[i["id"]] = max(0.0, (i["target"] - saved[i["id"]]) / left - contrib[i["id"]])
            ns = sum(needs.values())
            if extra > 0 and ns > 0:
                for i, n in needs.items():
                    contrib[i] += min(n, extra * n / ns)
            for i in active:
                saved[i["id"]] = min(i["target"], saved[i["id"]] + contrib[i["id"]])
            ef = min(ef + ef_add, ef_target) if ef_target and ef_add else ef + ef_add
        for i in items:
            if i["id"] not in done and saved[i["id"]] >= i["target"] - 0.01:
                done[i["id"]] = t
        ef_series.append(round(ef))
        goals_series.append(round(sum(saved.values())))
    goals = []
    for i in items:
        t = done.get(i["id"])
        d = an.add_months(today, t) if t is not None else None
        goals.append({"id": i["id"], "name": i["name"], "target": i["target"], "target_date": i["target_date"],
                      "completion_month": t, "completion_date": d.isoformat() if d else None,
                      "on_track": bool(d and an.parse_d(i["target_date"]) >= d), "saved_end": round(saved[i["id"]])})
    ef_done = next((t for t, v in enumerate(ef_series) if ef_target and v >= ef_target), None)
    lo = min(ef_series)
    return {"ef": ef_series, "goals_total": goals_series, "free": free_series, "goals": goals, "ef_target": ef_target,
            "ef_low": lo, "ef_low_month": ef_series.index(lo), "ef_depleted_month": depleted,
            "ef_target_month": ef_done, "essential_spend": round(ess), "as_of": today.isoformat()}


def simulate(uid, events, horizon=HORIZON):
    before, after = run(uid, [], horizon), run(uid, events, horizon)
    today = an.parse_d(before["as_of"])
    rows = []
    bg = {g["id"]: g for g in before["goals"]}
    for g in after["goals"]:
        b = bg[g["id"]]
        shift = None
        if g["completion_month"] is not None and b["completion_month"] is not None:
            shift = g["completion_month"] - b["completion_month"]
        rows.append({**g, "before_date": b["completion_date"], "before_on_track": b["on_track"],
                     "after_date": g["completion_date"], "after_on_track": g["on_track"], "shift_months": shift,
                     "not_in_horizon": g["completion_month"] is None})
    labels = [an.add_months(today, i).strftime("%Y-%m") for i in range(horizon + 1)]
    marks = [{"month": int(e.get("start", 1)), "label": _label(e)} for e in events]
    ess = after["essential_spend"] or 1
    out = {"labels": labels, "before": before, "after": after, "goals": rows, "marks": marks,
           "ef_runway_low_months": round(after["ef_low"] / ess, 1), "ef_runway_before_months": round(before["ef_low"] / ess, 1)}
    out["summary"] = summarize(out)
    return out


def _label(e):
    k = e["type"]
    if k == "salary_change":
        return f"Salary {float(e.get('percent', 0)):+.0f}%"
    if k == "job_loss":
        return f"Job loss {int(e.get('months', 3))} mo"
    if k == "rent_increase":
        return f"Rent +{an.inr(float(e.get('amount', 0)))}"
    if k == "new_emi":
        return f"New EMI {an.inr(float(e.get('amount', 0)))}"
    return k


def summarize(sim):
    a, b = sim["after"], sim["before"]
    parts = []
    if a["ef_depleted_month"]:
        parts.append(f"The emergency fund runs out in month {a['ef_depleted_month']} - this scenario is not survivable on savings alone.")
    elif a["ef_low"] < b["ef_low"] or a["ef_low"] < b["ef"][0]:
        parts.append(f"The emergency fund dips to {an.inr(a['ef_low'])} (about {sim['ef_runway_low_months']} months of essentials) in month {a['ef_low_month']}.")
    for g in sim["goals"]:
        if g["not_in_horizon"]:
            parts.append(f"{g['name']} is not reached within {HORIZON // 12} years.")
        elif g["shift_months"]:
            parts.append(f"{g['name']} moves {'later' if g['shift_months'] > 0 else 'sooner'} by {abs(g['shift_months'])} month(s)"
                         f"{'' if g['after_on_track'] else ' and misses its target date'}.")
    if a["ef_target_month"] is not None and b["ef_target_month"] is not None and a["ef_target_month"] != b["ef_target_month"]:
        d = a["ef_target_month"] - b["ef_target_month"]
        parts.append(f"Full emergency fund {'delayed' if d > 0 else 'reached earlier'} by {abs(d)} month(s).")
    return " ".join(parts) or "No meaningful change to your goals or emergency fund."


def narrate(uid, events):
    """Gemini explanation of an already-computed simulation (cached); deterministic summary as fallback."""
    sim = simulate(uid, events)
    facts = {"events": [m["label"] for m in sim["marks"]], "summary": sim["summary"],
             "emergency_fund_low": sim["after"]["ef_low"], "runway_months_at_low": sim["ef_runway_low_months"],
             "ef_depleted_month": sim["after"]["ef_depleted_month"],
             "goals": [{k: g[k] for k in ("name", "before_date", "after_date", "target_date", "after_on_track")} for g in sim["goals"]]}
    prompt = ("Explain this life-event scenario to the user in 3 short sentences (Indian rupee formatting) and give ONE "
              "practical, non-product step to prepare. Use only these facts; do not mention any investment product.\n"
              + json.dumps(facts, ensure_ascii=False))
    text = gemini.generate(prompt, system=guardrails.SYSTEM_RULES, cache_key="life|" + json.dumps(facts, sort_keys=True))
    if text:
        text = guardrails.sanitize_output(text)
    return {"text": text or sim["summary"], "ai": bool(text)}
