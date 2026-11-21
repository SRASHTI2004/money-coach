import { useState } from "react";
import { inr, monthName } from "./api";
import { type Ctx, ErrorBox, Loading, Md, useApi } from "./parts";
import type { Review as ReviewData } from "./types";

export default function Review({ summary }: Ctx) {
  const [month, setMonth] = useState("");
  const { data: r, error, loading, reload } = useApi<ReviewData>("/review" + (month ? "?month=" + month : ""), summary);
  if (error) return <ErrorBox message={error} onRetry={reload} />;
  if (!r) return <Loading what="Writing your review" />;
  const f = r.facts;
  return (
    <>
      <section className="card" aria-labelledby="rv-h">
        <div className="row" style={{ marginBottom: 8 }}>
          <h2 id="rv-h" style={{ marginBottom: 0, flex: 1 }}>Monthly review - {monthName(f.month)}{f.partial_month && " (so far)"}</h2>
          <select aria-label="Choose month" value={month || f.month} onChange={(e) => setMonth(e.target.value)}>{r.months.map((m) => <option key={m} value={m}>{monthName(m)}</option>)}</select>
          <button className="btn sm ghost" onClick={() => window.print()}>Print</button>
        </div>
        <span className={"badge " + (r.ai ? "" : "off")}>{r.ai ? "Written by Gemini from verified numbers" : "Built-in summary (AI offline)"}</span>
        <div style={{ marginTop: 12 }}>{loading ? <Loading what="Writing" /> : <Md text={r.narrative} />}</div>
      </section>
      <div className="grid g4" style={{ marginBottom: 16 }}>
        <div className="stat"><div className="l">Income</div><div className="v">{inr(f.income)}</div></div>
        <div className="stat"><div className="l">Spent</div><div className="v">{inr(f.spend)}</div></div>
        <div className="stat"><div className="l">Left over</div><div className="v">{inr(f.left_over)}</div></div>
        <div className="stat"><div className="l">Savings rate</div><div className="v">{f.savings_rate_pct ?? "-"}%</div></div>
      </div>
      <div className="grid g2 stack">
        <section className="card"><h2>Top categories</h2>
          {f.top_categories.map((c) => <div key={c.category} className="row small" style={{ marginBottom: 6 }}><span style={{ flex: 1 }}>{c.category}</span><b>{inr(c.amount)}</b><span className="mute">{c.share_pct}%</span></div>)}
        </section>
        <section className="card"><h2>Budgets</h2>
          {f.budgets.length === 0 && <p className="mute small">No budgets set.</p>}
          {f.budgets.map((b) => <div key={b.category} className="row small" style={{ marginBottom: 6 }}><span style={{ flex: 1 }}>{b.category}</span>
            <span>{inr(b.spent)} / {inr(b.budget)}</span><span className={"badge " + (b.status === "over" ? "alert" : "good")}>{b.status}</span></div>)}
        </section>
      </div>
    </>
  );
}
