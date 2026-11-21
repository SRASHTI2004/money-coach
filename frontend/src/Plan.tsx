import { useEffect, useState } from "react";
import { api, dateFmt, inr } from "./api";
import { Ctx, Progress } from "./parts";

const num = (v: string) => (v === "" ? 0 : Number(v));

export default function Plan({ summary, toast, refresh }: Ctx) {
  const [p, setP] = useState<any>(null);
  const [goals, setGoals] = useState<any>(null);
  const [cats, setCats] = useState<string[]>([]);
  const [ng, setNg] = useState({ name: "", target_amount: "", saved: "", target_date: "", monthly_contrib: "" });
  const load = async () => { setP(await api("/profile")); setGoals(await api("/goals")); };
  useEffect(() => { load().catch(() => {}); api("/categories").then(setCats); }, [summary]);
  if (!p || !goals) return <p className="mute">Loading...</p>;

  const saveProfile = async () => { await api("/profile", { method: "PUT", body: p }); toast("Profile saved."); await refresh(); };
  const setBudget = (c: string, v: string) => setP({ ...p, budgets: { ...p.budgets, [c]: num(v) } });
  const addGoal = async () => {
    if (!ng.name || !ng.target_date || !ng.target_amount) return toast("Name, target amount and date are required.");
    await api("/goals", { body: { name: ng.name, target_amount: num(ng.target_amount), saved: num(ng.saved), target_date: ng.target_date, monthly_contrib: num(ng.monthly_contrib) } });
    setNg({ name: "", target_amount: "", saved: "", target_date: "", monthly_contrib: "" }); toast("Goal added."); await refresh();
  };
  const patchGoal = async (g: any, patch: any) => {
    await api("/goals/" + g.id, { method: "PUT", body: { name: g.name, target_amount: g.target, saved: g.saved, target_date: g.target_date, monthly_contrib: g.planned, ...patch } });
    await refresh();
  };

  return (
    <>
      <div className="card">
        <h2>Your money profile</h2>
        <div className="grid g3">
          <label className="f">Monthly income (take-home)<input type="number" value={p.monthly_income ?? ""} onChange={(e) => setP({ ...p, monthly_income: e.target.value ? Number(e.target.value) : null })} placeholder="auto from statements" /></label>
          <label className="f">Emergency fund saved<input type="number" value={p.emergency_fund} onChange={(e) => setP({ ...p, emergency_fund: num(e.target.value) })} /></label>
          <label className="f">Adding to it each month<input type="number" value={p.emergency_monthly} onChange={(e) => setP({ ...p, emergency_monthly: num(e.target.value) })} /></label>
          <label className="f">Target (months of essentials)<input type="number" value={p.emergency_target_months} onChange={(e) => setP({ ...p, emergency_target_months: num(e.target.value) })} /></label>
        </div>
        <h3 style={{ marginTop: 18 }}>Fixed costs</h3>
        {p.fixed_costs.map((f: any, i: number) => (
          <div className="row" key={i} style={{ marginTop: 6 }}>
            <input value={f.name} onChange={(e) => { const fc = [...p.fixed_costs]; fc[i] = { ...f, name: e.target.value }; setP({ ...p, fixed_costs: fc }); }} />
            <input type="number" value={f.amount} style={{ width: 110 }} onChange={(e) => { const fc = [...p.fixed_costs]; fc[i] = { ...f, amount: num(e.target.value) }; setP({ ...p, fixed_costs: fc }); }} />
            <button className="btn sm muted" onClick={() => setP({ ...p, fixed_costs: p.fixed_costs.filter((_: any, j: number) => j !== i) })}>Remove</button>
          </div>
        ))}
        <div className="row" style={{ marginTop: 8 }}>
          <button className="btn sm ghost" onClick={() => setP({ ...p, fixed_costs: [...p.fixed_costs, { name: "New fixed cost", amount: 0 }] })}>+ Add fixed cost</button>
          <span className="small mute">Total {inr(p.fixed_costs.reduce((a: number, f: any) => a + f.amount, 0))}/month</span>
        </div>
        <h3 style={{ marginTop: 18 }}>Monthly budgets</h3>
        <div className="grid g3" style={{ marginTop: 6 }}>
          {cats.filter((c) => !["Income", "Savings & Investments", "Transfers", "Cash", "Other"].includes(c)).map((c) => (
            <label className="f" key={c}>{c}<input type="number" value={p.budgets[c] ?? ""} placeholder="no budget" onChange={(e) => setBudget(c, e.target.value)} /></label>
          ))}
        </div>
        <div style={{ marginTop: 14 }}><button className="btn" onClick={saveProfile}>Save profile</button></div>
      </div>

      <div className="card">
        <h2>Goals</h2>
        <p className="small mute" style={{ marginTop: -6 }}>Free cash is {inr(goals.free_cash)}/month; your plan sets aside {inr(goals.planned_total)}. Any extra is steered to goals that are behind.</p>
        {goals.items.map((g: any) => (
          <div key={g.id} style={{ padding: "12px 0", borderBottom: "1px solid var(--line)" }}>
            <div className="row"><b style={{ flex: 1 }}>{g.name}</b>
              <span className={"badge " + (g.on_track ? "good" : "warn")}>{g.on_track ? "On track" : "Behind"}</span>
              {g.kind === "goal" && <button className="btn sm muted" onClick={async () => { await api("/goals/" + g.id, { method: "DELETE" }); refresh(); }}>Delete</button>}</div>
            <Progress pct={g.pct} tone={g.on_track ? "good" : "warn"} />
            <div className="small mute" style={{ marginTop: 4 }}>
              {inr(g.saved)} of {inr(g.target)}{g.target_date && <> by {dateFmt(g.target_date)}</>} - funding {inr(g.contribution)}/mo
              {g.required_monthly != null && <> (needs {inr(g.required_monthly)})</>} - projected {dateFmt(g.projected_date)}
            </div>
            {g.kind === "goal" && (
              <div className="row small" style={{ marginTop: 6 }}>
                <label>Plan/month <input type="number" defaultValue={g.planned} style={{ width: 100 }} onBlur={(e) => num(e.target.value) !== g.planned && patchGoal(g, { monthly_contrib: num(e.target.value) })} /></label>
                <label>Saved so far <input type="number" defaultValue={g.saved} style={{ width: 110 }} onBlur={(e) => num(e.target.value) !== g.saved && patchGoal(g, { saved: num(e.target.value) })} /></label>
              </div>
            )}
          </div>
        ))}
        <h3 style={{ marginTop: 16 }}>Add a goal</h3>
        <div className="grid g3" style={{ marginTop: 6 }}>
          <label className="f">Name<input value={ng.name} onChange={(e) => setNg({ ...ng, name: e.target.value })} /></label>
          <label className="f">Target amount<input type="number" value={ng.target_amount} onChange={(e) => setNg({ ...ng, target_amount: e.target.value })} /></label>
          <label className="f">Target date<input type="date" value={ng.target_date} onChange={(e) => setNg({ ...ng, target_date: e.target.value })} /></label>
          <label className="f">Saved so far<input type="number" value={ng.saved} onChange={(e) => setNg({ ...ng, saved: e.target.value })} /></label>
          <label className="f">Monthly contribution<input type="number" value={ng.monthly_contrib} onChange={(e) => setNg({ ...ng, monthly_contrib: e.target.value })} /></label>
        </div>
        <div style={{ marginTop: 12 }}><button className="btn" onClick={addGoal}>Add goal</button></div>
      </div>
    </>
  );
}
