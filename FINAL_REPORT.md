# Final report

Live site: https://money-coach-k49s.onrender.com  ·  Repo: https://github.com/SRASHTI2004/money-coach

## Test and quality gates (run with `scripts/check.sh`)

| Gate | Result |
|---|---|
| ruff (Python lint) | passed, 0 issues |
| mypy (Python types, 25 source files) | passed, 0 issues |
| pytest | **69 passed** |
| ESLint (`no-explicit-any` = error, react-hooks, no-console) | passed, 0 issues |
| tsc (strict TypeScript) | passed |
| vitest | **6 passed** |
| Production build (Vite) | passed |
| **Total automated tests** | **75** (69 backend + 6 frontend) |

Backend test coverage by area: parsing (CSV/PDF/SMS), rule learning, recurring + AutoPay detection, what-if maths, life-event engine, timeline, drift nudges, guardrails (blocked and allowed questions, output filter), demo cache replay with Confirm, API flows, and security (upload type/size/fake PDF, validation shape, security headers, uid sanitising, rate limiting, path traversal).

## What was done in this pass

1. **Judges' view:** README now opens with the live link, the two-line problem, a seven-step "Try it in one minute", and a table mapping all 8 brief requirements to features. A **How it works** panel (header button) explains Gemini vs plain code, confirm-before-change, never recommending securities, and sample-data-only.
2. **Code quality:** `main.py` split into focused routers (`api/data`, `plan`, `insights`, `coach_api`) with shared schemas; coach split into `coach_tools` + `coach`; named thresholds in `config.py`; docstrings and type hints on public functions; `any` removed from TypeScript (central `types.ts`); no stray debug prints; ruff, mypy and ESLint clean.
3. **Reliability:** shared loading / empty / error-with-retry states on every screen; 45 s request timeout with friendly messages; a cold-start message (fades in after 3 s) instead of a blank page; Gemini timeout + circuit breaker fall back to rules.
4. **Security:** bounds on every request field, upload extension/size/PDF-magic checks, per-user AI rate limit, security headers (CSP, nosniff, frame deny), path-traversal-safe static serving, one consistent `{"detail": ...}` error shape, internals never leaked, `.env` ignored and `.env.example` placeholders only. No key patterns found in the repo.
5. **Accessibility:** labelled inputs, skip link, ARIA roles (tabs, dialog, progress, charts), visible focus rings, keyboard-closable dialog with focus trap, higher-contrast badge colours, 16 px base font, reduced-motion respected.
6. **Tests:** +7 security tests, +2 frontend test files (formatting and markdown safety).

## Live-site verification
Run against https://money-coach-k49s.onrender.com with real headless Chrome (puppeteer-core), after the final deploy:

| Check | Result |
|---|---|
| Landing page with "Try with demo data" | passed |
| One-click demo load through the real UI | passed |
| How it works dialog opens, closes with Esc | passed |
| All 9 tabs at desktop (1280 px) and phone (390 px) | all render, **0 px horizontal overflow** |
| Life event simulator | passed (chart and goal lanes render) |
| Coach: proposal, Confirm, applied | passed |
| Guardrail: "Which mutual fund should I buy?" | **Guardrail active** badge shown, no product named |
| Paste sample UPI SMS and import | passed |
| Correct a category | "Learned rule" toast, 5 similar rows re-labelled |
| Keyboard: first Tab stop | "Skip to content" |
| **Browser console errors / failed requests (4xx/5xx)** | **none** |
| Security headers on the live API | CSP, X-Frame-Options DENY present |
| Live health | `ai_enabled: true`, pre-computed cache hits recorded |

Deployed asset hash on the live site matches the final local build.

## Not done / known limits

- Data on Render's free tier lives in `/tmp` and resets on restart; the demo reloads in one click. No login (anonymous per-browser id).
- Docker image was not built locally (Docker is not installed here); the Render build is the proof it builds.
- The full-page "slow first load" is a free-tier cold start (about 10 to 30 s); the app shows a waiting message but cannot remove the delay.
- A formal automated accessibility audit (axe/Lighthouse) was not run; accessibility was checked by keyboard flow, ARIA review and contrast choices.
- Gemini was slow and occasionally unavailable during development, which is why demo answers are pre-computed. New questions on the live site call Gemini and fall back to the rule-based coach if it is slow.
