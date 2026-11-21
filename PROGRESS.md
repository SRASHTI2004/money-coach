# Progress log

| Step | Status |
|---|---|
| 1. Ingestion (CSV/PDF/SMS) + categorisation + correction rules | done, tested |
| 2. Profile + goals | done, tested |
| 3. Recurring/subscriptions + alerts | done, tested |
| 4. What-if simulator | done, tested |
| 5. Drift nudges | done, tested |
| 6. Monthly review (AI narrative + fallback) | done |
| 7. Coach chat with tools + Confirm flow | done, tested (live Gemini verified) |
| 8. UI (React + TS, mobile-friendly) | done, builds |
| 9. README, DEMO_SCRIPT, Dockerfile, render.yaml | done |
| 10. Deploy on Render | needs account owner: connect repo, set GEMINI_API_KEY |

Notes: Gemini primary `gemini-3.5-flash`, fallback `gemini-3.5-flash-lite` (2.x models return 404 for this key).
20s timeout + 45s circuit breaker, then rule-based fallbacks answer instantly.
