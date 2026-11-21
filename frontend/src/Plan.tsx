import { useEffect, useState } from "react";
import { api, dateFmt, errMsg, inr } from "./api";
import { type Ctx, ErrorBox, Loading, Progress, useApi } from "./parts";
import type { GoalsResponse, Profile } from "./types";

const num = (v: string): number => (v === "" ? 0 : Number(v));
const NO_BUDGET = ["Income", "Savings & Investments", "Transfers", "Cash", "Other"];
const BLANK_GOAL = { name: "", target_amount: "", saved: "", target_date: "", monthly_contrib: "" };

export default function Plan({ summary, toast, refresh }: Ctx) {
  const prof = useApi<Profile>("/profile", summary);
  const goals = useApi<GoalsResponse>("/goals", summary);
  const [edits, setP] = useState<Profile | null>(null);
  const p = edits ?? prof.data;
  const [cats, setCats] = useState<string[]>([]);
  const [ng, setNg] = useState(BLANK_GOAL);
  useEffect(() => { api<string[]>("/categories").then(setCats).catch(() => setCats([])); }, []);

  if ((prof.loading && !p) || (goals.loading && !goals.data)) return <Loading what="Loading your plan" />;
  if (prof.error || goals.error) return <ErrorBox message={prof.error || goals.error} onRetry={() => { prof.reload(); goals.reload(); }} />;
  if (!p || !goals.data) return null;
  const g = goals.data;

  const saveProfile = async () => {
    try { await api("/profile", { method: "PUT", body: p }); toast("Profile saved."); setP(null); await refresh(); } catch (e) { toast(errMsg(e)); }
  };
  const setBudget = (c: string, v: string) => setP({ ...p, budgets: { ...p.budgets, [c]: num(v) } });
  const addGoal = async () => {
    if (!ng.name || !ng.target_date || !ng.target_amount) return toast("Name, target amount and date are required.");
    try {
      await api("/goals", { body: { name: ng.name, target_amount: num(ng.target_amount), saved: num(ng.saved), target_date: ng.target_date, monthly_contrib: num(ng.monthly_contrib) } });
      setNg(BLANK_GOAL);
      toast("Goal added.");
      await refresh();
    } catch (e) { toast(errMsg(e)); }
  };
  const patchGoal = async (id: number | string, patch: Record<string, number>) => {
    const cur = g.items.find((x) => x.id === id);
    if (!cur || !cur.target_date) return;
    try {
      await api("/goals/" + id, { method: "PUT", body: { name: cur.name, target_amount: cur.target, saved: cur.saved, target_date: cur.target_date, monthly_contrib: cur.planned, ...patch } });
      await refresh();
    } catch (e) { toast(errMsg(e)); }
  };

  return (
    <>
      <section className="card" aria-labelledby="prof-h">
        <h2 id="prof-h">Your money profile</h2>
        <div className="grid g3">
          <label className="f">Monthly income (take-home)<input type="number" min={0} value={p.monthly_income ?? ""} onChange={(e) => setP({ ...p, monthly_income: e.target.value ? Number(e.target.value) : null })} placeholder="auto from statements" /></label>
          <label className="f">Emergency fund saved<input type="number" min={0} value={p.emergency_fund} onChange={(e) => setP({ ...p, emergency_fund: num(e.target.value) })} /></label>
          <label className="f">Adding to it each month<input type="number" min={0} value={p.emergency_monthly} onChange={(e) => setP({ ...p, emergency_monthly: num(e.target.value) })} /></label>
          <label className="f">Target (months of essentials)<input type="number" min={0} max={60} value={p.emergency_target_months} onChange={(e) => setP({ ...p, emergency_target_months: num(e.target.value) })} /></label>
        </div>
        <h3 style={{ marginTop: 18 }}>Fixed costs</h3>
        {p.fixed_costs.map((f, i) => (
          <div className="row" key={i} style={{ marginTop: 6 }}>
            <input aria-label={`Fixed cost ${i + 1} name`} value={f.name} onChange={(e) => setP({ ...p, fixed_costs: p.fixed_costs.map((x, j) => (j === i ? { ...x, name: e.target.value } : x)) })} />
            <input aria-label={`Fixed cost ${i + 1} amount`} type="number" min={0} value={f.amount} style={{ width: 110 }} onChange={(e) => setP({ ...p, fixed_costs: p.fixed_costs.map((x, j) => (j === i ? { ...x, amount: num(e.target.value) } : x)) })} />
            <button className="btn sm muted" onClick={() => setP({ ...p, fixed_costs: p.fixed_costs.filter((_, j) => j !== i) })}>Remove</button>
          </div>
        ))}
        <div className="row" style={{ marginTop: 8 }}>
          <button className="btn sm ghost" onClick={() => setP({ ...p, fixed_costs: [...p.fixed_costs, { name: "New fixed cost", amount: 0 }] })}>+ Add fixed cost</button>
          <span className="small mute">Total {inr(p.fixed_costs.reduce((a, f) => a + f.amount, 0))}/month</span>
        </div>
        <h3 style={{ marginTop: 18 }}>Monthly budgets</h3>
        <div className="grid g3" style={{ marginTop: 6 }}>
          {cats.filter((c) => !NO_BUDGET.includes(c)).map((c) => (
            <label className="f" key={c}>{c}<input type="number" min={0} value={p.budgets[c] ?? ""} placeholder="no budget" onChange={(e) => setBudget(c, e.target.value)} /></label>
          ))}
        </div>
        <div style={{ marginTop: 14 }}><button className="btn" onClick={saveProfile}>Save profile</button></div>
      </section>

      <section className="card" aria-labelledby="goals-h">
        <h2 id="goals-h">Goals</h2>
        <p className="small mute" style={{ marginTop: -6 }}>Free cash is {inr(g.free_cash)}/month; your plan sets aside {inr(g.planned_total)}. Any extra is steered to goals that are behind.</p>
        {g.items.map((x) => (
          <div key={x.id} className="sub-row">
            <div className="row"><b style={{ flex: 1 }}>{x.name}</b>
              <span className={"badge " + (x.on_track ? "good" : "warn")}>{x.on_track ? "On track" : "Behind"}</span>
              {x.kind === "goal" && <button className="btn sm muted" onClick={async () => { try { await api("/goals/" + x.id, { method: "DELETE" }); await refresh(); } catch (e) { toast(errMsg(e)); } }}>Delete</button>}</div>
            <Progress pct={x.pct} tone={x.on_track ? "good" : "warn"} label={`${x.name} progress`} />
            <div className="small mute" style={{ marginTop: 4 }}>
              {inr(x.saved)} of {inr(x.target)}{x.target_date && <> by {dateFmt(x.target_date)}</>} &middot; funding {inr(x.contribution)}/mo
              {x.required_monthly != null && <> (needs {inr(x.required_monthly)})</>} &middot; projected {dateFmt(x.projected_date)}
            </div>
            {x.kind === "goal" && (
              <div className="row small" style={{ marginTop: 6 }}>
                <label>Plan/month <input type="number" min={0} defaultValue={x.planned} style={{ width: 100 }} onBlur={(e) => num(e.target.value) !== x.planned && patchGoal(x.id, { monthly_contrib: num(e.target.value) })} /></label>
                <label>Saved so far <input type="number" min={0} defaultValue={x.saved} style={{ width: 110 }} onBlur={(e) => num(e.target.value) !== x.saved && patchGoal(x.id, { saved: num(e.target.value) })} /></label>
              </div>
            )}
          </div>
        ))}
        <h3 style={{ marginTop: 16 }}>Add a goal</h3>
        <div className="grid g3" style={{ marginTop: 6 }}>
          <label className="f">Name<input value={ng.name} maxLength={80} onChange={(e) => setNg({ ...ng, name: e.target.value })} /></label>
          <label className="f">Target amount<input type="number" min={1} value={ng.target_amount} onChange={(e) => setNg({ ...ng, target_amount: e.target.value })} /></label>
          <label className="f">Target date<input type="date" value={ng.target_date} onChange={(e) => setNg({ ...ng, target_date: e.target.value })} /></label>
          <label className="f">Saved so far<input type="number" min={0} value={ng.saved} onChange={(e) => setNg({ ...ng, saved: e.target.value })} /></label>
          <label className="f">Monthly contribution<input type="number" min={0} value={ng.monthly_contrib} onChange={(e) => setNg({ ...ng, monthly_contrib: e.target.value })} /></label>
        </div>
        <div style={{ marginTop: 12 }}><button className="btn" onClick={addGoal}>Add goal</button></div>
      </section>
    </>
  );
}
