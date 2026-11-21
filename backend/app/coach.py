"""Agentic coach: Gemini function-calling loop over coach_tools, with a rule-based fallback and demo replay."""
import hashlib
import json
import os
import re

from . import analytics as an
from . import coach_tools as ct
from . import db, gemini, guardrails, planner
from .config import CHAT_HISTORY_MESSAGES, MAX_TOOL_ROUNDS


# ------------------------------------------------------------------ Gemini loop
def _declarations():
    from google.genai import types
    def S(t, d=""):
        return {"type": t, "description": d}
    adj = {"type": "ARRAY", "description": "Adjustments. percent>0 raises, <0 cuts; or amount = monthly rupee change.",
           "items": {"type": "OBJECT", "properties": {
               "category": S("STRING", "Spending category (e.g. Dining, Rent, Groceries) or 'Income'"),
               "percent": S("NUMBER", "Percent change, e.g. -30 for a 30% cut"),
               "amount": S("NUMBER", "Monthly rupee change instead of percent")}, "required": ["category"]}}
    def fd(n, d, props=None, req=None):
        return types.FunctionDeclaration(name=n, description=d, parameters={"type": "OBJECT", "properties": props or {"_": S("STRING", "unused")}, **({"required": req} if req else {})})  # type: ignore[arg-type]
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


def _history(uid, limit=CHAT_HISTORY_MESSAGES):
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
    for _ in range(MAX_TOOL_ROUNDS):
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
            fn = ct.TOOLS.get(c.name)
            try:
                result = fn(uid, **args) if fn else {"error": "unknown tool"}
            except Exception as e:  # tool errors go back to the model, not the user
                result = {"error": str(e)}
            trace.append({"tool": c.name, "args": json.loads(json.dumps(args, default=str)), "result": ct.brief(c.name, result)})
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
    cat = ct.find_category(low)
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
                v = float(((amt_m.group(1) or amt_m.group(2)) if amt_m else (bare_m.group(1) if bare_m else "0")).replace(",", ""))
                adjs.append({"category": cat, "amount": sign * v})
            res = ct.tool_run_what_if(uid, adjs)
            trace.append({"tool": "run_what_if", "args": {"adjustments": adjs}, "result": ct.brief("run_what_if", res)})
            text = f"Here's the scenario: {res['summary']}"
            if cat != "Income" and sign < 0:
                new = res["applied"][0]["to"]
                ct.tool_propose_change(uid, "set_budget", f"Matches the what-if: {cat} at {an.inr(new)}/month",
                                    category=cat, amount=new)
                trace.append({"tool": "propose_change", "args": {"kind": "set_budget", "category": cat, "amount": new},
                               "result": "proposal created - waiting for your Confirm"})
                text += f"\n\nI've proposed a {cat} budget of {an.inr(new)}/month - confirm below to apply it."
            return text
    if re.search(r"subscription|recurring|netflix|spotify|gym", low):
        subs = ct.tool_list_subscriptions(uid)
        trace.append({"tool": "list_subscriptions", "args": {}, "result": ct.brief("list_subscriptions", subs)})
        subs = [s for s in subs if s["kind"] == "subscription"] or subs
        lines = [f"- {s['merchant'].title()}: {an.inr(s['amount'])}/{s['cadence']}" + (f" - {s['alerts'][0]}" if s["alerts"] else "") for s in subs[:8]]
        return "Here are your recurring payments:\n" + "\n".join(lines)
    if re.search(r"nudge|why|off track|drift|alert|over budget", low):
        ns = ct.tool_list_nudges(uid)
        trace.append({"tool": "list_nudges", "args": {}, "result": ct.brief("list_nudges", ns)})
        if not ns:
            return "No nudges right now - you're tracking within plan."
        target = next((n for n in ns if cat and n["id"].endswith(cat)), ns[0])
        ex = ct.tool_explain_nudge(uid, target["id"])
        trace.append({"tool": "explain_nudge", "args": {"nudge_id": target["id"]}, "result": ct.brief("explain_nudge", ex)})
        return f"**{target['title']}** - {ex.get('why', target['body'])}" + (
            f"\n\nIf you trimmed 15% of your usual: {ex['if_you_trim_15pct_of_usual']}" if ex.get("if_you_trim_15pct_of_usual") else "")
    if re.search(r"goal|target|on track|afford", low):
        p = ct.tool_get_profile(uid)
        trace.append({"tool": "get_profile", "args": {}, "result": ct.brief("get_profile", p)})
        lines = [f"- {g['name']}: {an.inr(g['saved'])}/{an.inr(g['target'])}, "
                 f"{'on track' if g['on_track'] else 'behind (needs ' + an.inr(g['required_monthly'] or 0) + '/mo)'}" for g in p["goals"]]
        return "Your goals:\n" + "\n".join(lines)
    m = re.search(r"(?:set|change|make|update).{0,25}budget.{0,25}?" + _NUM, low)
    if cat and m:
        r = ct.tool_propose_change(uid, "set_budget", "Requested in chat", category=cat, amount=float(m.group(1).replace(",", "")))
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
    have = {(p["kind"], json.dumps(p["payload"], sort_keys=True)) for p in ct.pending(uid)}
    for pr in entry.get("proposals", []):
        payload = dict(pr["payload"])
        if pr["kind"] == "update_goal":
            g = ct.find_goal(uid, payload.get("goal_name"))
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
            before = {p["id"] for p in ct.pending(uid)}
            reply = _ai_chat(uid, message, trace) if gemini.enabled() else None
            ai = reply is not None
            if reply is None:
                trace.clear()
                reply = _fallback_chat(uid, message, trace)
            reply = guardrails.sanitize_output(reply)
            if ai and os.environ.get("COACH_CACHE_WRITE") and reply != guardrails.EDUCATIONAL_REPLY:
                new = [p for p in ct.pending(uid) if p["id"] not in before]
                db.run("INSERT OR REPLACE INTO cache(h,v) VALUES(?,?)", (key, json.dumps(
                    {"reply": reply, "tools": trace, "proposals": [{"kind": p["kind"], "payload": p["payload"], "reason": p["reason"]} for p in new]})))
    db.run("INSERT INTO chat(uid,role,text) VALUES(?,?,?)", (uid, "model", reply))
    return {"reply": reply, "ai": ai, "guardrail": bool(blocked) or reply == guardrails.EDUCATIONAL_REPLY,
            "tools": trace, "cached": cached, "proposals": ct.pending(uid), "disclaimer": guardrails.DISCLAIMER}
