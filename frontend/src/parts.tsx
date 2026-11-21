import { CAT_COLORS, inr, monthName } from "./api";

export type Ctx = { refresh: () => Promise<void>; toast: (m: string) => void; summary: any; goTab: (t: string) => void };

export function Md({ text }: { text: string }) {
  const bold = (s: string) =>
    s.split(/(\*\*[^*]+\*\*)/g).map((p, i) => (p.startsWith("**") ? <b key={i}>{p.slice(2, -2)}</b> : <span key={i}>{p}</span>));
  const blocks = text.split(/\n{2,}/);
  return (
    <div className="md">
      {blocks.map((b, i) => {
        const lines = b.split("\n");
        if (lines.every((l) => /^\s*[-*] /.test(l)))
          return <ul key={i}>{lines.map((l, j) => <li key={j}>{bold(l.replace(/^\s*[-*] /, ""))}</li>)}</ul>;
        return <p key={i}>{lines.map((l, j) => <span key={j}>{bold(l)}{j < lines.length - 1 && <br />}</span>)}</p>;
      })}
    </div>
  );
}

export function Donut({ data }: { data: { label: string; value: number }[] }) {
  const total = data.reduce((a, b) => a + b.value, 0) || 1;
  const R = 52, C = 2 * Math.PI * R;
  let off = 0;
  return (
    <div className="row" style={{ alignItems: "center", gap: 20 }}>
      <svg width="150" height="150" viewBox="0 0 150 150" role="img" aria-label="Spending by category">
        <g transform="rotate(-90 75 75)">
          {data.map((d) => {
            const len = (d.value / total) * C;
            const el = (
              <circle key={d.label} cx="75" cy="75" r={R} fill="none" stroke={CAT_COLORS[d.label] || "#bbb"} strokeWidth="22"
                strokeDasharray={`${len} ${C - len}`} strokeDashoffset={-off} />
            );
            off += len;
            return el;
          })}
        </g>
        <text x="75" y="72" textAnchor="middle" fontSize="11" fill="#66767b">Spent</text>
        <text x="75" y="90" textAnchor="middle" fontSize="15" fontWeight="700" fill="#1d2a2e">{inr(total)}</text>
      </svg>
      <div className="legend" style={{ flex: 1, minWidth: 160, flexDirection: "column", flexWrap: "nowrap" }}>
        {data.slice(0, 7).map((d) => (
          <div key={d.label}>
            <i style={{ background: CAT_COLORS[d.label] || "#bbb" }} />
            {d.label} <b>{inr(d.value)}</b> <span className="mute">{Math.round((d.value / total) * 100)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function Trend({ months }: { months: { month: string; income: number; spend: number }[] }) {
  const max = Math.max(...months.map((m) => Math.max(m.income, m.spend)), 1);
  const W = 100 / months.length;
  return (
    <svg viewBox="0 0 320 150" width="100%" role="img" aria-label="Income vs spend by month">
      {months.map((m, i) => {
        const x = i * (320 / months.length) + 12;
        const bw = (320 / months.length - 24) / 2;
        const h1 = (m.income / max) * 105, h2 = (m.spend / max) * 105;
        return (
          <g key={m.month}>
            <rect x={x} y={120 - h1} width={bw} height={h1} rx="3" fill="#cfe3e0" />
            <rect x={x + bw + 2} y={120 - h2} width={bw} height={h2} rx="3" fill="#2d7d76" />
            <text x={x + bw} y="138" textAnchor="middle" fontSize="10" fill="#66767b">{monthName(m.month).split(" ")[0]}</text>
            <text x={x + bw + 2 + bw / 2} y={114 - h2} textAnchor="middle" fontSize="8.5" fill="#1d2a2e">{Math.round(m.spend / 1000)}k</text>
          </g>
        );
      })}
      <text x="4" y="12" fontSize="9" fill="#66767b">Income (light) vs spend (dark)</text>
      <rect x="0" y="0" width={W * 0} height="0" />
    </svg>
  );
}

export function Progress({ pct, tone }: { pct: number; tone?: "warn" | "bad" | "good" }) {
  return <div className={"bar " + (tone || "")}><i style={{ width: Math.min(100, Math.max(0, pct)) + "%" }} /></div>;
}

export function Sev({ s }: { s: string }) {
  return <span className={"badge " + s}>{s === "alert" ? "Needs attention" : s === "warn" ? "Heads up" : "FYI"}</span>;
}
