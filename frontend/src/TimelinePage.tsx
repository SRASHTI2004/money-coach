import { useState } from "react";
import { dateFmt } from "./api";
import { type Ctx, Empty, ErrorBox, Loading, useApi } from "./parts";
import type { TimelineEvent } from "./types";

const ICON: Record<string, [string, string]> = {
  income: ["+", "#2f7a4d"], goal: ["★", "#2d7d76"], emergency: ["♥", "#b8443c"], budget: ["◎", "#a85f14"],
  subscription: ["↻", "#6f63b3"], price: ["↑", "#a85f14"], cancelled: ["×", "#66767b"], rule: ["✓", "#2d7d76"],
  import: ["↓", "#3f78bf"],
};
const FALLBACK_ICON: [string, string] = ["•", "#66767b"];

export default function TimelinePage({ summary }: Ctx) {
  const { data, error, loading, reload } = useApi<TimelineEvent[]>("/timeline", summary);
  const [filter, setFilter] = useState("all");
  if (loading && !data) return <Loading what="Building your timeline" />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;
  const shown = (data ?? []).filter((e) => filter === "all" || (filter === "you" ? e.source === "logged" : e.source === "detected"));
  return (
    <section className="card" aria-labelledby="tl-h">
      <div className="row" style={{ marginBottom: 6 }}>
        <h2 id="tl-h" style={{ marginBottom: 0, flex: 1 }}>Your living money model</h2>
        <select aria-label="Filter timeline" value={filter} onChange={(e) => setFilter(e.target.value)}>
          <option value="all">Everything</option><option value="you">Changes you made</option><option value="det">Detected from data</option>
        </select>
      </div>
      <p className="small mute" style={{ marginTop: 0 }}>How your profile, goals and recurring payments evolved, and why. Detected events come straight from your statements.</p>
      <ol className="tl">
        {shown.map((e, i) => {
          const [ic, col] = ICON[e.kind] || FALLBACK_ICON;
          return (
            <li className="tl-item" key={i}>
              <div className="tl-dot" style={{ background: col }} aria-hidden="true">{ic}</div>
              <div className="tl-body">
                <div className="row small"><span className="mute">{dateFmt(e.date)}</span>
                  <span className={"badge " + (e.source === "detected" ? "info" : "")}>{e.source === "detected" ? "detected" : "you / coach"}</span></div>
                <b>{e.title}</b>
                {e.detail && <div className="small mute">{e.detail}</div>}
                {e.why && <div className="small why">Why: {e.why}</div>}
              </div>
            </li>
          );
        })}
      </ol>
      {shown.length === 0 && <Empty title="Nothing here yet">Changes to your profile, goals and subscriptions will appear here with the reason.</Empty>}
    </section>
  );
}
