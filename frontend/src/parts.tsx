import { type ReactNode, useCallback, useEffect, useState } from "react";
import { api, CAT_COLORS, errMsg, inr, monthName } from "./api";
import type { Severity, Summary } from "./types";

export type ToastKind = "learn" | undefined;
export interface Ctx {
  refresh: () => Promise<void>;
  toast: (m: string, kind?: ToastKind) => void;
  summary: Summary;
  goTab: (t: string) => void;
}

/** Load a GET endpoint with consistent loading / error state. `dep` changes refetch silently (data stays visible). */
export function useApi<T>(path: string, dep?: unknown) {
  const [nonce, setNonce] = useState(0);
  const key = `${path}|${nonce}`;
  const [res, setRes] = useState<{ key: string; data: T | null; error: string }>({ key: "", data: null, error: "" });
  useEffect(() => {
    let live = true;
    api<T>(path)
      .then((data) => live && setRes({ key, data, error: "" }))
      .catch((e) => live && setRes((r) => ({ key, data: r.data, error: errMsg(e) })));
    return () => { live = false; };
  }, [path, key, dep]);
  const reload = useCallback(() => setNonce((n) => n + 1), []);
  return { data: res.data, error: res.key === key ? res.error : "", loading: res.key !== key, reload };
}

export function Loading({ what = "Loading" }: { what?: string }) {
  return <div className="state" role="status" aria-live="polite"><span className="spinner" aria-hidden="true" />{what}...</div>;
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="state error" role="alert">
      <b>Couldn&apos;t load this.</b> {message}
      {onRetry && <div style={{ marginTop: 8 }}><button className="btn sm" onClick={onRetry}>Try again</button></div>}
    </div>
  );
}

export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return <div className="state"><b>{title}</b>{children && <div className="small mute">{children}</div>}</div>;
}

function inline(s: string): ReactNode[] {
  return s.split(/(\*\*[^*]+\*\*|\*[^*\s][^*]*\*)/g).map((p, i) =>
    p.startsWith("**") ? <b key={i}>{p.slice(2, -2)}</b>
      : p.startsWith("*") && p.endsWith("*") && p.length > 2 ? <em key={i}>{p.slice(1, -1)}</em> : <span key={i}>{p}</span>);
}

/** Tiny markdown renderer: paragraphs, bullet lists, **bold**, *italic* (no HTML injection). */
export function Md({ text }: { text: string }) {
  return (
    <div className="md">
      {text.split(/\n{2,}/).map((b, i) => {
        const lines = b.split("\n");
        if (lines.every((l) => /^\s*[-*] /.test(l)))
          return <ul key={i}>{lines.map((l, j) => <li key={j}>{inline(l.replace(/^\s*[-*] /, ""))}</li>)}</ul>;
        return <p key={i}>{lines.map((l, j) => <span key={j}>{inline(l)}{j < lines.length - 1 && <br />}</span>)}</p>;
      })}
    </div>
  );
}

const DONUT_RADIUS = 52;

export function Donut({ data }: { data: { label: string; value: number }[] }) {
  const total = data.reduce((a, b) => a + b.value, 0) || 1;
  const C = 2 * Math.PI * DONUT_RADIUS;
  const starts = data.map((_, i) => data.slice(0, i).reduce((a, b) => a + (b.value / total) * C, 0));
  return (
    <div className="row" style={{ alignItems: "center", gap: 20 }}>
      <svg width="150" height="150" viewBox="0 0 150 150" role="img" aria-label={`Spending by category, total ${inr(total)}`}>
        <g transform="rotate(-90 75 75)">
          {data.map((d, i) => {
            const len = (d.value / total) * C;
            return (
              <circle key={d.label} cx="75" cy="75" r={DONUT_RADIUS} fill="none" stroke={CAT_COLORS[d.label] || "#bbb"} strokeWidth="22"
                strokeDasharray={`${len} ${C - len}`} strokeDashoffset={-starts[i]} />
            );
          })}
        </g>
        <text x="75" y="72" textAnchor="middle" fontSize="11" fill="#566468">Spent</text>
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
  const desc = months.map((m) => `${monthName(m.month)}: income ${inr(m.income)}, spend ${inr(m.spend)}`).join("; ");
  return (
    <svg viewBox="0 0 320 150" width="100%" role="img" aria-label={`Income versus spend by month. ${desc}`}>
      {months.map((m, i) => {
        const x = i * (320 / months.length) + 12;
        const bw = (320 / months.length - 24) / 2;
        const h1 = (m.income / max) * 105, h2 = (m.spend / max) * 105;
        return (
          <g key={m.month}>
            <rect x={x} y={120 - h1} width={bw} height={h1} rx="3" fill="#cfe3e0" />
            <rect x={x + bw + 2} y={120 - h2} width={bw} height={h2} rx="3" fill="#2d7d76" />
            <text x={x + bw} y="138" textAnchor="middle" fontSize="10" fill="#566468">{monthName(m.month).split(" ")[0]}</text>
            <text x={x + bw + 2 + bw / 2} y={114 - h2} textAnchor="middle" fontSize="8.5" fill="#1d2a2e">{Math.round(m.spend / 1000)}k</text>
          </g>
        );
      })}
      <text x="4" y="12" fontSize="9" fill="#566468">Income (light) vs spend (dark)</text>
    </svg>
  );
}

export function Progress({ pct, tone, label }: { pct: number; tone?: "warn" | "bad" | "good"; label: string }) {
  const v = Math.min(100, Math.max(0, pct));
  return (
    <div className={"bar " + (tone || "")} role="progressbar" aria-label={label} aria-valuenow={Math.round(v)} aria-valuemin={0} aria-valuemax={100}>
      <i style={{ width: v + "%" }} />
    </div>
  );
}

export function Sev({ s }: { s: Severity }) {
  return <span className={"badge " + s}>{s === "alert" ? "Needs attention" : s === "warn" ? "Heads up" : "FYI"}</span>;
}
