"""Monthly review: deterministic numbers + Gemini narrative (with a template fallback)."""
import calendar
import json

from . import analytics as an
from . import gemini, guardrails, nudges, planner


def months_available(uid):
    return sorted(an.monthly(an.get_txns(uid)).keys())


def build(uid, month=None):
    txns = an.get_txns(uid)
    if not txns:
        return None
    mon = an.monthly(txns)
    keys = sorted(mon)
    month = month if month in mon else keys[-1]
    idx = keys.index(month)
    prev = mon[keys[idx - 1]] if idx > 0 else None
    cur = mon[month]
    y, m = map(int, month.split("-"))
    ao = an.as_of(uid, txns)
    partial = ao.strftime("%Y-%m") == month and ao.day < calendar.monthrange(y, m)[1]
    prof = planner.get_profile(uid)
    income = cur["income"] or (prof["monthly_income"] or 0)
    saved = income - cur["spend"]
    cats = sorted(cur["by_cat"].items(), key=lambda kv: -kv[1])
    movers = []
    if prev:
        for c, v in cur["by_cat"].items():
            pv = prev["by_cat"].get(c, 0)
            if pv > 0 and not partial:
                movers.append({"category": c, "this": round(v), "last": round(pv), "change_pct": round((v - pv) / pv * 100)})
        movers.sort(key=lambda r: -abs(r["this"] - r["last"]))
    budgets = []
    for c, b in sorted(prof["budgets"].items()):
        s = cur["by_cat"].get(c, 0)
        budgets.append({"category": c, "budget": b, "spent": round(s), "status": "over" if s > b else "within"})
    snap = planner.snapshot(uid)
    subs = an.detect_recurring(uid, txns)
    sub_total = sum(s["monthly_cost"] for s in subs if s["kind"] == "subscription")
    sub_alerts = [a["message"] for s in subs for a in s["alerts"] if a["type"] in ("price_change", "unused", "overlap")]
    facts = {
        "month": month, "partial_month": partial, "through_day": ao.day if partial else None,
        "income": round(income), "spend": round(cur["spend"]), "invested": round(cur["invested"]),
        "left_over": round(saved), "savings_rate_pct": round(saved / income * 100) if income else None,
        "top_categories": [{"category": c, "amount": round(v), "share_pct": round(v / cur["spend"] * 100) if cur["spend"] else 0}
                           for c, v in cats[:5]],
        "vs_previous_month": ({"spend_change_pct": round((cur["spend"] - prev["spend"]) / prev["spend"] * 100)
                               if prev["spend"] and not partial else None, "biggest_movers": movers[:3]}
                              if prev else None),
        "budgets": budgets,
        "goals": [{"name": g["name"], "pct_complete": g["pct"], "on_track": g["on_track"],
                   "monthly_funded": g["contribution"], "monthly_needed": g["required_monthly"]}
                  for g in snap["goals"]["items"]],
        "subscriptions": {"monthly_total": round(sub_total), "alerts": sub_alerts},
        "open_nudges": [n["title"] for n in nudges.generate(uid)][:6],
    }
    return facts


def fallback_narrative(f):
    inr = an.inr
    lines = [f"**{f['month']} at a glance.** You earned {inr(f['income'])} and spent {inr(f['spend'])}"
             + (f" (through day {f['through_day']})" if f["partial_month"] else "")
             + f", leaving {inr(f['left_over'])}" + (f" - a {f['savings_rate_pct']}% savings rate." if f["savings_rate_pct"] is not None else ".")]
    if f["top_categories"]:
        t = f["top_categories"][0]
        lines.append(f"Your biggest category was {t['category']} at {inr(t['amount'])} ({t['share_pct']}% of spend).")
    v = f["vs_previous_month"]
    if v and v["biggest_movers"]:
        mv = v["biggest_movers"][0]
        lines.append(f"Biggest change vs last month: {mv['category']} {'rose' if mv['change_pct'] > 0 else 'fell'} "
                     f"{abs(mv['change_pct'])}% ({inr(mv['last'])} -> {inr(mv['this'])}).")
    over = [b for b in f["budgets"] if b["status"] == "over"]
    lines.append("Budgets over: " + ", ".join(f"{b['category']} ({inr(b['spent'])}/{inr(b['budget'])})" for b in over) + "."
                 if over else "You stayed within every budget you set.")
    behind = [g["name"] for g in f["goals"] if not g["on_track"]]
    lines.append(("Goals behind schedule: " + ", ".join(behind) + ".") if behind else "All goals are on track.")
    if f["subscriptions"]["alerts"]:
        lines.append("Subscriptions: " + f["subscriptions"]["alerts"][0])
    lines.append("Next step: pick one nudge above and run it through the what-if simulator before committing.")
    return "\n\n".join(lines)


def narrative(uid, month=None):
    f = build(uid, month)
    if f is None:
        return None
    prompt = ("Write a warm, concise monthly money review (max ~170 words, markdown, 3 short paragraphs + 2 bullet "
              "'next steps') for an Indian user from ONLY these verified facts. Use Indian rupee formatting "
              "(e.g. ₹1,25,000). Do not invent numbers. Do not mention any investment product.\n\n"
              + json.dumps(f, ensure_ascii=False))
    text = gemini.generate(prompt, system=guardrails.SYSTEM_RULES, cache_key=json.dumps(f, sort_keys=True))
    ai = bool(text)
    text = guardrails.sanitize_output(text) if text else fallback_narrative(f)
    return {"facts": f, "narrative": text, "ai": ai and text != guardrails.EDUCATIONAL_REPLY}
