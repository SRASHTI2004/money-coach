# Progress log

| Step | Status |
|---|---|
| Core (ingestion, rules, profile/goals, recurring, what-if, nudges, review, coach + Confirm) | done, tested |
| Landing + premium dashboard, mobile-checked in real Chrome (390px, no overflow) | done |
| Visible AI: Learned-rule toast, SMS/PDF/CSV badges, coach tool steps, Confirm cards, guardrail badge | done |
| Life event simulator (job loss, hike, rent, EMI; EF curve + goal before/after lanes) | done, tested |
| Living money model timeline (logged + detected events, with "why") | done, tested |
| Indian touches: raw SMS paste, UPI AutoPay mandates -> subscriptions, upcoming-mandate price alerts, lakh/crore | done, tested |
| Pre-computed Gemini cache (backend/app/gemini_cache.json) + coach answer replay | done, tested |
| README + DEMO_SCRIPT (2:30) | done |
| Deploy on Render | needs account owner: connect repo, set GEMINI_API_KEY |

Verified end to end in headless Chrome via the real UI: demo button, cached coach answer in ~70 ms, Confirm applies the change,
timeline records it, learned-rule toast, SMS paste import, landing + all tabs at 1280px and 390px.
