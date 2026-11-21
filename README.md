# Money Coach - a personal finance coach with a living money model

Built for the Product Space Agentic AI Hackathon (Problem 04). Made for India: INR with lakh/crore grouping (₹1,25,000 · ₹1.8L), UPI / NEFT / card narrations, UPI AutoPay mandates and real bank-SMS formats.

Most budgeting apps categorise transactions and stop. Money Coach keeps a **living model** of one person's money (income, fixed costs, emergency fund, goals with dates), updates it as new statements arrive, learns from corrections, and answers "what happens if life changes?" without ever recommending a stock or fund.

**Try it in one click:** open the app and press **Try with demo data**. No signup.

## Standout features

1. **Life event simulator** - stack a salary hike, a 3-month job loss, a rent increase and a new EMI. A month-by-month engine shows the emergency-fund curve (before vs after, with the lowest point and whether it runs out) and moves every goal date on a before/after timeline. The maths is deterministic; Gemini only explains the result.
2. **Living money model timeline** - a dated history of how your profile changed and *why*: new income source, salary change, goals added, budgets set, emergency fund updated, subscription price rises, subscriptions that quietly stopped, rules the coach learned, coach proposals you confirmed. Part is logged, part is *detected from the statements themselves*.
3. **Visible AI** - every coach answer shows the tool steps it took (`run_what_if(Dining -30%)` -> result), every proposed change appears as a card with **Confirm / Dismiss**, correcting a category pops a **"Learned rule"** toast, and every transaction shows whether it was parsed from **SMS / PDF / CSV** and what categorised it (built-in, your rule, learned, Gemini).
4. **Indian touches** - paste raw bank/UPI SMS (HDFC/SBI/ICICI/Axis styles; OTPs and promos ignored), **UPI AutoPay mandates** detected as subscriptions (including *upcoming* mandate notices that flag a price rise before it debits), lakh/crore formatting everywhere.
5. **Guardrail demo** - ask "Which mutual fund should I buy?" and the coach explains priorities, risk and diversification, names no product, and shows a visible **Guardrail active** badge. A disclaimer is pinned on every screen.

## All requirements (Problem 04)

| # | Requirement | How it works |
|---|---|---|
| 1 | Messy ingestion + categorisation | CSV (bank preambles, split debit/credit or Dr/Cr), PDF (table layout, direction inferred from the running balance), pasted SMS. Categories: your rules -> built-in keywords -> history of the same merchant -> **Gemini** for unknown merchants. Text the regex parsers cannot read is rescued by Gemini. |
| 2 | Correction loop | Fix a category once: a rule is stored on the normalised merchant, existing transactions are re-labelled, future uploads (even from another source) follow it. Rules are listed and can be forgotten. |
| 3 | Recurring + subscriptions | Deterministic detection (regular weekly/monthly/quarterly/yearly gaps). Alerts for price change, seems unused, overlapping streaming services, cancelled subscriptions, upcoming AutoPay debits. |
| 4 | Persistent profile | Income, fixed costs, emergency fund (+ target months and monthly top-up), budgets, goals with dates - in SQLite. |
| 5 | Goal planner + what-if | One-shot what-if (cut a category by %, change rent/income, add an EMI) plus the month-by-month life event simulator. Surplus beyond plan is steered to goals that are behind. |
| 6 | Nudges | Budget pace tracking for the month, goals behind schedule, low emergency fund, subscription and AutoPay alerts; "Explain this" per nudge. |
| 7 | Monthly review | Numbers computed in code, narrated by Gemini (template fallback), printable. |
| 8 | Guardrails | Enforced in code on input *and* output, plus the system prompt and a visible disclaimer. |

### The agentic coach
Gemini calls **tools**: `get_profile`, `run_what_if`, `list_subscriptions`, `list_nudges`, `explain_nudge`, `get_spending_summary`, `propose_change`. It can only *propose* (set a budget, update/create a goal, update a profile field). **Nothing changes until the user clicks Confirm**, and the confirmed change is recorded on the timeline.

## How AI is used (and where it is not)

- **Deterministic code** does all money maths: totals, baselines, recurring detection, simulations, drift, goal projections, the life-event engine. Covered by tests.
- **Gemini** (`gemini-3.5-flash`, fallback `gemini-3.5-flash-lite`) does: parsing text the regex cannot read, categorising unknown merchants, the monthly narrative, nudge and life-event explanations, and the tool-calling coach.
- **Pre-computed demo cache:** `backend/app/gemini_cache.json` holds real Gemini results for the bundled demo data (categorisation, four monthly reviews, nudge explanations, life-event narrations, coach answers incl. tool steps). The demo is instant and never shows "AI busy". Cached coach answers are labelled "pre-computed for the demo data". **Live Gemini still runs for anything new** (your own uploads, new questions). Regenerate with `python scripts/build_demo_cache.py`.
- **Results cache** by content hash for live calls too, then a **20 s timeout + 45 s circuit breaker**; if Gemini is down or out of quota the app falls back to keyword/history categorisation, template reviews and a rule-based coach that still runs what-ifs, lists subscriptions and proposes budgets. The header badge shows the mode.

## Guardrails

The coach educates and models scenarios; it never recommends specific securities, funds or stocks.

1. **Input check** (`backend/app/guardrails.py`): requests to pick, rank or buy a stock/fund/ETF/crypto/scheme get a fixed educational answer and a referral to a SEBI-registered adviser. The model is not called.
2. **Output check:** every model answer (coach, review, explanations, life-event text) is scanned for product names and "buy X Fund" patterns; a hit replaces the answer with the educational one.
3. **System prompt** forbids product recommendations and requires numbers to come from tools.
4. **Visible guardrail badge** on blocked answers and a **disclaimer** on every screen.

## Run it

```bash
pip install -r requirements.txt
cd frontend && npm install && npm run build && cd ..
echo GEMINI_API_KEY=your_key > .env          # git-ignored, never committed
cd backend && uvicorn app.main:app --port 8000   # http://localhost:8000
```

Dev: `uvicorn app.main:app --port 8000` in `backend/` and `npm run dev` in `frontend/`. Tests: `python -m pytest -q` (parsing, rule learning, recurring/AutoPay, simulation, life events, timeline, nudges, guardrails, cache replay, API flows; AI is disabled in tests). Docker: `docker build -t money-coach . && docker run -p 8000:8000 -e GEMINI_API_KEY=... money-coach`.

### Deploy on Render
Push the repo, create a **Blueprint** from `render.yaml`, set `GEMINI_API_KEY` in the dashboard. One Docker web service serves API and UI. SQLite lives in `/tmp` on the free tier, so data resets on restart; the demo reloads in one click.

## Demo in 60 seconds
1. **Try with demo data** (a CSV, a PDF statement and bank SMS are ingested through the real pipeline).
2. **Life events** -> "Job loss + new EMI": watch the emergency fund dip and goals slip.
3. **Coach** -> "Set my dining budget to 4000 and explain why" -> tool steps -> **Confirm**.
4. **Timeline** shows that change with its reason; **Subscriptions** shows the Netflix price rise, the unused gym and the Hotstar AutoPay hike.
5. Ask "Which mutual fund should I buy?" to see the guardrail badge.

`DEMO_SCRIPT.md` is the 2:30 video script. Sample files are in `samples/` (`python scripts/generate_samples.py` regenerates them; `samples/sms_quick_paste.txt` is a short paste set, and the Transactions screen has a "Fill sample UPI SMS" button). Open the app with `?u=anything&tab=coach` to jump to a tab with a fresh anonymous profile.

## Project layout
```
backend/app/   parsing ingest categorize analytics planner lifeevents timeline nudges review
               coach guardrails gemini seed main db   (+ gemini_cache.json)
backend/tests/ pytest suite        frontend/src/  React + TypeScript (Vite)
samples/       demo CSV, PDF, SMS  scripts/       sample + cache generators
```

## Limitations
INR only, per-browser anonymous profile (no login), "unused subscription" relies on a last-used date the user confirms (banks do not expose usage), heuristics are tuned on common Indian bank formats, life-event projections assume today's averages continue.
