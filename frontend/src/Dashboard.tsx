import { useState } from "react";
import { api, errMsg, inr, inrShort, monthName } from "./api";
import { type Ctx, Donut, ErrorBox, Loading, Progress, Sev, Trend, useApi } from "./parts";
import type { Goal, Nudge, NudgeExplanation } from "./types";

const VISIBLE_NUDGES = 3;

export default function Dashboard({ summary: s, toast, goTab }: Ctx) {
  const { data: nudges, error, loading, reload } = useApi<Nudge[]>("/nudges", s);
  const [open, setOpen] = useState<Record<string, NudgeExplanation>>({});
  const [all, setAll] = useState(false);

  const explain = async (id: string) => {
    setOpen((o) => ({ ...o, [id]: { loading: true } }));
    try {
      const r = await api<NudgeExplanation>("/nudges/explain?id=" + encodeURIComponent(id));
      setOpen((o) => ({ ...o, [id]: r }));
    } catch (e) {
      setOpen((o) => Object.fromEntries(Object.entries(o).filter(([k]) => k !== id)));
      toast(errMsg(e));
    }
  };

  const months = s.months;
  const cur = months[months.length - 1];
  const snap = s.snapshot;
  const budgets = s.profile.budgets;
  const cats = Object.entries(cur.by_cat).filter(([, v]) => v > 0)
    .map(([label, value]) => ({ label, value })).sort((a, b) => b.value - a.value);
  const list = nudges ?? [];
  const urgent = list.filter((n) => n.severity !== "info").length;
  const shown = all ? list : list.slice(0, VISIBLE_NUDGES);
  const dated = snap.goals.items.filter((g: Goal) => g.kind === "goal");
  const onTrack = dated.filter((g) => g.on_track).length;

  return (
    <>
      <div className="card hero-card">
        <div className="l">Free cash each month</div>
        <div className="big-num">{inr(snap.free_cash)}</div>
        <div className="small">
          After {inr(snap.spend)} of spending{snap.invested ? ` and ${inr(snap.invested)} of SIPs` : ""}, from {inr(snap.income)} income.
          Your plan sets aside {inr(snap.goals.planned_total)} for goals.
        </div>
        <div className="row" style={{ marginTop: 12 }}>
          <span className={"pill " + (urgent ? "warn" : "good")}>{urgent ? `${urgent} thing${urgent > 1 ? "s" : ""} need attention` : "All on plan"}</span>
          <span className="pill">{onTrack}/{dated.length} goals on track</span>
          <span className="pill">as of {s.as_of}</span>
        </div>
      </div>

      <div className="grid g3" style={{ marginBottom: 16 }}>
        <div className="stat"><div className="l">Spent in {monthName(cur.month)}</div><div className="v">{inr(cur.spend)}</div><div className="s">{inrShort(cur.spend)} so far</div></div>
        <div className="stat"><div className="l">Income / month</div><div className="v">{inr(snap.income)}</div><div className="s">{s.profile.monthly_income ? "from your profile" : "estimated"}</div></div>
        <div className="stat"><div className="l">Emergency fund</div><div className="v">{snap.emergency_months ?? "-"} mo</div><div className="s">{inr(s.profile.emergency_fund)} saved &middot; target {s.profile.emergency_target_months} mo</div></div>
      </div>

      <section className="card" aria-labelledby="nudges-h">
        <h2 id="nudges-h">Nudges {list.length > 0 && <span className="badge info">{list.length}</span>}</h2>
        {loading && !nudges && <Loading what="Checking your plan" />}
        {error && <ErrorBox message={error} onRetry={reload} />}
        {nudges && list.length === 0 && <p className="mute">All on plan - nothing needs your attention.</p>}
        {shown.map((n) => (
          <div key={n.id} className={"nudge " + n.severity}>
            <div className="row"><b style={{ flex: 1 }}>{n.title}</b><Sev s={n.severity} /></div>
            <div className="small">{n.body}</div>
            <div className="row" style={{ marginTop: 6 }}>
              <button className="btn sm ghost" onClick={() => explain(n.id)}>Explain this</button>
              {n.kind === "goal" && <button className="btn sm ghost" onClick={() => goTab("whatif")}>Try what-if</button>}
              {n.kind === "subscription" && <button className="btn sm ghost" onClick={() => goTab("subs")}>See subscriptions</button>}
            </div>
            {open[n.id] && (
              <div className="small ai-note" style={{ marginTop: 8 }} aria-live="polite">
                {open[n.id].loading ? "Thinking..." : <>
                  {open[n.id].explanation}
                  <div className="mute" style={{ marginTop: 4 }}>{open[n.id].ai ? "Explained by Gemini from your numbers" : "Built-in explanation"}</div>
                </>}
              </div>
            )}
          </div>
        ))}
        {list.length > VISIBLE_NUDGES && <button className="btn sm muted" onClick={() => setAll(!all)}>{all ? "Show fewer" : `Show ${list.length - VISIBLE_NUDGES} more`}</button>}
      </section>

      <div className="grid g2 stack">
        <section className="card"><h2>Where it went - {monthName(cur.month)}</h2><Donut data={cats} /></section>
        <section className="card"><h2>Income vs spending</h2><Trend months={months} /></section>
      </div>

      <div className="grid g2 stack">
        <section className="card">
          <h2>Budgets this month</h2>
          {Object.keys(budgets).length === 0 && <p className="mute">No budgets yet - set them in Plan or ask the coach.</p>}
          {Object.entries(budgets).map(([c, b]) => {
            const sp = cur.by_cat[c] || 0, pct = (sp / b) * 100;
            return (
              <div key={c} style={{ marginBottom: 12 }}>
                <div className="row small"><b style={{ flex: 1 }}>{c}</b><span>{inr(sp)} / {inr(b)}</span></div>
                <Progress pct={pct} tone={pct > 100 ? "bad" : pct > 85 ? "warn" : undefined} label={`${c} budget used`} />
              </div>
            );
          })}
        </section>
        <section className="card">
          <h2>Goals</h2>
          {snap.goals.items.map((g) => (
            <div key={g.id} style={{ marginBottom: 12 }}>
              <div className="row small"><b style={{ flex: 1 }}>{g.name}</b>
                <span className={"badge " + (g.on_track ? "good" : "warn")}>{g.on_track ? "On track" : "Behind"}</span></div>
              <Progress pct={g.pct} tone={g.on_track ? "good" : "warn"} label={`${g.name} progress`} />
              <div className="small mute">{inr(g.saved)} of {inr(g.target)}</div>
            </div>
          ))}
        </section>
      </div>
    </>
  );
}
