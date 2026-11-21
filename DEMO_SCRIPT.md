# Demo video script (3 minutes)

Record the deployed app in a desktop browser; resize once to phone width near the end. Start on an empty profile (click **Clear data** first).

## 0:00-0:15 - The problem
**Show:** the landing screen ("Your money, understood").
**Say:** "Budgeting apps categorise transactions and stop. They don't know my goals and they don't adapt. Money Coach keeps a living model of my money in INR, with UPI and Indian bank SMS, and a coach that can model scenarios but never tells me which stock to buy."

## 0:15-0:50 - Req 1: messy ingestion + categorisation
**Do:** click **Load demo data**. (Or go to Transactions and upload `hdfc_aug_sep_2026.csv`, `icici_oct_2026_statement.pdf`, then paste `sms_quick_paste.txt`.)
**Show:** the import report: CSV, PDF, SMS each read; "categorised by built-in / learned / Gemini".
**Say:** "A bank CSV with a preamble, a PDF statement where direction is inferred from the running balance, and raw SMS with OTPs and promos ignored. Unknown merchants like a local tiffin centre are categorised by Gemini."

## 0:50-1:15 - Req 2: correction loop
**Do:** Transactions tab, change a merchant's category (e.g. a Dining item to Shopping).
**Show:** the toast "Learned: merchant -> category. Also updated N other transactions." Scroll to "Rules you've taught the coach".
**Say:** "One correction teaches a rule on the merchant, fixes the past, and applies to future uploads, even from a different source like SMS."

## 1:15-1:40 - Req 3: subscriptions + alerts
**Do:** Subscriptions tab.
**Show:** Netflix price change (₹649 to ₹799, +₹1,800/year), Cult.fit "seems unused" (80 days), the Netflix/Hotstar overlap. Click **I used it recently** on one.
**Say:** "Detection is deterministic: same merchant, regular gaps. It flags price changes, unused services and overlaps."

## 1:40-2:00 - Req 4 + 6: profile, goals, nudges
**Do:** Plan & goals tab (income, fixed costs, emergency fund, budgets, three goals with dates), then Dashboard.
**Show:** nudges: Dining over budget, Japan vacation behind schedule. Click **Explain this** on Dining.
**Say:** "The profile and goals persist. Nudges fire when pace drifts off plan, and Gemini explains them from the real numbers."

## 2:00-2:25 - Req 5: what-if simulator
**Do:** What-if tab. Click "Cut dining out 30%", then "Rent goes up ₹3,000".
**Show:** free cash before/after, yearly impact, and the goal table with shifted dates and "Behind" badges.
**Say:** "This is pure arithmetic on my own averages, not an AI guess. Dining down 30% brings Japan closer; a rent hike pushes every goal out."

## 2:25-2:40 - Req 7: monthly review
**Do:** Monthly review tab.
**Show:** the narrative badge "Written by Gemini from verified numbers", top categories, budgets.
**Say:** "Numbers are computed in code; Gemini only narrates them."

## 2:40-3:00 - Req 8 + agentic coach: confirm flow and guardrails
**Do:** Coach tab. Ask "What if I cut dining out by 30%?" (tool chips appear, a proposal card shows). Click **Confirm**, then open the Dashboard to show the new budget. Back in Coach ask "Which mutual fund should I buy?".
**Show:** the "Coach used: run_what_if / propose_change" chips, the Confirm card, the guardrail answer (educational, no product) and the bottom disclaimer.
**Say:** "The coach calls tools and can only propose changes; nothing applies until I confirm. Asked for a fund, it explains risk and diversification but never names a product. That is enforced in code on both input and output, and the disclaimer is always visible. If Gemini is down, the badge flips to rules mode and everything still works."

**Close (last 3 seconds):** shrink the browser to phone width to show the mobile layout.
