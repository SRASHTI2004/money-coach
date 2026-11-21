import { useCallback, useEffect, useRef, useState } from "react";
import { api, errMsg, inr } from "./api";
import { EfChart, GoalLanes } from "./LifeCharts";
import { type Ctx, ErrorBox, Md } from "./parts";
import type { LifeEventInput as Ev, LifeSim, Narration } from "./types";

type EventType = Ev["type"];

const DEFAULTS: Record<EventType, Ev> = {
  salary_change: { type: "salary_change", start: 2, percent: 15 },
  job_loss: { type: "job_loss", start: 2, months: 3, cut_pct: 30 },
  rent_increase: { type: "rent_increase", start: 2, amount: 4000 },
  new_emi: { type: "new_emi", start: 2, amount: 8000, months: 36 },
};
const TITLES: Record<EventType, string> = {
  salary_change: "Salary change", job_loss: "Job loss", rent_increase: "Rent increase", new_emi: "New EMI",
};
const PRESETS: { label: string; ev: Ev[] }[] = [
  { label: "Salary hike 15%", ev: [{ ...DEFAULTS.salary_change }] },
  { label: "Job loss for 3 months", ev: [{ ...DEFAULTS.job_loss }] },
  { label: "Job loss + new EMI", ev: [{ ...DEFAULTS.job_loss }, { ...DEFAULTS.new_emi, start: 5 }] },
  { label: "Rent up + salary hike", ev: [{ ...DEFAULTS.rent_increase, amount: 6000 }, { ...DEFAULTS.salary_change, start: 4, percent: 20 }] },
];
const VIEW_OPTIONS = [24, 36, 48];
const DEFAULT_VIEW = 36;
const num = (v: string): number => (v === "" ? 0 : Number(v));

export default function LifeEvents({ summary }: Ctx) {
  const [evs, setEvs] = useState<Ev[]>(PRESETS[1].ev);
  const [sim, setSim] = useState<LifeSim | null>(null);
  const [nar, setNar] = useState<Narration | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [view, setView] = useState(DEFAULT_VIEW);
  const seq = useRef(0);

  const run = useCallback(async (list: Ev[]) => {
    const my = ++seq.current;
    setBusy(true);
    setNar(null);
    setError("");
    try {
      const r = await api<LifeSim>("/life-events", { body: { events: list } });
      if (my !== seq.current) return;
      setSim(r);
      api<Narration>("/life-events/narrate", { body: { events: list } })
        .then((n) => { if (my === seq.current) setNar(n); })
        .catch(() => { if (my === seq.current) setNar({ text: r.summary, ai: false }); });
    } catch (e) { setError(errMsg(e)); } finally { setBusy(false); }
  }, []);
  useEffect(() => {
    let live = true;
    api<LifeSim>("/life-events", { body: { events: PRESETS[1].ev } })
      .then((r) => {
        if (!live) return;
        setSim(r);
        api<Narration>("/life-events/narrate", { body: { events: PRESETS[1].ev } })
          .then((n) => { if (live) setNar(n); })
          .catch(() => { if (live) setNar({ text: r.summary, ai: false }); });
      })
      .catch((e) => { if (live) setError(errMsg(e)); });
    return () => { live = false; };
  }, [summary]);
  const upd = (i: number, p: Partial<Ev>) => setEvs(evs.map((e, j) => (j === i ? { ...e, ...p } : e)));

  return (
    <>
      <section className="card" aria-labelledby="le-h">
        <h2 id="le-h">Life event simulator</h2>
        <p className="small mute" style={{ marginTop: -6 }}>Stack real-life changes and see month by month what happens to your emergency fund and every goal. The maths is deterministic; Gemini only explains the result.</p>
        <div className="chips" role="group" aria-label="Scenario presets">{PRESETS.map((p) => <button key={p.label} className="chip" onClick={() => { setEvs(p.ev); run(p.ev); }}>{p.label}</button>)}</div>
        {evs.map((e, i) => (
          <div key={i} className="event-row">
            <b>{TITLES[e.type]}</b>
            <label className="f">Starts in (months)<input type="number" min={1} max={48} value={e.start} onChange={(ev) => upd(i, { start: num(ev.target.value) })} /></label>
            {e.type === "salary_change" && <label className="f">Change %<input type="number" value={e.percent ?? 0} onChange={(ev) => upd(i, { percent: num(ev.target.value) })} /></label>}
            {e.type === "job_loss" && <>
              <label className="f">For (months)<input type="number" min={1} value={e.months ?? 1} onChange={(ev) => upd(i, { months: num(ev.target.value) })} /></label>
              <label className="f">Cut spending %<input type="number" min={0} max={100} value={e.cut_pct ?? 0} onChange={(ev) => upd(i, { cut_pct: num(ev.target.value) })} /></label></>}
            {(e.type === "rent_increase" || e.type === "new_emi") && <label className="f">&#8377; per month<input type="number" min={0} value={e.amount ?? 0} onChange={(ev) => upd(i, { amount: num(ev.target.value) })} /></label>}
            {e.type === "new_emi" && <label className="f">Tenure (months)<input type="number" min={1} value={e.months ?? 1} onChange={(ev) => upd(i, { months: num(ev.target.value) })} /></label>}
            <button className="btn sm muted" onClick={() => setEvs(evs.filter((_, j) => j !== i))} aria-label={`Remove ${TITLES[e.type]}`}>&times;</button>
          </div>
        ))}
        <div className="row" style={{ marginTop: 10 }}>
          <select aria-label="Add a life event" value="" onChange={(e) => e.target.value && setEvs([...evs, { ...DEFAULTS[e.target.value as EventType] }])}>
            <option value="">+ Add life event...</option>
            {(Object.keys(TITLES) as EventType[]).map((k) => <option key={k} value={k}>{TITLES[k]}</option>)}
          </select>
          <button className="btn" disabled={busy} onClick={() => run(evs)}>{busy ? "Calculating..." : "Run scenario"}</button>
        </div>
      </section>

      {error && <ErrorBox message={error} onRetry={() => run(evs)} />}
      {sim && (
        <>
          <section className="card" aria-labelledby="le-r" aria-live="polite">
            <h2 id="le-r">What it does</h2>
            <div className="grid g3" style={{ marginBottom: 14 }}>
              <div className="stat"><div className="l">Emergency fund low point</div><div className="v" style={{ color: sim.after.ef_depleted_month ? "var(--bad)" : undefined }}>{inr(sim.after.ef_low)}</div><div className="s">{sim.ef_runway_low_months} months of essentials{sim.after.ef_depleted_month ? ` - runs out in month ${sim.after.ef_depleted_month}` : ""}</div></div>
              <div className="stat"><div className="l">Without the event</div><div className="v">{inr(sim.before.ef_low)}</div><div className="s">lowest point of the fund</div></div>
              <div className="stat"><div className="l">Goals off track</div><div className="v">{sim.goals.filter((g) => !g.after_on_track).length} / {sim.goals.length}</div><div className="s">was {sim.goals.filter((g) => !g.before_on_track).length}</div></div>
            </div>
            <p style={{ margin: "0 0 8px" }}>{sim.summary}</p>
            <div className="ai-note">
              <span className={"badge " + (nar?.ai ? "" : "off")}>{nar ? (nar.ai ? "Gemini explains" : "Summary") : "Gemini is explaining..."}</span>
              <div className="small" style={{ marginTop: 6 }}>{nar ? <Md text={nar.text} /> : "..."}</div>
            </div>
          </section>
          <section className="card" aria-labelledby="le-ef">
            <div className="row" style={{ marginBottom: 6 }}>
              <h2 id="le-ef" style={{ marginBottom: 0, flex: 1 }}>Emergency fund, month by month</h2>
              <select aria-label="Chart range" value={view} onChange={(e) => setView(Number(e.target.value))}>{VIEW_OPTIONS.map((v) => <option key={v} value={v}>{v / 12} years</option>)}</select>
            </div>
            <EfChart sim={sim} view={view} />
            <div className="legend small mute"><span><i style={{ background: "#8d9a93" }} />without the event</span><span><i style={{ background: "#2d7d76" }} />with the event</span><span><i style={{ background: "#b8443c", borderRadius: 5 }} />lowest point</span></div>
          </section>
          <section className="card"><h2>Goal dates: before &rarr; after</h2><GoalLanes sim={sim} view={view} /></section>
        </>
      )}
    </>
  );
}
