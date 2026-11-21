import { useCallback, useEffect, useState } from "react";
import { api, dateFmt, errMsg, inr } from "./api";
import { type Ctx, ErrorBox } from "./parts";
import type { WhatIfResult } from "./types";

interface Adj { category: string; mode: "percent" | "amount"; value: number }

const PERCENT_RANGE = 100;
const AMOUNT_RANGE = 20000;
const PRESETS: { label: string; adj: Adj[] }[] = [
  { label: "Cut dining out 30%", adj: [{ category: "Dining", mode: "percent", value: -30 }] },
  { label: "Rent goes up ₹3,000", adj: [{ category: "Rent", mode: "amount", value: 3000 }] },
  { label: "Income drops 10%", adj: [{ category: "Income", mode: "percent", value: -10 }] },
  { label: "Cut shopping 50%", adj: [{ category: "Shopping", mode: "percent", value: -50 }] },
  { label: "New ₹8,000 EMI", adj: [{ category: "New EMI", mode: "amount", value: 8000 }] },
];

export default function WhatIf({ summary }: Ctx) {
  const [adjs, setAdjs] = useState<Adj[]>(PRESETS[0].adj);
  const [res, setRes] = useState<WhatIfResult | null>(null);
  const [cats, setCats] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api<string[]>("/categories")
      .then((c) => setCats(["Income", ...c.filter((x) => !["Income", "Savings & Investments", "Transfers"].includes(x))]))
      .catch(() => setCats([]));
  }, []);
  const run = useCallback(async (list: Adj[]) => {
    setBusy(true);
    setError("");
    try {
      setRes(await api<WhatIfResult>("/simulate", { body: { adjustments: list.map((a) => ({ category: a.category, [a.mode]: a.value })) } }));
    } catch (e) { setError(errMsg(e)); } finally { setBusy(false); }
  }, []);
  useEffect(() => {
    let live = true;
    api<WhatIfResult>("/simulate", { body: { adjustments: PRESETS[0].adj.map((a) => ({ category: a.category, [a.mode]: a.value })) } })
      .then((r) => { if (live) setRes(r); })
      .catch((e) => { if (live) setError(errMsg(e)); });
    return () => { live = false; };
  }, [summary]);
  const upd = (i: number, p: Partial<Adj>) => setAdjs(adjs.map((a, j) => (j === i ? { ...a, ...p } : a)));
  const range = (a: Adj) => (a.mode === "percent" ? PERCENT_RANGE : AMOUNT_RANGE);

  return (
    <>
      <section className="card" aria-labelledby="wi-h">
        <h2 id="wi-h">What-if simulator</h2>
        <p className="small mute" style={{ marginTop: -6 }}>Pure arithmetic on your real averages - no AI guesses. Try a scenario and see what it does to free cash and goal dates.</p>
        <div className="chips" role="group" aria-label="Scenario presets">{PRESETS.map((p) => <button key={p.label} className="chip" onClick={() => { setAdjs(p.adj); run(p.adj); }}>{p.label}</button>)}</div>
        {adjs.map((a, i) => (
          <div className="row" key={i} style={{ marginBottom: 10 }}>
            {a.category === "New EMI" || !cats.includes(a.category)
              ? <input aria-label="Expense name" value={a.category} maxLength={40} onChange={(e) => upd(i, { category: e.target.value })} style={{ width: 130 }} />
              : <select aria-label="Category" value={a.category} onChange={(e) => upd(i, { category: e.target.value })}>{cats.map((c) => <option key={c}>{c}</option>)}</select>}
            <select aria-label="Change type" value={a.mode} onChange={(e) => upd(i, { mode: e.target.value as Adj["mode"], value: 0 })}>
              <option value="percent">% change</option><option value="amount">&#8377; per month</option></select>
            <input type="range" aria-label="Change amount" className="slider" style={{ flex: 1, minWidth: 120 }}
              min={-range(a)} max={range(a)} step={a.mode === "percent" ? 5 : 500}
              value={a.value} onChange={(e) => upd(i, { value: Number(e.target.value) })} />
            <input type="number" aria-label="Change value" value={a.value} style={{ width: 90 }} onChange={(e) => upd(i, { value: Number(e.target.value) })} />
            <button className="btn sm muted" aria-label="Remove change" onClick={() => setAdjs(adjs.filter((_, j) => j !== i))}>&times;</button>
          </div>
        ))}
        <div className="row">
          <button className="btn sm ghost" onClick={() => setAdjs([...adjs, { category: "Dining", mode: "percent", value: -10 }])}>+ Add change</button>
          <button className="btn" disabled={busy} onClick={() => run(adjs)}>{busy ? "Calculating..." : "Run simulation"}</button>
        </div>
      </section>

      {error && <ErrorBox message={error} onRetry={() => run(adjs)} />}
      {res && (
        <section className="card" aria-labelledby="wi-r" aria-live="polite">
          <h2 id="wi-r">Result</h2>
          <div className="grid g3" style={{ marginBottom: 14 }}>
            <div className="stat"><div className="l">Free cash / month</div><div className="v">{inr(res.after.free_cash)}</div><div className="s">was {inr(res.before.free_cash)}</div></div>
            <div className="stat"><div className="l">Change / month</div><div className="v" style={{ color: res.delta_free_cash >= 0 ? "var(--good-text)" : "var(--bad-text)" }}>{inr(res.delta_free_cash, true)}</div></div>
            <div className="stat"><div className="l">Change / year</div><div className="v" style={{ color: res.delta_yearly >= 0 ? "var(--good-text)" : "var(--bad-text)" }}>{inr(res.delta_yearly, true)}</div></div>
          </div>
          <p style={{ marginTop: 0 }}>{res.summary}</p>
          <div className="scroll-x"><table>
            <thead><tr><th scope="col">Goal</th><th scope="col">Target date</th><th scope="col">Before</th><th scope="col">After</th><th scope="col">Status</th></tr></thead>
            <tbody>{res.goal_changes.map((g) => (
              <tr key={g.id}><td><b>{g.name}</b></td><td>{dateFmt(g.target_date)}</td><td>{dateFmt(g.before_date)}</td>
                <td>{dateFmt(g.after_date)} {g.shift_months ? <span className="mute small">({g.shift_months > 0 ? "+" : ""}{g.shift_months} mo)</span> : null}</td>
                <td><span className={"badge " + (g.after_on_track ? "good" : "warn")}>{g.after_on_track ? "On track" : "Behind"}</span></td></tr>
            ))}</tbody></table></div>
        </section>
      )}
    </>
  );
}
