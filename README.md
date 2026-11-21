# Money Coach - a personal finance coach with a living money model

Built for the Product Space Agentic AI Hackathon (Problem 04).

Most budgeting apps categorise transactions and stop. Money Coach keeps a **living model** of one person's money: income, fixed costs, emergency fund, goals with dates. It re-computes that model as new statements arrive, learns from corrections, models "what if" scenarios, and nudges the user when spending drifts off plan.

Indian context throughout: INR with lakh/crore grouping (₹1,25,000), UPI / NEFT / card narrations, Indian bank SMS formats.

## Features (mapped to the brief)

| # | Requirement | How it works |
|---|---|---|
| 1 | Messy ingestion + categorisation | CSV (bank preambles, split debit/credit or Dr/Cr columns), PDF statements (table layout, direction inferred from the running balance), pasted SMS (HDFC/SBI/ICICI/Axis-style, OTP/promo noise ignored). Categories come from user rules, then built-in keywords, then history of the same merchant, then **Gemini** for unknown merchants. Anything the regex parsers cannot read is rescued by Gemini. |
| 2 | Correction loop | Change a category on any transaction and the app stores a rule on the normalised merchant, re-labels existing transactions of that merchant, and applies it to future uploads (even from a different source, e.g. an SMS after a CSV). Rules are listed and can be forgotten. |
| 3 | Recurring + subscriptions | Deterministic detection (same merchant, regular weekly/monthly/quarterly/yearly gaps). Alerts for **price change**, **seems unused** (based on "last used"), **overlapping streaming services**, and upcoming charges. |
| 4 | Persistent profile | Income, fixed costs, emergency fund (+ monthly top-up and target months), category budgets, goals with target dates. Stored in SQLite. |
| 5 | Goal planner + what-if | Pure-arithmetic simulator: cut a category by %, change rent/income/any category by a rupee amount, add a new EMI. Shows free cash before/after, yearly impact and how each goal's projected date moves. Surplus beyond plan is steered to goals that are behind. |
| 6 | Nudges | Budget pace tracking for the current month (already over / on pace to exceed by >10%), goals behind schedule, low emergency fund, subscription alerts. Each has an "Explain this" button (Gemini, with a built-in explanation as fallback). |
| 7 | Monthly review | Verified numbers computed in code, narrated by Gemini (template fallback), printable. |
| 8 | Guardrails | See below. |

### The agentic coach
A chat where Gemini calls **tools**: `get_profile`, `run_what_if`, `list_subscriptions`, `list_nudges`, `explain_nudge`, `get_spending_summary`, `propose_change`. The UI shows which tools were used. The coach can only **propose** changes (set a budget, update/create a goal, update a profile field); a pending card appears and **nothing changes until the user clicks Confirm**.

## How AI is used (and where it is not)

- **Deterministic code** does all money maths: totals, baselines, recurring detection, simulations, drift, goal projections. Tests cover these.
- **Gemini** (`gemini-3.5-flash`, fallback `gemini-3.5-flash-lite`) does: parsing text the regex cannot read, categorising unknown merchants, the monthly review narrative, nudge explanations, and the tool-calling coach chat.
- Results are **cached by content hash** (file hash for parsing, merchant-set hash for categorisation, facts hash for narratives).
- **No-AI fallback:** 20-second timeout, then a 45-second circuit breaker. If Gemini is down or out of quota the app keeps working: keyword/history categorisation, template review, template nudge explanations, and a rule-based coach that still runs what-ifs, lists subscriptions and proposes budgets. The header badge shows which mode you are in.

## Guardrails

The coach educates and models scenarios; it never recommends specific securities, funds or stocks. Enforced in **code**, not only in the prompt:

1. **Input check** (`backend/app/guardrails.py`): requests to pick, rank or buy a stock/fund/ETF/crypto/scheme get a fixed educational answer (priorities, risk vs return, diversification, what a SIP is) and referral to a SEBI-registered adviser. The model is not even called.
2. **Output check:** every model answer is scanned for product names and "buy X Fund" patterns; a hit replaces the whole answer with the educational one.
3. **System prompt** forbids product recommendations and requires numbers to come from tools.
4. **Visible disclaimer** pinned to the bottom of every screen.

## Run it

```bash
# 1. backend deps
pip install -r requirements.txt
# 2. frontend build (served by FastAPI)
cd frontend && npm install && npm run build && cd ..
# 3. key (never committed; .env is git-ignored)
echo GEMINI_API_KEY=your_key > .env
# 4. start
cd backend && uvicorn app.main:app --port 8000      # http://localhost:8000
```

Dev mode with hot reload: `uvicorn app.main:app --port 8000` in `backend/` and `npm run dev` in `frontend/`.

Tests: `python -m pytest -q` (parsing, rule learning, recurring detection, simulation maths, drift nudges, guardrails, API flows; AI is disabled in tests).

Docker: `docker build -t money-coach . && docker run -p 8000:8000 -e GEMINI_API_KEY=... money-coach`

### Deploy on Render
Push the repo, create a **Blueprint** from `render.yaml`, and set the `GEMINI_API_KEY` environment variable in the dashboard. One Docker web service serves API and UI. SQLite lives in `/tmp` on the free tier, so data resets on redeploy or restart; the demo reloads in one click.

## Demo in 60 seconds
1. Open the app and click **Load demo data**. It ingests a CSV (Aug-Sep), a PDF statement (Oct) and SMS (Nov) through the real pipeline.
2. **Dashboard:** nudges (Dining over budget, Japan goal behind, Netflix price rise, unused gym).
3. **Transactions:** change a category; see the learned rule.
4. **What-if:** "Cut dining out 30%" and "Rent goes up ₹3,000".
5. **Coach:** ask "What if I cut dining out by 30%?", confirm the proposed budget, then ask "Which mutual fund should I buy?" to see the guardrail.

Sample files are in `samples/` (regenerate with `python scripts/generate_samples.py`); `samples/sms_quick_paste.txt` is a short set of SMS to paste. See `DEMO_SCRIPT.md` for the 3-minute video script.

## Project layout
```
backend/app/   parsing.py ingest.py categorize.py analytics.py planner.py nudges.py review.py
               coach.py guardrails.py gemini.py seed.py main.py db.py
backend/tests/ pytest suite
frontend/src/  React + TypeScript (Vite) UI
samples/       demo CSV, PDF, SMS
```

## Limitations
Single currency (INR), per-browser anonymous profile (no login), subscription "unused" status relies on a last-used date the user confirms (banks do not expose usage), and heuristics are tuned on common Indian bank formats.
