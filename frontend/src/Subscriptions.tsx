import { api, dateFmt, errMsg, inr } from "./api";
import { type Ctx, Empty, ErrorBox, Loading, useApi } from "./parts";
import type { Subscription, SubscriptionsResponse } from "./types";

const ALERT_LABEL: Record<string, string> = { price_change: "Price change", unused: "Seems unused", overlap: "Overlap", cancelled: "Cancelled" };
const ALERT_TONE: Record<string, string> = { price_change: "warn", unused: "alert", overlap: "info" };

export default function Subscriptions({ summary, toast, refresh }: Ctx) {
  const { data: d, error, loading, reload } = useApi<SubscriptionsResponse>("/subscriptions", summary);
  if (loading && !d) return <Loading what="Finding recurring payments" />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;
  if (!d) return null;
  const groups: [string, Subscription[]][] = [
    ["Subscriptions", d.items.filter((s) => s.kind === "subscription")],
    ["Bills & EMIs", d.items.filter((s) => s.kind === "bill")],
    ["Recurring investments", d.items.filter((s) => s.kind === "saving")],
  ];
  const used = async (m: string) => {
    try {
      await api(`/subscriptions/${encodeURIComponent(m)}/used`, { method: "PUT", body: {} });
      toast("Marked as used today.");
      reload();
      await refresh();
    } catch (e) { toast(errMsg(e)); }
  };

  return (
    <>
      <section className="card">
        <h2>Recurring payments we found</h2>
        <p style={{ margin: 0 }}>Subscriptions cost you <b>{inr(d.monthly_total)}/month</b> ({inr(d.monthly_total * 12)}/year). Detection is deterministic: same merchant, regular gaps, similar amounts, plus UPI AutoPay mandates.</p>
      </section>
      {d.items.length === 0 && <Empty title="No recurring payments yet">Import at least three months of statements to detect them.</Empty>}

      {d.mandates.length > 0 && (
        <section className="card">
          <h2>Upcoming UPI AutoPay mandates</h2>
          <p className="small mute" style={{ marginTop: -6 }}>Read from your bank SMS notices.</p>
          {d.mandates.map((m) => (
            <div key={m.merchant} className={"nudge " + (m.changed ? "warn" : "info")}>
              <div className="row"><b style={{ flex: 1, textTransform: "capitalize" }}>{m.name}</b>
                <span><b>{inr(m.amount)}</b> on {dateFmt(m.date)}</span></div>
              {m.changed
                ? <div className="small">Up from {inr(m.current_amount)}. Review or revoke this mandate in your UPI app before it debits.</div>
                : <div className="small mute">Same as your last charge.</div>}
            </div>
          ))}
        </section>
      )}

      {groups.map(([title, items]) => items.length > 0 && (
        <section className="card" key={title}>
          <h2>{title}</h2>
          {items.map((s) => (
            <div key={s.merchant} className="sub-row">
              <div className="row">
                <b style={{ flex: 1, textTransform: "capitalize" }}>{s.merchant} {s.autopay && <span className="badge info">UPI AutoPay</span>}</b>
                <span><b>{inr(s.amount)}</b> <span className="mute small">/ {s.cadence.replace("ly", "")}{s.fixed_amount ? "" : " (varies)"}</span></span>
              </div>
              <div className="small mute">Seen {s.count}x since {dateFmt(s.first_date)} &middot; next around {dateFmt(s.next_date)}
                {s.last_used && <> &middot; last used {dateFmt(s.last_used)}</>}</div>
              {s.alerts.filter((a) => a.type !== "upcoming").map((a, i) => (
                <div key={i} className={"nudge " + a.severity} style={{ marginTop: 8, marginBottom: 0 }}>
                  <span className={"badge " + (ALERT_TONE[a.type] || "info")}>{ALERT_LABEL[a.type] || a.type}</span>
                  <div className="small" style={{ marginTop: 4 }}>{a.message}</div>
                </div>
              ))}
              {s.kind === "subscription" && <button className="btn sm muted" style={{ marginTop: 8 }} onClick={() => used(s.merchant)}>I used it recently</button>}
            </div>
          ))}
        </section>
      ))}
    </>
  );
}
