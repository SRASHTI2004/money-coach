# Product thinking - Money Coach

## Who it is for

**Priya, 27, salaried in Bengaluru.** She is a 22-to-35-year-old Indian professional who pays almost everything by UPI and card, gets a bank SMS for each payment, and has a few goals (a trip, a laptop, an emergency fund) plus an EMI and a handful of subscriptions. She is not a finance person and does not want to learn a spreadsheet. She wants to know, in plain rupees, "am I okay, and what happens if something changes?"

## The problem, and three insights

Budgeting apps categorise transactions and stop. They do not understand goals with dates, and they do not adapt when life changes.

1. **Money data is messy and lives in SMS.** In India the most complete record of spending is a stream of bank SMS and UPI narrations, plus statements in whatever layout a bank chose. An app that only accepts clean data is dead on arrival, so ingestion has to cope with CSV, PDF and raw SMS.
2. **Categorising is not the point; being correct once is.** Users abandon trackers because the same wrong label keeps coming back. One correction must become a rule that fixes the past and the future.
3. **People ask "what if", not "what was".** The real decisions are forward-looking: a rent rise, a new EMI, a job change. A coach is useful when it turns a worry into a number and a date, and when it notices drift or a price rise before the user does.

## Jobs to be done

- *When* I get a statement or SMS, *help me* see where my money went without cleaning anything up.
- *When* a label is wrong, *let me* fix it once.
- *When* something quietly costs more (a subscription, an AutoPay mandate), *tell me* before it hurts.
- *When* I am planning a goal, *show me* whether I will make the date at my current pace.
- *When* life might change, *show me* what it does to my safety net and my goals, month by month.
- *When* I overspend, *nudge me* early enough to act, and explain why.
- *When* the month ends, *give me* a short, honest review.
- *When* I ask about investing, *teach me* the concepts and risks, and never tell me what to buy.

## Why each of the 8 features exists

| Feature | Why it exists |
|---|---|
| 1. Messy ingestion + categorisation | Insight 1: without it nothing else has data. CSV, PDF and SMS are what Indian users actually have. |
| 2. Correction loop | Insight 2: trust comes from fixing a mistake once. |
| 3. Recurring payments + subscriptions | Small recurring leaks (price rises, unused plans, AutoPay hikes) are the easiest savings to miss. |
| 4. Persistent profile | Advice without income, fixed costs, a safety net and dated goals is generic. The profile is the "living model". |
| 5. Goal planner + what-if (and life events) | Insight 3: converts "what if" into a number and a date. |
| 6. Nudges | Drift matters while it is still fixable, so the app speaks up mid-month. |
| 7. Monthly review | A calm summary builds the habit and shows progress. |
| 8. Guardrails | A budgeting coach is trusted with personal data; recommending products would be out of its depth and a regulatory risk. |

## Key decisions and trade-offs

- **AI explains, code calculates, the user confirms.** All money maths is deterministic and tested, so numbers are never hallucinated. Gemini parses messy text, labels unknown merchants, narrates results and runs the tool-calling coach. The coach can only *propose* changes; nothing applies until the user clicks Confirm. Trade-off: less "magic", far more trust.
- **No securities advice, enforced in code.** Product-pick questions get an educational answer on both the input and the output side, plus a visible badge and disclaimer. Trade-off: the coach declines a very common question, deliberately.
- **Deterministic detection over ML for subscriptions.** Regular gaps and stable amounts are explainable ("seen 4 times, every month"). Trade-off: needs 3+ occurrences.
- **"Seems unused" relies on a last-used date the user confirms.** Banks do not expose app usage; we say so rather than guess.
- **Graceful AI failure.** Timeouts and a circuit breaker fall back to built-in rules so the product never dead-ends.
- **Pre-computed demo answers.** A judge or new user gets an instant, high-quality first experience; new inputs still go to live Gemini.
- **Anonymous, no signup, sample data for the demo.** Lowest friction to value. Trade-off: no cross-device sync yet.
- **Privacy-minded by default.** No bank credentials are ever collected; users bring their own statements or SMS.

## Success metrics we would track

- **Activation:** share of new users who reach a populated dashboard (demo or own data) within 2 minutes.
- **Ingestion quality:** share of transactions categorised correctly without edits; share of statements/SMS parsed without the AI rescue path.
- **Learning:** corrections per user over time (should fall) and rule reuse rate.
- **Value moments:** subscriptions or AutoPay hikes flagged and acted on; nudges followed by a spending change; what-ifs and life events run per user.
- **Trust:** proposals confirmed vs dismissed; guardrail triggers (expected) and zero product recommendations in audits.
- **Retention:** users who come back to review a month or add new statements.
- **Reliability:** AI fallback rate, p95 response time, error rate.

## What we would build next

1. **Gmail / SMS auto-ingest** (with explicit consent) so the model updates without uploads.
2. **Account Aggregator (AA) integration** for consented bank data instead of files.
3. **Multi-month forecasting** with variable income (freelancers) and seasonal expenses (insurance, annual fees).
4. **Household mode** (shared goals, split rent) and festival or travel planning.
5. **Smarter recurring detection** (annual plans, family plans) and one-tap "cancel or revoke mandate" guidance.
6. **Login and sync** across devices, with export and delete-my-data controls.
7. **Evaluation harness** for parsing accuracy across bank formats and for guardrail red-teaming.
