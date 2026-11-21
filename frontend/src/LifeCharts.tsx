import { dateFmt, inr, inrShort, monthName } from "./api";
import type { LifeSim } from "./types";

const W = 640, H = 230, PAD_L = 52, PAD_R = 12, PAD_T = 14, PAD_B = 30;
const MONTHS_PER_TICK = 6;

const monthsFrom = (asOf: string, d: string | null): number | null => {
  if (!d) return null;
  const a = new Date(asOf + "T00:00:00"), b = new Date(d + "T00:00:00");
  return (b.getFullYear() - a.getFullYear()) * 12 + (b.getMonth() - a.getMonth());
};

/** Emergency fund balance by month: without the event (grey) vs with it (teal), marking the lowest point. */
export function EfChart({ sim, view }: { sim: LifeSim; view: number }) {
  const b = sim.before.ef.slice(0, view + 1), a = sim.after.ef.slice(0, view + 1);
  const target = sim.after.ef_target;
  const top = Math.max(...b, ...a, target, 1);
  const max = top * 1.08;
  const x = (i: number) => PAD_L + (i / view) * (W - PAD_L - PAD_R);
  const y = (v: number) => PAD_T + (1 - v / max) * (H - PAD_T - PAD_B);
  const path = (arr: number[]) => arr.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  const ticks = [0, 0.5, 1].map((f) => f * top);
  const xt = Array.from({ length: Math.floor(view / MONTHS_PER_TICK) + 1 }, (_, i) => i * MONTHS_PER_TICK);
  const low = sim.after.ef_low;
  const label = `Emergency fund by month. Lowest point ${inr(low)} in month ${sim.after.ef_low_month}` +
    (sim.after.ef_depleted_month ? `, running out in month ${sim.after.ef_depleted_month}` : "") + `. Without the event it never drops below ${inr(sim.before.ef_low)}.`;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label={label}>
      {ticks.map((t) => <g key={t}><line x1={PAD_L} x2={W - PAD_R} y1={y(t)} y2={y(t)} stroke="#e3e7e2" /><text x={PAD_L - 6} y={y(t) + 4} textAnchor="end" fontSize="11" fill="#566468">{inrShort(t)}</text></g>)}
      {xt.map((i) => <text key={i} x={x(i)} y={H - 10} textAnchor="middle" fontSize="11" fill="#566468">{i === 0 ? "now" : monthName(sim.labels[i]).split(" ")[0] + " '" + sim.labels[i].slice(2, 4)}</text>)}
      {sim.marks.map((m, i) => m.month <= view && (
        <g key={i}><line x1={x(m.month)} x2={x(m.month)} y1={PAD_T} y2={H - PAD_B} stroke="#a85f14" strokeDasharray="3 4" />
          <text x={x(m.month) + 4} y={PAD_T + 10 + (i % 3) * 12} fontSize="10.5" fill="#8a4d12" fontWeight="600">{m.label}</text></g>
      ))}
      {target > 0 && <g><line x1={PAD_L} x2={W - PAD_R} y1={y(target)} y2={y(target)} stroke="#2f7a4d" strokeDasharray="5 4" /><text x={W - PAD_R} y={y(target) - 4} textAnchor="end" fontSize="10.5" fill="#2f7a4d">target {inrShort(target)}</text></g>}
      <path d={path(b)} fill="none" stroke="#8d9a93" strokeWidth="2.5" />
      <path d={path(a)} fill="none" stroke="#2d7d76" strokeWidth="3" strokeLinejoin="round" />
      <circle cx={x(sim.after.ef_low_month)} cy={y(low)} r="5" fill="#b8443c" />
    </svg>
  );
}

/** One lane per goal: before date (grey), after date (teal/red), target date (orange tick). */
export function GoalLanes({ sim, view }: { sim: LifeSim; view: number }) {
  const asOf = sim.before.as_of;
  const pos = (m: number | null) => (m === null ? null : Math.max(0, Math.min(100, (m / view) * 100)));
  return (
    <div>
      {sim.goals.map((g) => {
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
            <div className="lane" role="img" aria-label={`${g.name}: before ${dateFmt(g.before_date)}, after ${g.not_in_horizon ? "later than 4 years" : dateFmt(g.after_date)}, target ${dateFmt(g.target_date)}`}>
              {af !== null && bf !== null && <div className="lane-span" style={{ left: Math.min(af, bf) + "%", width: Math.abs(af - bf) + "%", background: shift && shift > 0 ? "#e9b9b5" : "#b9dcc6" }} />}
              {t !== null && <div className="lane-target" title={"Target " + dateFmt(g.target_date)} style={{ left: `calc(${t}% - 1px)` }} />}
              {bf !== null && <div className="lane-dot before" title={"Before: " + dateFmt(g.before_date)} style={{ left: `calc(${bf}% - 7px)` }} />}
              {af !== null && <div className={"lane-dot " + (g.after_on_track ? "ok" : "bad")} title={"After: " + dateFmt(g.after_date)} style={{ left: `calc(${af}% - 8px)` }} />}
            </div>
            <div className="small mute" style={{ marginTop: 4 }}>
              Before <b>{dateFmt(g.before_date)}</b> &rarr; after <b>{g.not_in_horizon ? "later than 4 yrs" : dateFmt(g.after_date)}</b>
              {shift ? <> ({shift > 0 ? "+" : ""}{shift} mo)</> : null} &middot; target {dateFmt(g.target_date)}
            </div>
          </div>
        );
      })}
      <div className="legend small mute"><span><i style={{ background: "#8d9a93", borderRadius: 7 }} />before</span><span><i style={{ background: "#2d7d76", borderRadius: 7 }} />after</span><span><i style={{ background: "#c9772b", width: 3 }} />target date</span></div>
    </div>
  );
}
