"""Agentic coach: Gemini function-calling loop over deterministic tools, with a rule-based fallback.
Money maths only ever comes from tools. Changes are PROPOSED (stored pending) and applied only on user Confirm."""
import hashlib
import json
import os
import re
from datetime import date

from . import analytics as an
from . import db, gemini, guardrails, nudges, planner, review, timeline
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
            g = _find_goal(uid, p.get("goal_name"))
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


def _find_goal(uid, name):
    goals = planner.list_goals(uid)
    low = str(name or "").lower()
    return next((g for g in goals if g["name"].lower() == low), None) or \
        next((g for g in goals if low and (low in g["name"].lower() or g["name"].lower() in low)), None)


TOOLS = {"get_profile": tool_get_profile, "run_what_if": tool_run_what_if,
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


# ------------------------------------------------------------------ Gemini loop
def _declarations():
    from google.genai import types
    S = lambda t, d="": {"type": t, "description": d}
    adj = {"type": "ARRAY", "description": "Adjustments. percent>0 raises, <0 cuts; or amount = monthly rupee change.",
           "items": {"type": "OBJECT", "properties": {
               "category": S("STRING", "Spending category (e.g. Dining, Rent, Groceries) or 'Income'"),
               "percent": S("NUMBER", "Percent change, e.g. -30 for a 30% cut"),
               "amount": S("NUMBER", "Monthly rupee change instead of percent")}, "required": ["category"]}}
    fd = lambda n, d, props=None, req=None: types.FunctionDeclaration(
        name=n, description=d,
        parameters={"type": "OBJECT", "properties": props or {"_": S("STRING", "unused")}, **({"required": req} if req else {})})
    return [types.Tool(function_declarations=[
        fd("get_profile", "Read the user's financial profile, income, average spend by category, goals and emergency fund."),
        fd("run_what_if", "Simulate a scenario (cut a category, rent increase, income change) and get impact on free "
                          "cash and goal dates. Use for ANY what-if question.", {"adjustments": adj}, ["adjustments"]),
        fd("list_subscriptions", "List detected recurring payments/subscriptions with price-change and unused alerts."),
        fd("list_nudges", "List current spending-drift nudges and alerts."),
        fd("explain_nudge", "Explain why a nudge fired, with numbers.", {"nudge_id": S("STRING", "id like budget:Dining")}, ["nudge_id"]),
        fd("get_spending_summary", "Month facts: income, spend, top categories, budgets, goals.", {"month": S("STRING", "YYYY-MM, optional")}),
        fd("propose_change", "PROPOSE (not apply) a change; the user must confirm in the UI. kinds: set_budget(category, amount), "
                             "update_goal(goal_name + monthly_contrib/target_amount/target_date), "
                             "create_goal(name,target_amount,target_date,saved,monthly_contrib), update_profile(field,value).",
           {"kind": S("STRING", "set_budget|update_goal|create_goal|update_profile"), "reason": S("STRING", "why"),
            "category": S("STRING"), "amount": S("NUMBER"), "goal_name": S("STRING"), "monthly_contrib": S("NUMBER"),
            "target_amount": S("NUMBER"), "target_date": S("STRING", "YYYY-MM-DD"), "name": S("STRING"),
            "saved": S("NUMBER"), "field": S("STRING"), "value": S("NUMBER")}, ["kind", "reason"]),
    ])]


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


def _history(uid, limit=8):
    rows = db.rows("SELECT role,text FROM chat WHERE uid=? ORDER BY id DESC LIMIT ?", (uid, limit))
    return list(reversed(rows))


def _ai_chat(uid, message, trace):
    from google.genai import types
    contents = [types.Content(role="user" if h["role"] == "user" else "model", parts=[types.Part(text=h["text"])])
                for h in _history(uid)]
    contents.append(types.Content(role="user", parts=[types.Part(text=message)]))
    system = (guardrails.SYSTEM_RULES + " Today's data runs through " + an.as_of(uid).isoformat() +
              ". Keep answers short (under 150 words), friendly, with Indian rupee formatting. Use tools for facts; "
              "when the user wants a change, call propose_change and tell them to press Confirm on the card.")
    decl = _declarations()
    for _ in range(6):
        resp = gemini.generate(None, system=system, tools=decl, contents=contents, raw=True)
        if resp is None or not resp.candidates:
            return None
        parts = resp.candidates[0].content.parts or []
        calls = [p.function_call for p in parts if getattr(p, "function_call", None)]
        if not calls:
            return (resp.text or "").strip() or None
        contents.append(resp.candidates[0].content)
        out_parts = []
        for c in calls:
            args = dict(c.args or {})
            fn = TOOLS.get(c.name)
            try:
                result = fn(uid, **args) if fn else {"error": "unknown tool"}
            except Exception as e:  # tool errors go back to the model, not the user
                result = {"error": str(e)}
            trace.append({"tool": c.name, "args": json.loads(json.dumps(args, default=str)), "result": brief(c.name, result)})
            out_parts.append(types.Part.from_function_response(name=c.name, response={"result": json.loads(json.dumps(result, default=str))}))
        contents.append(types.Content(role="user", parts=out_parts))
    return None


# ------------------------------------------------------------------ non-AI fallback
_NUM = r"(\d[\d,]*(?:\.\d+)?)"


def _fallback_chat(uid, message, trace):
    low = message.lower()
    amt_m = re.search(r"(?:rs\.?|inr|₹)\s*" + _NUM + r"|" + _NUM + r"\s*(?:rs|rupees|inr|₹)", low)
    pct_m = re.search(_NUM + r"\s*(?:%|percent|per cent)", low)
    bare_m = re.search(r"(?<![\d.])(\d[\d,]{2,}(?:\.\d+)?)(?!\s*%)", low)
    cat = find_category(low)
    increase = re.search(r"goes up|go up|increase|rise|hike|raise|more|higher", low)
    decrease = re.search(r"cut|reduce|lower|decrease|less|drop|trim|save on", low)
    if re.search(r"what if|how would|simulate|if i|if my", low) or (cat or "income" in low) and (pct_m or amt_m or bare_m) and (increase or decrease):
        adjs = []
        sign = 1 if increase and not decrease else -1
        if "income" in low or "salary" in low:
            if re.search(r"drop|cut|lose|fall|less|decrease|reduce", low):
                sign = -1
            elif re.search(r"raise|hike|increase|more|up", low):
                sign = 1
            cat = "Income"
        if cat and (pct_m or amt_m or bare_m):
            if pct_m:
                adjs.append({"category": cat, "percent": sign * float(pct_m.group(1).replace(",", ""))})
            else:
                v = float(((amt_m.group(1) or amt_m.group(2)) if amt_m else bare_m.group(1)).replace(",", ""))
                adjs.append({"category": cat, "amount": sign * v})
            res = tool_run_what_if(uid, adjs)
            trace.append({"tool": "run_what_if", "args": {"adjustments": adjs}, "result": brief("run_what_if", res)})
            text = f"Here's the scenario: {res['summary']}"
            if cat != "Income" and sign < 0:
                new = res["applied"][0]["to"]
                tool_propose_change(uid, "set_budget", f"Matches the what-if: {cat} at {an.inr(new)}/month",
                                    category=cat, amount=new)
                trace.append({"tool": "propose_change", "args": {"kind": "set_budget", "category": cat, "amount": new},
                               "result": "proposal created - waiting for your Confirm"})
                text += f"\n\nI've proposed a {cat} budget of {an.inr(new)}/month - confirm below to apply it."
            return text
    if re.search(r"subscription|recurring|netflix|spotify|gym", low):
        subs = tool_list_subscriptions(uid)
        trace.append({"tool": "list_subscriptions", "args": {}, "result": brief("list_subscriptions", subs)})
        subs = [s for s in subs if s["kind"] == "subscription"] or subs
        lines = [f"- {s['merchant'].title()}: {an.inr(s['amount'])}/{s['cadence']}" + (f" - {s['alerts'][0]}" if s["alerts"] else "") for s in subs[:8]]
        return "Here are your recurring payments:\n" + "\n".join(lines)
    if re.search(r"nudge|why|off track|drift|alert|over budget", low):
        ns = tool_list_nudges(uid)
        trace.append({"tool": "list_nudges", "args": {}, "result": brief("list_nudges", ns)})
        if not ns:
            return "No nudges right now - you're tracking within plan."
        target = next((n for n in ns if cat and n["id"].endswith(cat)), ns[0])
        ex = tool_explain_nudge(uid, target["id"])
        trace.append({"tool": "explain_nudge", "args": {"nudge_id": target["id"]}, "result": brief("explain_nudge", ex)})
        return f"**{target['title']}** - {ex.get('why', target['body'])}" + (
            f"\n\nIf you trimmed 15% of your usual: {ex['if_you_trim_15pct_of_usual']}" if ex.get("if_you_trim_15pct_of_usual") else "")
    if re.search(r"goal|target|on track|afford", low):
        p = tool_get_profile(uid)
        trace.append({"tool": "get_profile", "args": {}, "result": brief("get_profile", p)})
        lines = [f"- {g['name']}: {an.inr(g['saved'])}/{an.inr(g['target'])}, "
                 f"{'on track' if g['on_track'] else 'behind (needs ' + an.inr(g['required_monthly'] or 0) + '/mo)'}" for g in p["goals"]]
        return "Your goals:\n" + "\n".join(lines)
    m = re.search(r"(?:set|change|make|update).{0,25}budget.{0,25}?" + _NUM, low)
    if cat and m:
        r = tool_propose_change(uid, "set_budget", "Requested in chat", category=cat, amount=float(m.group(1).replace(",", "")))
        trace.append({"tool": "propose_change", "args": {"kind": "set_budget", "category": cat},
                      "result": "proposal created - waiting for your Confirm"})
        return "Done - I've proposed that budget. Press Confirm below to apply it." if "proposal_id" in r else "I couldn't parse that budget."
    return ("I can run what-if scenarios (e.g. *what if I cut dining out by 30%?* or *what if my rent goes up by "
            "₹3,000?*), explain nudges, list subscriptions, and propose budget or goal changes you can confirm. "
            "(AI chat is offline right now, so I'm using built-in rules.)")


def data_fingerprint(uid):
    """Hash of everything a coach answer depends on, independent of user id - so the demo user's answers can be replayed."""
    tx = [(t["date"], t["amount"], t["category"]) for t in an.get_txns(uid)]
    goals = [(g["name"], g["target_amount"], g["saved"], g["target_date"], g["monthly_contrib"]) for g in planner.list_goals(uid)]
    blob = json.dumps([tx, goals, planner.get_profile(uid), db.kv_get(uid, "mandates", {})], sort_keys=True, default=str)
    return hashlib.sha1(blob.encode()).hexdigest()


def _coach_key(uid, message):
    return "coach|" + hashlib.sha1((data_fingerprint(uid) + "|" + re.sub(r"\s+", " ", message.lower().strip())).encode()).hexdigest()


def _replay(uid, entry):
    have = {(p["kind"], json.dumps(p["payload"], sort_keys=True)) for p in pending(uid)}
    for pr in entry.get("proposals", []):
        payload = dict(pr["payload"])
        if pr["kind"] == "update_goal":
            g = _find_goal(uid, payload.get("goal_name"))
            if not g:
                continue
            payload["goal_id"] = g["id"]
        if (pr["kind"], json.dumps(payload, sort_keys=True)) in have:
            continue
        db.run("INSERT INTO proposals(uid,kind,payload,reason) VALUES(?,?,?,?)",
               (uid, pr["kind"], json.dumps(payload), pr.get("reason")))


def chat(uid, message):
    db.run("INSERT INTO chat(uid,role,text) VALUES(?,?,?)", (uid, "user", message))
    blocked = guardrails.check_input(message)
    trace, ai, cached = [], False, False
    if blocked:
        reply = blocked
    else:
        key = _coach_key(uid, message)
        hit = db.one("SELECT v FROM cache WHERE h=?", (key,))
        reply = None
        if hit:  # pre-computed Gemini answer (demo data) - instant, replayed with its tool steps and proposals
            entry = json.loads(hit["v"])
            reply, trace, ai, cached = entry["reply"], entry["tools"], True, True
            _replay(uid, entry)
        else:
            before = {p["id"] for p in pending(uid)}
            reply = _ai_chat(uid, message, trace) if gemini.enabled() else None
            ai = reply is not None
            if reply is None:
                trace.clear()
                reply = _fallback_chat(uid, message, trace)
            reply = guardrails.sanitize_output(reply)
            if ai and os.environ.get("COACH_CACHE_WRITE") and reply != guardrails.EDUCATIONAL_REPLY:
                new = [p for p in pending(uid) if p["id"] not in before]
                db.run("INSERT OR REPLACE INTO cache(h,v) VALUES(?,?)", (key, json.dumps(
                    {"reply": reply, "tools": trace, "proposals": [{"kind": p["kind"], "payload": p["payload"], "reason": p["reason"]} for p in new]})))
    db.run("INSERT INTO chat(uid,role,text) VALUES(?,?,?)", (uid, "model", reply))
    return {"reply": reply, "ai": ai, "guardrail": bool(blocked) or reply == guardrails.EDUCATIONAL_REPLY,
            "tools": trace, "cached": cached, "proposals": pending(uid), "disclaimer": guardrails.DISCLAIMER}
