import { useEffect, useState } from "react";
import { api, inr, inrShort, monthName } from "./api";
import { Ctx, Donut, Progress, Sev, Trend } from "./parts";

export default function Dashboard({ summary: s, toast, goTab }: Ctx) {
  const [nudges, setNudges] = useState<any[]>([]);
  const [open, setOpen] = useState<Record<string, any>>({});
  const [all, setAll] = useState(false);
  useEffect(() => { api("/nudges").then(setNudges).catch(() => {}); }, [s]);

  const explain = async (id: string) => {
    setOpen((o) => ({ ...o, [id]: { loading: true } }));
    try { const r = await api("/nudges/explain?id=" + encodeURIComponent(id)); setOpen((o) => ({ ...o, [id]: r })); }
    catch (e: any) { toast(e.message); }
  };

  const months = s.months as any[];
  const cur = months[months.length - 1];
  const snap = s.snapshot;
  const budgets = s.profile.budgets as Record<string, number>;
  const cats = Object.entries(cur.by_cat as Record<string, number>).filter(([, v]) => v > 0)
    .map(([label, value]) => ({ label, value })).sort((a, b) => b.value - a.value);
  const urgent = nudges.filter((n) => n.severity !== "info").length;
  const shown = all ? nudges : nudges.slice(0, 3);
  const onTrack = snap.goals.items.filter((g: any) => g.on_track).length;

  return (
    <>
      <div className="card hero-card">
        <div className="l">Free cash each month</div>
        <div className="big-num">{inr(snap.free_cash)}</div>
        <div className="small" style={{ opacity: 0.85 }}>
          After {inr(snap.spend)} of spending{snap.invested ? ` and ${inr(snap.invested)} of SIPs` : ""}, from {inr(snap.income)} income.
          Your plan sets aside {inr(snap.goals.planned_total)} for goals.
        </div>
        <div className="row" style={{ marginTop: 12 }}>
          <span className={"pill " + (urgent ? "warn" : "good")}>{urgent ? `${urgent} thing${urgent > 1 ? "s" : ""} need attention` : "All on plan"}</span>
          <span className="pill">{onTrack}/{snap.goals.items.filter((g: any) => g.kind === "goal").length || snap.goals.items.length} goals on track</span>
          <span className="pill">as of {s.as_of}</span>
        </div>
      </div>

      <div className="grid g3" style={{ marginBottom: 16 }}>
        <div className="stat"><div className="l">Spent in {monthName(cur.month)}</div><div className="v">{inr(cur.spend)}</div><div className="s">{inrShort(cur.spend)} so far</div></div>
        <div className="stat"><div className="l">Income / month</div><div className="v">{inr(snap.income)}</div><div className="s">{s.profile.monthly_income ? "from your profile" : "estimated"}</div></div>
        <div className="stat"><div className="l">Emergency fund</div><div className="v">{snap.emergency_months ?? "-"} mo</div><div className="s">{inr(s.profile.emergency_fund)} saved &middot; target {s.profile.emergency_target_months} mo</div></div>
      </div>

      <div className="card">
        <h2>Nudges {nudges.length > 0 && <span className="badge info">{nudges.length}</span>}</h2>
        {nudges.length === 0 && <p className="mute">All on plan - nothing needs your attention.</p>}
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
              <div className="small ai-note" style={{ marginTop: 8 }}>
                {open[n.id].loading ? "Thinking..." : <>
                  {open[n.id].explanation}
                  <div className="mute" style={{ marginTop: 4 }}>{open[n.id].ai ? "Explained by Gemini from your numbers" : "Built-in explanation"}</div>
                </>}
              </div>
            )}
          </div>
        ))}
        {nudges.length > 3 && <button className="btn sm muted" onClick={() => setAll(!all)}>{all ? "Show fewer" : `Show ${nudges.length - 3} more`}</button>}
      </div>

      <div className="grid g2 stack">
        <div className="card"><h2>Where it went - {monthName(cur.month)}</h2><Donut data={cats} /></div>
        <div className="card"><h2>Income vs spending</h2><Trend months={months} /></div>
      </div>

      <div className="grid g2 stack">
        <div className="card">
          <h2>Budgets this month</h2>
          {Object.keys(budgets).length === 0 && <p className="mute">No budgets yet - set them in Plan or ask the coach.</p>}
          {Object.entries(budgets).map(([c, b]) => {
            const sp = cur.by_cat[c] || 0, pct = (sp / b) * 100;
            return (
              <div key={c} style={{ marginBottom: 12 }}>
                <div className="row small"><b style={{ flex: 1 }}>{c}</b><span>{inr(sp)} / {inr(b)}</span></div>
                <Progress pct={pct} tone={pct > 100 ? "bad" : pct > 85 ? "warn" : undefined} />
              </div>
            );
          })}
        </div>
        <div className="card">
          <h2>Goals</h2>
          {snap.goals.items.map((g: any) => (
            <div key={g.id} style={{ marginBottom: 12 }}>
              <div className="row small"><b style={{ flex: 1 }}>{g.name}</b>
                <span className={"badge " + (g.on_track ? "good" : "warn")}>{g.on_track ? "On track" : "Behind"}</span></div>
              <Progress pct={g.pct} tone={g.on_track ? "good" : "warn"} />
              <div className="small mute">{inr(g.saved)} of {inr(g.target)}</div>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
