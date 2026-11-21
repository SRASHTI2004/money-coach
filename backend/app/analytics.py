"""Deterministic money maths: monthly aggregates, baseline, recurring/subscription detection. No AI here."""
import calendar
import statistics
from datetime import date, timedelta

from . import db
from .categorize import NON_SPEND


def inr(v, sign=False):
    """Indian digit grouping: 1234567.5 -> '₹12,34,568'."""
    n = round(abs(v))
    s = str(n)
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts) + "," + tail
    pre = "-" if v < 0 else ("+" if sign and v > 0 else "")
    return f"{pre}₹{s}"


def parse_d(s):
    return date.fromisoformat(s)


def add_months(d: date, n: int) -> date:
    m = d.month - 1 + n
    y, m = d.year + m // 12, m % 12 + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def months_between(a: date, b: date) -> float:
    return (b - a).days / 30.4375


def get_txns(uid):
    return db.rows("SELECT * FROM transactions WHERE uid=? ORDER BY date, id", (uid,))


def as_of(uid, txns=None):
    txns = txns if txns is not None else get_txns(uid)
    return parse_d(max(t["date"] for t in txns)) if txns else date.today()


def monthly(txns):
    """{'2026-09': {'income','spend','invested','by_cat':{}}}"""
    out = {}
    for t in txns:
        m = out.setdefault(t["date"][:7], {"income": 0.0, "spend": 0.0, "invested": 0.0, "by_cat": {}})
        a, c = t["amount"], t["category"]
        if c == "Income" and a > 0:
            m["income"] += a
        elif c == "Savings & Investments":
            m["invested"] += -a
        elif c in NON_SPEND:
            continue
        elif a < 0:
            m["spend"] += -a
            m["by_cat"][c] = m["by_cat"].get(c, 0.0) + -a
        elif a > 0:  # refunds reduce spend
            m["spend"] -= a
            m["by_cat"][c] = m["by_cat"].get(c, 0.0) - a
    return out


def baseline(uid, txns=None):
    """Average of up to 3 complete months before the latest month (or the latest month alone if that is all we have)."""
    txns = txns if txns is not None else get_txns(uid)
    if not txns:
        return {"months": [], "income": 0.0, "spend": 0.0, "invested": 0.0, "by_cat": {}, "free_cash": 0.0}
    ao = as_of(uid, txns)
    mon = monthly(txns)
    cur = ao.strftime("%Y-%m")
    last_day = calendar.monthrange(ao.year, ao.month)[1]
    complete = sorted(k for k in mon if k < cur or (k == cur and ao.day >= last_day))
    use = complete[-3:] or [cur]
    n = len(use)
    cats = {}
    for k in use:
        for c, v in mon[k]["by_cat"].items():
            cats[c] = cats.get(c, 0.0) + v / n
    b = {"months": use, "income": sum(mon[k]["income"] for k in use) / n,
         "spend": sum(mon[k]["spend"] for k in use) / n, "invested": sum(mon[k]["invested"] for k in use) / n,
         "by_cat": {c: round(v, 2) for c, v in cats.items()}}
    b["free_cash"] = b["income"] - b["spend"]
    return b


# ------------------------------------------------------------------ recurring detection
CADENCES = [("weekly", 6, 8, 7), ("monthly", 25, 35, 30), ("quarterly", 84, 98, 91), ("yearly", 350, 380, 365)]
STREAMING = {"netflix", "hotstar", "primevideo", "sonyliv", "zee5", "jiocinema", "youtube"}
SKIP_RECURRING = {"Income", "Cash", "Transfers"}
DISCRETIONARY = {"Shopping", "Dining", "Groceries", "Transport", "Health", "Other", "Travel", "Entertainment"}


def detect_recurring(uid, txns=None):
    txns = txns if txns is not None else get_txns(uid)
    if not txns:
        return []
    ao = as_of(uid, txns)
    meta = {m["merchant"]: m["last_used"] for m in db.rows("SELECT * FROM sub_meta WHERE uid=?", (uid,))}
    groups = {}
    for t in txns:
        if t["amount"] < 0 and t["category"] not in SKIP_RECURRING and t["merchant"] != "unknown":
            groups.setdefault(t["merchant"], []).append(t)
    found = []
    for key, rows in groups.items():
        days = {}
        for r in rows:  # collapse same-day duplicates
            days.setdefault(r["date"], 0.0)
            days[r["date"]] += -r["amount"]
        ds = sorted(days)
        need = 3
        if len(ds) < 2:
            continue
        gaps = [(parse_d(b) - parse_d(a)).days for a, b in zip(ds, ds[1:])]
        med = statistics.median(gaps)
        cad = next((c for c in CADENCES if c[1] <= med <= c[2]), None)
        if not cad:
            continue
        ok = sum(1 for g in gaps if cad[1] <= g <= cad[2]) / len(gaps)
        need = 3 if cad[0] in ("weekly", "monthly") else 2
        if len(ds) < need or ok < 0.7:
            continue
        amts = [days[d] for d in ds]
        med_amt = statistics.median(amts)
        spread = (max(amts) - min(amts)) / med_amt if med_amt else 0
        fixed = spread <= 0.05
        cat0 = rows[-1]["category"]
        if cat0 in DISCRETIONARY and not fixed:
            continue  # irregular shopping/dining/etc. that merely happened monthly is not a subscription
        # price change: most recent step >2% where the charge was stable (>=2 equal charges) beforehand
        change = None
        for i in range(len(amts) - 1, 0, -1):
            if abs(amts[i] - amts[i - 1]) / amts[i - 1] > 0.02:
                before = amts[:i]
                stable = len(before) >= 2 and all(abs(a - before[-1]) / before[-1] <= 0.02 for a in before[-2:])
                if stable and (ao - parse_d(ds[i])).days <= 75:
                    change = {"old": amts[i - 1], "new": amts[i], "date": ds[i],
                              "pct": round((amts[i] - amts[i - 1]) / amts[i - 1] * 100, 1)}
                break
        last = parse_d(ds[-1])
        nxt = last + timedelta(days=cad[3])
        cat = rows[-1]["category"]
        name = rows[-1]["description"]
        monthly_cost = amts[-1] * {"weekly": 4.345, "monthly": 1, "quarterly": 1 / 3, "yearly": 1 / 12}[cad[0]]
        kind = "saving" if cat == "Savings & Investments" else \
            "subscription" if cat in ("Subscriptions", "Entertainment") else "bill"
        alerts = []
        if change and kind != "saving":
            up = change["pct"] > 0
            alerts.append({"type": "price_change", "severity": "warn" if up else "info",
                           "message": f"{key.title()} {'rose' if up else 'dropped'} from {inr(change['old'])} to "
                                      f"{inr(change['new'])} ({change['pct']:+.0f}%) on {change['date']}. "
                                      f"That's {inr(abs(change['new'] - change['old']) * 12)}/year "
                                      f"{'more' if up else 'less'}."})
        lu = meta.get(key)
        if kind == "subscription" and lu:
            idle = (ao - parse_d(lu)).days
            if idle > 45:
                alerts.append({"type": "unused", "severity": "warn",
                               "message": f"You haven't used {key.title()} in {idle} days (last used {lu}) but it still "
                                          f"costs {inr(amts[-1])}/{cad[0][:-2] if cad[0] != 'weekly' else 'week'}. "
                                          f"Cancelling would free ~{inr(monthly_cost * 12)}/year."})
        found.append({"merchant": key, "name": name, "category": cat, "kind": kind, "cadence": cad[0],
                      "amount": round(amts[-1], 2), "typical": round(med_amt, 2), "fixed_amount": bool(fixed),
                      "count": len(ds), "first_date": ds[0], "last_date": ds[-1], "next_date": nxt.isoformat(),
                      "monthly_cost": round(monthly_cost, 2), "last_used": lu, "price_change": change,
                      "alerts": alerts})
    streaming = [f for f in found if f["merchant"] in STREAMING]
    if len(streaming) >= 2:
        tot = sum(f["monthly_cost"] for f in streaming)
        names = ", ".join(f["merchant"].title() for f in streaming)
        for f in streaming:
            f["alerts"].append({"type": "overlap", "severity": "info",
                                "message": f"You pay for {len(streaming)} video/music services ({names}) totalling "
                                           f"{inr(tot)}/month. Keeping fewer could save money."})
    for f in found:
        if 0 <= (parse_d(f["next_date"]) - ao).days <= 3 and f["kind"] != "saving":
            f["alerts"].append({"type": "upcoming", "severity": "info",
                                "message": f"{f['merchant'].title()} is due around {f['next_date']} ({inr(f['amount'])})."})
    found.sort(key=lambda f: -f["monthly_cost"])
    return found
