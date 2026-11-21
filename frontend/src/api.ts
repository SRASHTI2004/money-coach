const REQUEST_TIMEOUT_MS = 45_000;
const UID_MAX_CHARS = 40;

function uid(): string {
  try {
    const q = new URLSearchParams(window.location.search).get("u");
    if (q) localStorage.setItem("mc_uid", q.replace(/[^a-zA-Z0-9_-]/g, "").slice(0, UID_MAX_CHARS));
    let u = localStorage.getItem("mc_uid");
    if (!u) {
      u = "u" + Math.random().toString(36).slice(2, 10);
      localStorage.setItem("mc_uid", u);
    }
    return u;
  } catch {
    return "demo";
  }
}

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
  }
}

interface Options {
  method?: string;
  body?: unknown;
  form?: FormData;
}

/** Typed fetch wrapper: JSON in/out, 45 s timeout, friendly error messages. */
export async function api<T>(path: string, opts: Options = {}): Promise<T> {
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), REQUEST_TIMEOUT_MS);
  try {
    const r = await fetch("/api" + path, {
      method: opts.method || (opts.body || opts.form ? "POST" : "GET"),
      headers: { "X-User": uid(), ...(opts.body ? { "Content-Type": "application/json" } : {}) },
      body: opts.form ? opts.form : opts.body ? JSON.stringify(opts.body) : undefined,
      signal: ctl.signal,
    });
    if (!r.ok) {
      let msg = "Something went wrong. Please try again.";
      try {
        const j = (await r.json()) as { detail?: string };
        if (typeof j.detail === "string") msg = j.detail;
      } catch {
        /* non-JSON error body: keep the default message */
      }
      throw new ApiError(msg, r.status);
    }
    return (await r.json()) as T;
  } catch (e) {
    if (e instanceof ApiError) throw e;
    if (e instanceof DOMException && e.name === "AbortError") throw new ApiError("The server took too long to respond. Please try again.", 0);
    throw new ApiError("Could not reach the server. Check your connection and try again.", 0);
  } finally {
    clearTimeout(timer);
  }
}

export const errMsg = (e: unknown): string => (e instanceof Error ? e.message : "Something went wrong.");

const LAKH = 1e5;
const CRORE = 1e7;
const THOUSAND = 1e3;

export function inr(v: number | null | undefined, sign = false): string {
  if (v === null || v === undefined || isNaN(v)) return "-";
  const n = Math.round(Math.abs(v));
  return (v < 0 ? "-" : sign && v > 0 ? "+" : "") + "₹" + n.toLocaleString("en-IN");
}

/** Compact Indian units for charts and tight spaces: 1,80,000 -> 1.8L ; 2,50,00,000 -> 2.5Cr */
export function inrShort(v: number): string {
  const a = Math.abs(v), s = v < 0 ? "-" : "";
  if (a >= CRORE) return `${s}₹${+(a / CRORE).toFixed(2)}Cr`;
  if (a >= LAKH) return `${s}₹${+(a / LAKH).toFixed(1)}L`;
  if (a >= THOUSAND) return `${s}₹${+(a / THOUSAND).toFixed(a >= 1e4 ? 0 : 1)}k`;
  return `${s}₹${Math.round(a)}`;
}

export const monthName = (m: string): string =>
  new Date(m + "-01T00:00:00").toLocaleString("en-IN", { month: "short", year: "numeric" });

export const dateFmt = (d: string | null | undefined): string =>
  d ? new Date(d + "T00:00:00").toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }) : "-";

export const CAT_COLORS: Record<string, string> = {
  Rent: "#2d7d76", Groceries: "#6aa84f", Dining: "#e08e45", Transport: "#5b8fd1", Utilities: "#8a7fc9",
  Subscriptions: "#c9628a", Shopping: "#d4a72c", Health: "#cf5c5c", Entertainment: "#46a7b5", Travel: "#9a6b4f",
  "EMI & Loans": "#7a8794", Insurance: "#5f9f8f", Education: "#a1887f", Cash: "#b0b7a8", Other: "#c4c9bf",
};

export const SRC_LABEL: Record<string, string> = { sms: "SMS", pdf: "PDF", csv: "CSV" };
export const CAT_SRC: Record<string, string> = {
  rule: "your rule", keyword: "built-in", ai: "Gemini AI", history: "learned", user: "you", none: "-",
};
