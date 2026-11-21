"""Living money model timeline: a dated history of how the profile changed and WHY.
Two sources: events the app logged (profile edits, goals, rules, imports, confirmed proposals) and events
detected from the data itself (new/cancelled subscriptions, price changes, new income, salary changes)."""
from datetime import date

from . import analytics as an
from . import db


def _clean(desc):
    import re
    return re.sub(r"(?i)^(neft|imps|rtgs|upi)[- ]+", "", desc).replace("-", " ").title()[:40]


def _today(uid):
    return an.as_of(uid).isoformat() if db.one("SELECT 1 FROM transactions WHERE uid=? LIMIT 1", (uid,)) \
        else date.today().isoformat()


def log(uid, kind, title, detail="", why="", on=None):
    db.run("INSERT INTO events(uid,date,kind,title,detail,why) VALUES(?,?,?,?,?,?)",
           (uid, on or _today(uid), kind, title, detail, why))


def log_profile_change(uid, old, new, why="Edited in Plan"):
    if (new.get("monthly_income") or 0) != (old.get("monthly_income") or 0) and new.get("monthly_income"):
        log(uid, "income", f"Income set to {an.inr(new['monthly_income'])}/month",
            f"was {an.inr(old.get('monthly_income') or 0)}", why)
    if new.get("emergency_fund") != old.get("emergency_fund"):
        log(uid, "emergency", f"Emergency fund updated to {an.inr(new['emergency_fund'])}",
            f"was {an.inr(old.get('emergency_fund') or 0)}", why)
    if new.get("emergency_monthly") != old.get("emergency_monthly"):
        log(uid, "emergency", f"Emergency top-up now {an.inr(new['emergency_monthly'])}/month", "", why)
    for c, v in (new.get("budgets") or {}).items():
        ov = (old.get("budgets") or {}).get(c)
        if ov != v:
            log(uid, "budget", f"{c} budget {'set to' if ov is None else 'changed to'} {an.inr(v)}",
                f"was {an.inr(ov)}" if ov is not None else "", why)


def detected(uid):
    """Events inferred from transactions - no logging needed, always consistent with the data."""
    txns = an.get_txns(uid)
    if not txns:
        return []
    out = []
    first = min(t["date"] for t in txns)
    found = an.detect_recurring(uid, txns)
    for r in found:
        if r["kind"] == "subscription" and (an.parse_d(r["first_date"]) - an.parse_d(first)).days > 20:
            out.append({"date": r["first_date"], "kind": "subscription", "source": "detected",
                        "title": f"New subscription: {r['merchant'].title()} {an.inr(r['amount'])}/{r['cadence'][:-2]}",
                        "detail": "", "why": "A new recurring charge appeared in your statements."})
        pc = r["price_change"]
        if pc:
            out.append({"date": pc["date"], "kind": "price", "source": "detected",
                        "title": f"{r['merchant'].title()} price {'rose' if pc['pct'] > 0 else 'fell'} "
                                 f"{an.inr(pc['old'])} -> {an.inr(pc['new'])}",
                        "detail": f"{pc['pct']:+.0f}%", "why": f"Detected from consecutive charges ({an.inr(abs(pc['new'] - pc['old']) * 12)}/year impact)."})
    for c in an.detect_cancelled(uid, txns, {r["merchant"] for r in found}):
        out.append({"date": c["last_date"], "kind": "cancelled", "source": "detected",
                    "title": f"{c['merchant'].title()} looks cancelled",
                    "detail": f"{an.inr(c['amount'])}/month stopped after {c['count']} charges",
                    "why": f"No charge since {c['last_date']}; that frees about {an.inr(c['amount'] * 12)}/year."})
    inc: dict[str, list] = {}
    for t in txns:
        if t["category"] == "Income" and t["amount"] > 0:
            inc.setdefault(t["merchant"], []).append(t)
    if inc:
        main = max(inc, key=lambda k: sum(x["amount"] for x in inc[k]))
        for k, rows in inc.items():
            if k != main and rows[0]["date"] > first:
                out.append({"date": rows[0]["date"], "kind": "income", "source": "detected",
                            "title": f"New income source: {_clean(rows[0]['description'])}",
                            "detail": an.inr(rows[0]["amount"]), "why": "A credit from a new payer appeared."})
        rows = sorted(inc[main], key=lambda t: t["date"])
        for a, b in zip(rows, rows[1:], strict=False):
            if abs(b["amount"] - a["amount"]) / a["amount"] > 0.03:
                out.append({"date": b["date"], "kind": "income", "source": "detected",
                            "title": f"Salary changed {an.inr(a['amount'])} -> {an.inr(b['amount'])}",
                            "detail": "", "why": "Detected from consecutive salary credits."})
    for m in db.kv_get(uid, "mandates", {}).values():
        match = next((r for r in found if r["merchant"] == m["merchant"]), None)
        if match and abs(match["amount"] - m["amount"]) > 1:
            out.append({"date": m["notice_date"], "kind": "price", "source": "detected",
                        "title": f"UPI AutoPay notice: {m['merchant'].title()} will debit {an.inr(m['amount'])}",
                        "detail": f"currently {an.inr(match['amount'])}",
                        "why": f"Upcoming mandate on {m['date']} differs from your last charge."})
    return out


def build(uid):
    logged = [{**e, "source": "logged"} for e in db.rows("SELECT date,kind,title,detail,why FROM events WHERE uid=?", (uid,))]
    items = logged + detected(uid)
    seen, out = set(), []
    for e in sorted(items, key=lambda e: e["date"], reverse=True):
        k = (e["date"], e["title"])
        if k not in seen:
            seen.add(k)
            out.append(e)
    return out
