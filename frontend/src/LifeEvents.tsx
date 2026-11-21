import { useEffect, useRef, useState } from "react";
import { api, dateFmt, inr, inrShort, monthName } from "./api";
import { Ctx } from "./parts";

type Ev = { type: string; start: number; percent?: number; months?: number; amount?: number; cut_pct?: number };

const DEFAULTS: Record<string, Ev> = {
  salary_change: { type: "salary_change", start: 2, percent: 15 },
  job_loss: { type: "job_loss", start: 2, months: 3, cut_pct: 30 },
  rent_increase: { type: "rent_increase", start: 2, amount: 4000 },
  new_emi: { type: "new_emi", start: 2, amount: 8000, months: 36 },
};
const TITLES: Record<string, string> = {
  salary_change: "Salary change", job_loss: "Job loss", rent_increase: "Rent increase", new_emi: "New EMI",
};
const PRESETS: { label: string; ev: Ev[] }[] = [
  { label: "Salary hike 15%", ev: [{ ...DEFAULTS.salary_change }] },
  { label: "Job loss for 3 months", ev: [{ ...DEFAULTS.job_loss }] },
  { label: "Job loss + new EMI", ev: [{ ...DEFAULTS.job_loss, start: 2 }, { ...DEFAULTS.new_emi, start: 5 }] },
  { label: "Rent up + salary hike", ev: [{ ...DEFAULTS.rent_increase, amount: 6000 }, { ...DEFAULTS.salary_change, start: 4, percent: 20 }] },
];

const monthsFrom = (asOf: string, d: string | null) => {
  if (!d) return null;
  const a = new Date(asOf + "T00:00:00"), b = new Date(d + "T00:00:00");
  return (b.getFullYear() - a.getFullYear()) * 12 + (b.getMonth() - a.getMonth());
};

function EfChart({ sim, view }: { sim: any; view: number }) {
  const W = 640, H = 230, L = 52, R = 12, T = 14, B = 30;
  const b = sim.before.ef.slice(0, view + 1), a = sim.after.ef.slice(0, view + 1);
  const target = sim.after.ef_target;
  const max = Math.max(...b, ...a, target, 1) * 1.08;
  const x = (i: number) => L + (i / view) * (W - L - R);
  const y = (v: number) => T + (1 - v / max) * (H - T - B);
  const path = (arr: number[]) => arr.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  const ticks = [0, 0.5, 1].map((f) => f * max / 1.08);
  const xt = Array.from({ length: Math.floor(view / 6) + 1 }, (_, i) => i * 6);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="Emergency fund before and after">
      {ticks.map((t) => <g key={t}><line x1={L} x2={W - R} y1={y(t)} y2={y(t)} stroke="#e3e7e2" /><text x={L - 6} y={y(t) + 4} textAnchor="end" fontSize="11" fill="#66767b">{inrShort(t)}</text></g>)}
      {xt.map((i) => <text key={i} x={x(i)} y={H - 10} textAnchor="middle" fontSize="11" fill="#66767b">{i === 0 ? "now" : monthName(sim.labels[i]).split(" ")[0] + " '" + sim.labels[i].slice(2, 4)}</text>)}
      {sim.marks.map((m: any, i: number) => m.month <= view && (
        <g key={i}><line x1={x(m.month)} x2={x(m.month)} y1={T} y2={H - B} stroke="#c9772b" strokeDasharray="3 4" />
          <text x={x(m.month) + 4} y={T + 10 + (i % 3) * 12} fontSize="10.5" fill="#c9772b" fontWeight="600">{m.label}</text></g>
      ))}
      {target > 0 && <g><line x1={L} x2={W - R} y1={y(target)} y2={y(target)} stroke="#3d8b5a" strokeDasharray="5 4" /><text x={W - R} y={y(target) - 4} textAnchor="end" fontSize="10.5" fill="#3d8b5a">target {inrShort(target)}</text></g>}
      <path d={path(b)} fill="none" stroke="#aab4ae" strokeWidth="2.5" strokeDasharray="1 0" />
      <path d={path(a)} fill="none" stroke="#2d7d76" strokeWidth="3" strokeLinejoin="round" />
      <circle cx={x(sim.after.ef_low_month)} cy={y(sim.after.ef_low)} r="5" fill="#b8443c" />
    </svg>
  );
}

function GoalLanes({ sim, view }: { sim: any; view: number }) {
  const asOf = sim.before.as_of;
  const pos = (m: number | null) => (m === null ? null : Math.max(0, Math.min(100, (m / view) * 100)));
  return (
    <div>
      {sim.goals.map((g: any) => {
        const t = pos(monthsFrom(asOf, g.target_date)), bf = pos(monthsFrom(asOf, g.before_date)), af = pos(monthsFrom(asOf, g.after_date));
        const shift = g.shift_months;
        return (
          <div key={g.id} style={{ marginBottom: 18 }}>
            <div className="row small" style={{ marginBottom: 4 }}>
              <b style={{ flex: 1 }}>{g.name}</b>
              <span className={"badge " + (g.after_on_track ? "good" : "alert")}>
                {g.not_in_horizon ? "Beyond 4 years" : g.after_on_track ? "Still on track" : "Misses target"}
              </span>
            </div>
            <div style={{ position: "relative", height: 26, background: "#eef1ec", borderRadius: 13 }}>
              {af !== null && bf !== null && <div style={{ position: "absolute", left: Math.min(af, bf) + "%", width: Math.abs(af - bf) + "%", top: 11, height: 4, background: shift && shift > 0 ? "#e9b9b5" : "#b9dcc6" }} />}
              {t !== null && <div title={"Target " + dateFmt(g.target_date)} style={{ position: "absolute", left: `calc(${t}% - 1px)`, top: 2, bottom: 2, width: 2, background: "#c9772b" }} />}
              {bf !== null && <div title={"Before: " + dateFmt(g.before_date)} style={{ position: "absolute", left: `calc(${bf}% - 7px)`, top: 6, width: 14, height: 14, borderRadius: 7, background: "#aab4ae", border: "2px solid #fff" }} />}
              {af !== null && <div title={"After: " + dateFmt(g.after_date)} style={{ position: "absolute", left: `calc(${af}% - 8px)`, top: 5, width: 16, height: 16, borderRadius: 8, background: g.after_on_track ? "#2d7d76" : "#b8443c", border: "2px solid #fff" }} />}
            </div>
            <div className="small mute" style={{ marginTop: 4 }}>
              Before <b>{dateFmt(g.before_date)}</b> &rarr; after <b>{g.not_in_horizon ? "later than 4 yrs" : dateFmt(g.after_date)}</b>
              {shift ? <> ({shift > 0 ? "+" : ""}{shift} mo)</> : null} &middot; target {dateFmt(g.target_date)}
            </div>
          </div>
        );
      })}
      <div className="legend small mute"><span><i style={{ background: "#aab4ae", borderRadius: 7 }} />before</span><span><i style={{ background: "#2d7d76", borderRadius: 7 }} />after</span><span><i style={{ background: "#c9772b", width: 3 }} />target date</span></div>
    </div>
  );
}

export default function LifeEvents({ summary }: Ctx) {
  const [evs, setEvs] = useState<Ev[]>(PRESETS[1].ev);
  const [sim, setSim] = useState<any>(null);
  const [nar, setNar] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [view, setView] = useState(36);
  const seq = useRef(0);

  const run = async (list: Ev[]) => {
    const my = ++seq.current;
    setBusy(true); setNar(null);
    try {
      const r = await api("/life-events", { body: { events: list } });
      if (my !== seq.current) return;
      setSim(r);
      api("/life-events/narrate", { body: { events: list } }).then((n) => my === seq.current && setNar(n)).catch(() => {});
    } finally { setBusy(false); }
  };
  useEffect(() => { run(PRESETS[1].ev).catch(() => {}); }, [summary]);
  const upd = (i: number, p: Partial<Ev>) => setEvs(evs.map((e, j) => (j === i ? { ...e, ...p } : e)));
  const num = (v: string) => (v === "" ? 0 : Number(v));

  return (
    <>
      <div className="card">
        <h2>Life event simulator</h2>
        <p className="small mute" style={{ marginTop: -6 }}>Stack real-life changes and see month by month what happens to your emergency fund and every goal. The maths is deterministic; Gemini only explains the result.</p>
        <div className="chips">{PRESETS.map((p) => <button key={p.label} className="chip" onClick={() => { setEvs(p.ev); run(p.ev); }}>{p.label}</button>)}</div>
        {evs.map((e, i) => (
          <div key={i} className="event-row">
            <b>{TITLES[e.type]}</b>
            <label className="f">Starts in (months)<input type="number" min={1} value={e.start} onChange={(ev) => upd(i, { start: num(ev.target.value) })} /></label>
            {e.type === "salary_change" && <label className="f">Change %<input type="number" value={e.percent} onChange={(ev) => upd(i, { percent: num(ev.target.value) })} /></label>}
            {e.type === "job_loss" && <>
              <label className="f">For (months)<input type="number" min={1} value={e.months} onChange={(ev) => upd(i, { months: num(ev.target.value) })} /></label>
              <label className="f">Cut spending %<input type="number" value={e.cut_pct} onChange={(ev) => upd(i, { cut_pct: num(ev.target.value) })} /></label></>}
            {(e.type === "rent_increase" || e.type === "new_emi") && <label className="f">&#8377; per month<input type="number" value={e.amount} onChange={(ev) => upd(i, { amount: num(ev.target.value) })} /></label>}
            {e.type === "new_emi" && <label className="f">Tenure (months)<input type="number" value={e.months} onChange={(ev) => upd(i, { months: num(ev.target.value) })} /></label>}
            <button className="btn sm muted" onClick={() => setEvs(evs.filter((_, j) => j !== i))} aria-label="Remove event">&times;</button>
          </div>
        ))}
        <div className="row" style={{ marginTop: 10 }}>
          <select value="" onChange={(e) => e.target.value && setEvs([...evs, { ...DEFAULTS[e.target.value] }])}>
            <option value="">+ Add life event...</option>
            {Object.entries(TITLES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
          <button className="btn" disabled={busy} onClick={() => run(evs)}>{busy ? "Calculating..." : "Run scenario"}</button>
        </div>
      </div>

      {sim && (
        <>
          <div className="card">
            <h2>What it does</h2>
            <div className="grid g3" style={{ marginBottom: 14 }}>
              <div className="stat"><div className="l">Emergency fund low point</div><div className="v" style={{ color: sim.after.ef_depleted_month ? "var(--bad)" : undefined }}>{inr(sim.after.ef_low)}</div><div className="s">{sim.ef_runway_low_months} months of essentials{sim.after.ef_depleted_month ? ` - runs out in month ${sim.after.ef_depleted_month}` : ""}</div></div>
              <div className="stat"><div className="l">Without the event</div><div className="v">{inr(sim.before.ef_low)}</div><div className="s">lowest point of the fund</div></div>
              <div className="stat"><div className="l">Goals off track</div><div className="v">{sim.goals.filter((g: any) => !g.after_on_track).length} / {sim.goals.length}</div><div className="s">was {sim.goals.filter((g: any) => !g.before_on_track).length}</div></div>
            </div>
            <p style={{ margin: "0 0 8px" }}>{sim.summary}</p>
            <div className="ai-note">
              <span className={"badge " + (nar?.ai ? "" : "off")}>{nar ? (nar.ai ? "Gemini explains" : "Summary") : "Gemini is explaining..."}</span>
              <div className="small" style={{ marginTop: 6 }}>{nar ? nar.text : "..."}</div>
            </div>
          </div>
          <div className="card">
            <div className="row" style={{ marginBottom: 6 }}>
              <h2 style={{ marginBottom: 0, flex: 1 }}>Emergency fund, month by month</h2>
              <select value={view} onChange={(e) => setView(Number(e.target.value))}><option value={24}>2 years</option><option value={36}>3 years</option><option value={48}>4 years</option></select>
            </div>
            <EfChart sim={sim} view={view} />
            <div className="legend small mute"><span><i style={{ background: "#aab4ae" }} />without the event</span><span><i style={{ background: "#2d7d76" }} />with the event</span><span><i style={{ background: "#b8443c", borderRadius: 5 }} />lowest point</span></div>
          </div>
          <div className="card"><h2>Goal dates: before &rarr; after</h2><GoalLanes sim={sim} view={view} /></div>
        </>
      )}
    </>
  );
}
