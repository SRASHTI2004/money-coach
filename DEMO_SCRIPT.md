# Demo video script (2 min 30 sec)

Record on the deployed app at desktop width; resize to phone width for the last 5 seconds. Start on a fresh browser (empty profile). All demo AI answers are pre-computed, so every step below responds instantly. Total target: **2:30** (limit 2:45).

## 0:00-0:15 - One-line pitch + landing
**Show:** landing screen.
**Say:** "Most budgeting apps categorise and stop. Money Coach keeps a living model of your money, in rupees, built for UPI and Indian bank SMS, and it adapts when life changes. It never picks a stock for you."
**Do:** click **Try with demo data**.

## 0:15-0:40 - Messy ingestion + visible parsing (Req 1)
**Show:** dashboard hero (free cash, nudges), then **Transactions**.
**Say:** "That loaded a bank CSV, a PDF statement and bank SMS through the real pipeline. Every row shows whether it came from SMS, PDF or CSV and who categorised it. Unknown merchants were labelled by Gemini."
**Do:** click the **Parsed from SMS** chip, then **Fill sample UPI SMS** -> **Import pasted SMS**.
**Say:** "Raw UPI SMS paste straight in; OTPs and promos are ignored."

## 0:40-0:55 - Correction loop (Req 2)
**Do:** change one transaction's category.
**Show:** the green **Learned rule** toast.
**Say:** "One correction becomes a rule, fixes the past and applies to future uploads, even from another source."

## 0:55-1:15 - Subscriptions + UPI AutoPay (Req 3)
**Do:** **Subscriptions** tab.
**Show:** Netflix ₹649 -> ₹799, Cult.fit "seems unused", the **Upcoming UPI AutoPay mandates** card (Hotstar ₹299 -> ₹349) and the UPI AutoPay badges.
**Say:** "AutoPay mandates are detected as subscriptions, and a mandate notice that is about to cost more is flagged before it debits."

## 1:15-1:50 - Life event simulator (Req 4, 5, innovation)
**Do:** **Life events** tab -> click **Job loss + new EMI**.
**Show:** emergency-fund curve dipping, lowest point, the before/after goal lanes (all goals miss their dates), the Gemini explanation.
**Say:** "Stack a job loss and a new EMI. The month-by-month engine shows the emergency fund dipping to under a month of cover and every goal date slipping. The maths is deterministic; Gemini only explains it."
**Do (5 s):** click **Salary hike 15%** to show goals moving the other way.

## 1:50-2:15 - Agentic coach + Confirm + guardrail (Req 8)
**Do:** **Coach** tab -> click **Set my dining budget to 4000 and explain why**.
**Show:** the numbered tool steps, the proposed-change card -> click **Confirm** -> toast.
**Say:** "The coach uses tools, and can only propose. Nothing changes until I confirm."
**Do:** click **Which mutual fund should I buy?**
**Show:** the **Guardrail active** badge and the educational answer.
**Say:** "Asked for a fund, it explains risk and diversification, names no product, and the disclaimer is always visible."

## 2:15-2:30 - Living model timeline, review, mobile (Req 4, 6, 7)
**Do:** **Timeline** tab, scroll briefly; open **Monthly review** for 3 seconds; resize to phone width.
**Show:** the confirmed Dining budget with its reason, Netflix price rise, Audible detected as cancelled, new freelance income.
**Say:** "Every change to the model is recorded with why, some logged, some detected straight from the statements. Nudges, a Gemini-written monthly review and what-ifs keep it current, and it works on a phone."
