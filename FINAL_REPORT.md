# Final report

Live site: https://money-coach-k49s.onrender.com  ·  Repo: https://github.com/SRASHTI2004/money-coach  ·  Product thinking: [PRODUCT.md](PRODUCT.md)

## Test and quality gates (run with `scripts/check.sh`)

| Gate | Result |
|---|---|
| ruff (Python lint) | passed, 0 issues |
| mypy (Python types, 25 source files) | passed, 0 issues |
| pytest | **70 passed** |
| ESLint (`no-explicit-any` = error, react-hooks, no-console) | passed, 0 issues |
| tsc (strict TypeScript) | passed |
| vitest | **6 passed** |
| Production build (Vite) | passed |
| **Total automated tests** | **76** (70 backend + 6 frontend) |

Backend coverage by area: parsing (CSV/PDF/SMS), rule learning, recurring + AutoPay detection, what-if maths, life-event engine, timeline, drift nudges, guardrails (blocked and allowed questions, output filter), demo-cache replay with Confirm, API flows, and security (upload type/size/fake PDF, validation shape, security headers, uid sanitising, rate limiting, path traversal, health endpoint incl. HEAD).

## Accessibility audit (axe-core)

axe-core (WCAG 2.0/2.1 A and AA plus best-practice rules) was run in headless Chrome on the **live site**, on every state at desktop (1280 px) and phone (390 px) width: landing, dashboard, How-it-works dialog, coach (empty and with chat, proposal and guardrail answer), life events, what-if, subscriptions, transactions, plan, timeline, monthly review.

- **First run found** (all fixed): teal text below 4.5:1 contrast (status badge, ghost buttons), green income amounts at 4.16:1, `role="tabpanel"` on `<main>` which removed the main landmark (and broke the page region structure), tab roles on `<nav>` which removed the navigation landmark, no level-one heading, the disclaimer outside any landmark, and a scrollable chat area that was not keyboard-focusable.
- **After fixes, on the live site: 0 violations across all 24 audited views.**

## Live-site verification (after the final deploy)

Real headless Chrome against https://money-coach-k49s.onrender.com, run one tool at a time:

| Check | Result |
|---|---|
| Landing page with "Try with demo data" | passed |
| One-click demo load through the real UI | passed |
| How it works dialog opens, closes with Esc | passed |
| All 9 tabs at desktop and phone width | all render, **0 px horizontal overflow** |
| Life event simulator (chart + goal lanes) | passed |
| Coach: proposal, Confirm, applied | passed |
| Guardrail: "Which mutual fund should I buy?" | **Guardrail active** badge, no product named |
| Paste sample UPI SMS and import | passed |
| Correct a category | "Learned rule" toast, 5 similar rows re-labelled |
| Keyboard: first Tab stop | "Skip to content" |
| **Browser console errors / failed requests** | **none** |
| axe-core | **0 violations** (24 views) |
| `GET /api/health` and `HEAD /api/health` | 200 |
| Security headers (CSP, X-Frame-Options DENY, nosniff) | present |

### Cached coach answers and life-event presets
Timed on the live API after the latest deploy (figures include network round-trip from this machine):

| Item | Time | Source |
|---|---|---|
| 6 coach answers (cut dining 30%, why over budget, set dining budget to 4000 + Confirm, subscriptions, goals on track, rent +3000) | 310 to 970 ms | `cached=true`, with their tool steps |
| Guardrail answer (mutual fund) | about 340 ms | enforced in code, model not called |
| 4 life-event presets (hike, job loss, job loss + EMI, rent + hike) | 330 to 400 ms | cached Gemini explanation |
| Monthly review | about 360 ms | cached Gemini narrative |
| Demo load (CSV + PDF + SMS, categorisation from cache) | about 1.2 s | |

All six cached answers and all four presets still hit the cache (health shows `calls: 0` live Gemini calls), so **no cache rebuild was needed**; the cache is keyed to the demo data and the system prompt, neither of which changed.

## Issue found and fixed during the final check
While running three tools against the live site at once, the free instance restarted (its in-memory data was reset). Run one at a time, every check passed. Profiling showed demo loading spent nearly all its time committing to SQLite once per inserted row. Rows are now written in a single transaction: demo load went from 1.24 s to 0.21 s locally, and **four simultaneous demo loads on the live free tier went from about 14.5 s each to about 4 s each** with health pings staying fast (about 0.5 s). This was the only code change in this pass besides the accessibility fixes and the `HEAD` support on the health endpoint.

## Not done / known limits

- Free-tier hosting: first load after idle takes about 10 to 30 s (the app shows a waiting message), and data lives in `/tmp` so it resets when Render restarts the instance; the demo reloads in one click. A very large burst of simultaneous users could still queue on the 0.1-CPU free instance.
- No login (anonymous per-browser id) and no cross-device sync.
- The Docker image was not built locally (Docker is not installed here); the Render build is the proof it builds.
- axe-core covers the automatable subset of WCAG; a manual screen-reader pass (NVDA/VoiceOver) was not done.
- New questions on the live site call Gemini and fall back to the rule-based coach if Gemini is slow; the demo answers above are pre-computed so they never depend on it.

## Code freeze
No further changes are planned before the demo recording. Final code commit: `faa8590`.
