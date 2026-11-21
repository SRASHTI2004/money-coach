# Money Coach - a personal finance coach with a living money model

**Live demo: https://money-coach-k49s.onrender.com** (free hosting: the first load can take ~30 s to wake up)

**Product thinking: [PRODUCT.md](PRODUCT.md)** (target user, insights, jobs to be done, decisions and trade-offs, metrics, roadmap) · **Uptime ping:** `GET /api/health` (lightweight JSON, no database or AI call)

Built for the Product Space Agentic AI Hackathon, Problem 04. Made for India: INR with lakh/crore grouping (₹1,25,000 · ₹1.8L), UPI / NEFT / card narrations, UPI AutoPay mandates and real bank-SMS formats.

**The problem.** Budgeting apps categorise transactions and stop: they do not understand a person's goals, and they do not adapt when life changes.
**Our answer.** Money Coach keeps a *living model* of your money (income, fixed costs, emergency fund, goals with dates), learns from your corrections, and answers "what happens if...?" with deterministic maths and an agentic AI coach, without ever recommending a stock or fund.

## Try it in one minute

1. Open the live link and click **Try with demo data** (a CSV, a PDF statement and bank SMS are ingested; no signup).
2. Go to **Transactions** -> click **Fill sample UPI SMS** -> **Import pasted SMS** (raw UPI/bank SMS parsed, including a UPI AutoPay debit). Note the SMS / PDF / CSV badges on each row.
3. In the same table, change any row's category (e.g. a Dining item to **Shopping**). A green **Learned rule** toast appears and similar rows are re-labelled.
4. Open **Life events** -> click **Job loss + new EMI**. Watch the emergency fund dip and every goal date slip (before/after lanes); Gemini explains the result.
5. Open **Coach** -> click **Set my dining budget to 4000 and explain why** -> see the numbered tool steps -> click **Confirm**.
6. Still in **Coach**, click **Which mutual fund should I buy?** -> an educational answer with a **Guardrail active** badge, naming no product.
7. Optional: **Timeline** (why your model changed), **Subscriptions** (Netflix price rise, unused gym, Hotstar AutoPay hike), **How it works** (header button).

## Requirements (all 8 brief items)

| # | Brief requirement | Where it lives | How it works |
|---|---|---|---|
| 1 | Ingest messy statements (PDF, CSV, SMS) + auto-categorise | **Transactions** | CSV with bank preambles and split debit/credit or Dr/Cr; PDF tables (direction inferred from the running balance); pasted SMS (HDFC/SBI/ICICI/Axis styles, OTPs/promos ignored). Categories: your rules, then built-in keywords, then merchant history, then **Gemini** for unknown merchants. Anything the parsers cannot read is rescued by Gemini. |
| 2 | Correction loop: fix a category, learn a rule | **Transactions** | One correction stores a rule on the normalised merchant, re-labels past rows and applies to future uploads from any source. Rules are listed and can be forgotten. |
| 3 | Recurring payments + subscriptions, with price-change / unused alerts | **Subscriptions** | Deterministic detection of regular weekly/monthly/quarterly/yearly charges, plus **UPI AutoPay** mandates (including upcoming-mandate notices). Alerts: price change, seems unused, overlapping streaming, cancelled, mandate about to cost more. |
| 4 | Persistent profile: income, fixed costs, emergency fund, goals with dates | **Plan & goals**, **Timeline** | Stored in SQLite. The Timeline records every change with a reason, plus changes detected from the statements. |
| 5 | Goal planner + what-if ("cut dining 30%", "rent goes up") | **What-if**, **Life events** | One-shot what-if, and a month-by-month life-event engine (salary change, job loss, rent increase, new EMI) with before/after emergency-fund curve and goal dates. |
| 6 | Nudges when spending drifts off plan | **Dashboard** | Budget pace tracking for the month, goals behind schedule, low emergency fund, subscription and AutoPay alerts, each with "Explain this". |
| 7 | Monthly review report | **Monthly review** | Numbers computed in code, narrated by Gemini (template fallback), printable. |
| 8 | Guardrails: educate and model, never recommend securities | **Coach**, everywhere | Enforced in code on input and output, plus system prompt, a visible guardrail badge and a disclaimer on every screen. |

Agentic coach: Gemini calls tools (`get_profile`, `run_what_if`, `list_subscriptions`, `list_nudges`, `explain_nudge`, `get_spending_summary`, `propose_change`). It can only **propose** a change; nothing applies until the user clicks **Confirm**, and the change is then recorded on the Timeline.

## Standout features

- **Life event simulator** - stack a hike, a job loss, a rent rise and a new EMI; see the fund and each goal month by month.
- **Living money model timeline** - what changed and why, logged or detected from your data.
- **Visible AI** - tool steps on every coach answer, Confirm cards, "Learned rule" toast, per-row SMS/PDF/CSV and categoriser badges.
- **Indian touches** - raw SMS paste, UPI AutoPay detection, lakh/crore formatting.
- **Guardrail you can see** - asked for a fund, it explains risk and diversification and names nothing.

## How AI is used (and where it is not)

- **Plain code** does all money maths (totals, averages, free cash, goal dates, drift, the simulators), subscription detection and rule learning. Covered by tests.
- **Gemini** (`gemini-3.5-flash`, fallback `gemini-3.5-flash-lite`) parses text the regex cannot, labels unknown merchants, writes the monthly review, explains nudges and simulations, and runs the tool-calling coach.
- **Pre-computed demo cache:** `backend/app/gemini_cache.json` holds real Gemini results for the bundled demo data, so the demo is instant and never shows "AI busy". Cached coach answers are labelled as pre-computed. **Live Gemini still runs for anything new.** Regenerate with `python scripts/build_demo_cache.py`.
- **Resilience:** results cached by content hash, 20 s timeout and a 45 s circuit breaker; if Gemini is down the app falls back to keyword categorisation, template reviews and a rule-based coach, and the header badge shows the mode.

## Guardrails

1. **Input check** (`backend/app/guardrails.py`): requests to pick, rank or buy a stock/fund/ETF/crypto/scheme get a fixed educational answer and a referral to a SEBI-registered adviser; the model is not called.
2. **Output check:** every model answer (coach, review, explanations, life-event text) is scanned for product names and "buy X Fund" patterns; a hit replaces it with the educational answer.
3. **System prompt** forbids product recommendations and requires numbers to come from tools.
4. **Visible:** guardrail badge on blocked answers and a disclaimer on every screen.

## Quality and security

- **Checks:** `scripts/check.sh` runs ruff, mypy, pytest, ESLint (`no-explicit-any` enforced), tsc, vitest and the production build.
- **Structure:** small modules (`backend/app/api/*` routers, `coach_tools` / `coach`, `lifeevents`, `timeline`, `config.py` for named thresholds); typed TypeScript throughout (`frontend/src/types.ts`).
- **API hardening:** pydantic bounds on every input, upload type/size/PDF-magic limits, per-user rate limit on AI endpoints, security headers (CSP, nosniff, frame deny), path-traversal-safe static serving, one consistent error shape (`{"detail": "..."}`), no stack traces or secrets in responses or logs.
- **Secrets:** `.env` is git-ignored; `.env.example` has placeholders only; the key is a Render environment variable.
- **Accessibility:** axe-core audit on the live site (every tab, dialog and chat state, desktop and phone) reports **0 violations**; labelled inputs, skip link, landmarks and an h1 per view, visible focus rings, keyboard-closable dialog, ARIA for progress/charts, WCAG AA colour contrast, reduced-motion respected.
- **Reliability:** loading, empty and error states with retry on every screen; a cold-start message instead of a blank page.

## Run it

```bash
pip install -r requirements.txt
cd frontend && npm install && npm run build && cd ..
cp .env.example .env     # then put your GEMINI_API_KEY in .env (git-ignored)
cd backend && uvicorn app.main:app --port 8000   # http://localhost:8000
```

Dev: `uvicorn` in `backend/` plus `npm run dev` in `frontend/`. All gates: `pip install -r requirements-dev.txt && scripts/check.sh`. Docker: `docker build -t money-coach . && docker run -p 8000:8000 -e GEMINI_API_KEY=... money-coach`. Render: create a Blueprint from `render.yaml` and set `GEMINI_API_KEY` (SQLite lives in `/tmp` on the free tier, so data resets on restart; the demo reloads in one click).

`DEMO_SCRIPT.md` is the 2:30 video script. Sample files are in `samples/` (`python scripts/generate_samples.py`). Open the app with `?u=anything&tab=coach` to jump to a tab with a fresh anonymous profile. `FINAL_REPORT.md` lists what was verified.

## Layout
```
backend/app/   api/ (routers, schemas)  parsing ingest categorize analytics planner lifeevents timeline
               nudges review coach_tools coach guardrails gemini seed config main db  (+ gemini_cache.json)
backend/tests/ pytest suite     frontend/src/  React + TypeScript (Vite), vitest     samples/  scripts/
```

## Limitations
INR only; per-browser anonymous profile (no login); "unused subscription" relies on a last-used date the user confirms (banks do not expose usage); heuristics are tuned on common Indian bank formats; life-event projections assume today's averages continue.
