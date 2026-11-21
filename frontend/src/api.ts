function uid(): string {
  try {
    const q = new URLSearchParams(window.location.search).get("u");
    if (q) localStorage.setItem("mc_uid", q.replace(/[^a-zA-Z0-9_-]/g, "").slice(0, 40));
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

export async function api<T = any>(
  path: string,
  opts: { method?: string; body?: any; form?: FormData } = {}
): Promise<T> {
  const r = await fetch("/api" + path, {
    method: opts.method || (opts.body || opts.form ? "POST" : "GET"),
    headers: { "X-User": uid(), ...(opts.body ? { "Content-Type": "application/json" } : {}) },
    body: opts.form ? opts.form : opts.body ? JSON.stringify(opts.body) : undefined,
  });
  if (!r.ok) {
    let m = r.statusText;
    try {
      m = (await r.json()).detail || m;
    } catch {}
    throw new Error(m);
  }
  return r.json();
}

export function inr(v: number | null | undefined, sign = false): string {
  if (v === null || v === undefined || isNaN(v as number)) return "-";
  const n = Math.round(Math.abs(v));
  return (v < 0 ? "-" : sign && v > 0 ? "+" : "") + "₹" + n.toLocaleString("en-IN");
}

export const monthName = (m: string) =>
  new Date(m + "-01T00:00:00").toLocaleString("en-IN", { month: "short", year: "numeric" });

export const dateFmt = (d: string | null | undefined) =>
  d ? new Date(d + "T00:00:00").toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }) : "-";

export const CAT_COLORS: Record<string, string> = {
  Rent: "#2d7d76", Groceries: "#6aa84f", Dining: "#e08e45", Transport: "#5b8fd1", Utilities: "#8a7fc9",
  Subscriptions: "#c9628a", Shopping: "#d4a72c", Health: "#cf5c5c", Entertainment: "#46a7b5", Travel: "#9a6b4f",
  "EMI & Loans": "#7a8794", Insurance: "#5f9f8f", Education: "#a1887f", Cash: "#b0b7a8", Other: "#c4c9bf",
};

/** Compact Indian units for charts and tight spaces: 1,80,000 -> ₹1.8L ; 2,50,00,000 -> ₹2.5Cr */
export function inrShort(v: number): string {
  const a = Math.abs(v), s = v < 0 ? "-" : "";
  if (a >= 1e7) return `${s}₹${+(a / 1e7).toFixed(2)}Cr`;
  if (a >= 1e5) return `${s}₹${+(a / 1e5).toFixed(1)}L`;
  if (a >= 1e3) return `${s}₹${+(a / 1e3).toFixed(a >= 1e4 ? 0 : 1)}k`;
  return `${s}₹${Math.round(a)}`;
}

export const SRC_LABEL: Record<string, string> = { sms: "SMS", pdf: "PDF", csv: "CSV" };
export const CAT_SRC: Record<string, string> = { rule: "your rule", keyword: "built-in", ai: "Gemini AI", history: "learned", user: "you", none: "-" };
