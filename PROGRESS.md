# Progress log

| Step | Status |
|---|---|
| 1. Ingestion (CSV/PDF/SMS) + categorisation + correction rules | done, tested |
| 2. Profile + goals | done, tested |
| 3. Recurring/subscriptions + alerts | done, tested |
| 4. What-if simulator | done, tested |
| 5. Drift nudges | done, tested |
| 6. Monthly review (AI narrative + fallback) | done |
| 7. Coach chat with tools + Confirm flow | done, tested |
| 8. UI (React + TS) | in progress |
| 9. README, DEMO_SCRIPT, Docker/render, deploy | pending |

Notes: Gemini primary `gemini-3.5-flash`, fallback `gemini-3.5-flash-lite` (older 2.x models return 404 for this key).
Gemini calls have a 20s timeout and a 45s circuit breaker, after which rule-based fallbacks answer instantly.
