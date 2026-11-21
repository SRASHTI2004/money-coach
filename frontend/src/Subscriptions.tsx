import { useEffect, useState } from "react";
import { api, dateFmt, inr } from "./api";
import { Ctx } from "./parts";

export default function Subscriptions({ summary, toast, refresh }: Ctx) {
  const [d, setD] = useState<any>(null);
  const load = () => api("/subscriptions").then(setD);
  useEffect(() => { load().catch(() => {}); }, [summary]);
  if (!d) return <p className="mute">Loading...</p>;
  const groups = [
    ["Subscriptions", d.items.filter((s: any) => s.kind === "subscription")],
    ["Bills & EMIs", d.items.filter((s: any) => s.kind === "bill")],
    ["Recurring investments", d.items.filter((s: any) => s.kind === "saving")],
  ] as [string, any[]][];
  const used = async (m: string) => { await api(`/subscriptions/${m}/used`, { method: "PUT", body: {} }); toast("Marked as used today."); load(); refresh(); };

  return (
    <>
      <div className="card">
        <h2>Recurring payments we found</h2>
        <p style={{ margin: 0 }}>Subscriptions cost you <b>{inr(d.monthly_total)}/month</b> ({inr(d.monthly_total * 12)}/year). Detection is deterministic: same merchant, regular gaps, similar amounts.</p>
      </div>
      {groups.map(([title, items]) => items.length > 0 && (
        <div className="card" key={title}>
          <h2>{title}</h2>
          {items.map((s) => (
            <div key={s.merchant} style={{ padding: "10px 0", borderBottom: "1px solid var(--line)" }}>
              <div className="row">
                <b style={{ flex: 1, textTransform: "capitalize" }}>{s.merchant}</b>
                <span><b>{inr(s.amount)}</b> <span className="mute small">/ {s.cadence.replace("ly", "")}{s.fixed_amount ? "" : " (varies)"}</span></span>
              </div>
              <div className="small mute">Seen {s.count}x since {dateFmt(s.first_date)} - next around {dateFmt(s.next_date)}
                {s.last_used && <> - last used {dateFmt(s.last_used)}</>}</div>
              {s.alerts.filter((a: any) => a.type !== "upcoming").map((a: any, i: number) => (
                <div key={i} className={"nudge " + a.severity} style={{ marginTop: 8, marginBottom: 0 }}>
                  <span className={"badge " + (a.type === "price_change" ? "warn" : a.type === "unused" ? "alert" : "info")}>
                    {a.type === "price_change" ? "Price change" : a.type === "unused" ? "Seems unused" : "Overlap"}</span>
                  <div className="small" style={{ marginTop: 4 }}>{a.message}</div>
                </div>
              ))}
              {s.kind === "subscription" && <button className="btn sm muted" style={{ marginTop: 8 }} onClick={() => used(s.merchant)}>I used it recently</button>}
            </div>
          ))}
        </div>
      ))}
    </>
  );
}
