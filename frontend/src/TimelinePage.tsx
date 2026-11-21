import { useEffect, useState } from "react";
import { api, dateFmt } from "./api";
import { Ctx } from "./parts";

const ICON: Record<string, [string, string]> = {
  income: ["+", "#3d8b5a"], goal: ["★", "#2d7d76"], emergency: ["♥", "#b8443c"], budget: ["◎", "#c9772b"],
  subscription: ["↻", "#8a7fc9"], price: ["↑", "#c9772b"], cancelled: ["×", "#7a8794"], rule: ["✓", "#2d7d76"],
  import: ["↓", "#5b8fd1"],
};

export default function TimelinePage({ summary }: Ctx) {
  const [items, setItems] = useState<any[]>([]);
  const [filter, setFilter] = useState("all");
  useEffect(() => { api("/timeline").then(setItems).catch(() => {}); }, [summary]);
  const shown = items.filter((e) => filter === "all" || (filter === "you" ? e.source === "logged" : e.source === "detected"));
  return (
    <div className="card">
      <div className="row" style={{ marginBottom: 6 }}>
        <h2 style={{ marginBottom: 0, flex: 1 }}>Your living money model</h2>
        <select value={filter} onChange={(e) => setFilter(e.target.value)}>
          <option value="all">Everything</option><option value="you">Changes you made</option><option value="det">Detected from data</option>
        </select>
      </div>
      <p className="small mute" style={{ marginTop: 0 }}>How your profile, goals and recurring payments evolved, and why. Detected events come straight from your statements.</p>
      <div className="tl">
        {shown.map((e, i) => {
          const [ic, col] = ICON[e.kind] || ["•", "#66767b"];
          return (
            <div className="tl-item" key={i}>
              <div className="tl-dot" style={{ background: col }}>{ic}</div>
              <div className="tl-body">
                <div className="row small"><span className="mute">{dateFmt(e.date)}</span>
                  <span className={"badge " + (e.source === "detected" ? "info" : "")}>{e.source === "detected" ? "detected" : "you / coach"}</span></div>
                <b>{e.title}</b>
                {e.detail && <div className="small mute">{e.detail}</div>}
                {e.why && <div className="small why">Why: {e.why}</div>}
              </div>
            </div>
          );
        })}
        {shown.length === 0 && <p className="mute">Nothing yet.</p>}
      </div>
    </div>
  );
}
