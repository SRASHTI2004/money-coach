import { useEffect, useState } from "react";
import { api, inr, monthName } from "./api";
import { Ctx, Md } from "./parts";

export default function Review({ summary }: Ctx) {
  const [month, setMonth] = useState("");
  const [r, setR] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    setBusy(true);
    api("/review" + (month ? "?month=" + month : "")).then(setR).finally(() => setBusy(false));
  }, [month, summary]);
  if (!r) return <p className="mute">{busy ? "Writing your review..." : "No data yet."}</p>;
  const f = r.facts;
  return (
    <>
      <div className="card">
        <div className="row" style={{ marginBottom: 8 }}>
          <h2 style={{ marginBottom: 0, flex: 1 }}>Monthly review - {monthName(f.month)}{f.partial_month && " (so far)"}</h2>
          <select value={month || f.month} onChange={(e) => setMonth(e.target.value)}>{r.months.map((m: string) => <option key={m} value={m}>{monthName(m)}</option>)}</select>
          <button className="btn sm ghost" onClick={() => window.print()}>Print</button>
        </div>
        <span className={"badge " + (r.ai ? "" : "off")}>{r.ai ? "Written by Gemini from verified numbers" : "Built-in summary (AI offline)"}</span>
        <div style={{ marginTop: 12 }}>{busy ? <p className="mute">Writing...</p> : <Md text={r.narrative} />}</div>
      </div>
      <div className="grid g4" style={{ marginBottom: 16 }}>
        <div className="stat"><div className="l">Income</div><div className="v">{inr(f.income)}</div></div>
        <div className="stat"><div className="l">Spent</div><div className="v">{inr(f.spend)}</div></div>
        <div className="stat"><div className="l">Left over</div><div className="v">{inr(f.left_over)}</div></div>
        <div className="stat"><div className="l">Savings rate</div><div className="v">{f.savings_rate_pct ?? "-"}%</div></div>
      </div>
      <div className="grid g2 stack">
        <div className="card"><h2>Top categories</h2>
          {f.top_categories.map((c: any) => <div key={c.category} className="row small" style={{ marginBottom: 6 }}><span style={{ flex: 1 }}>{c.category}</span><b>{inr(c.amount)}</b><span className="mute">{c.share_pct}%</span></div>)}
        </div>
        <div className="card"><h2>Budgets</h2>
          {f.budgets.length === 0 && <p className="mute small">No budgets set.</p>}
          {f.budgets.map((b: any) => <div key={b.category} className="row small" style={{ marginBottom: 6 }}><span style={{ flex: 1 }}>{b.category}</span>
            <span>{inr(b.spent)} / {inr(b.budget)}</span><span className={"badge " + (b.status === "over" ? "alert" : "good")}>{b.status}</span></div>)}
        </div>
      </div>
    </>
  );
}
