import { useCallback, useEffect, useState } from "react";
import { api, errMsg } from "./api";
import Coach from "./Coach";
import Dashboard from "./Dashboard";
import HowItWorks from "./HowItWorks";
import LifeEvents from "./LifeEvents";
import { type Ctx, ErrorBox, type ToastKind } from "./parts";
import Plan from "./Plan";
import Review from "./Review";
import Subscriptions from "./Subscriptions";
import TimelinePage from "./TimelinePage";
import Transactions from "./Transactions";
import type { Health, Summary } from "./types";
import WhatIf from "./WhatIf";

const TABS: [string, string][] = [
  ["home", "Dashboard"], ["coach", "Coach"], ["life", "Life events"], ["whatif", "What-if"], ["subs", "Subscriptions"],
  ["tx", "Transactions"], ["plan", "Plan & goals"], ["timeline", "Timeline"], ["review", "Monthly review"],
];
const TOAST_MS = 5500;
const FALLBACK_DISCLAIMER = "Educational information and scenario modelling only - not investment advice. This coach never recommends specific stocks, funds or securities.";
const EMPTY_SUMMARY = { months: [] } as unknown as Summary;

function initialTab(): string {
  try {
    return new URLSearchParams(window.location.search).get("tab") || localStorage.getItem("mc_tab") || "home";
  } catch {
    return "home";
  }
}

export default function App() {
  const [tab, setTab] = useState(initialTab);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [loadError, setLoadError] = useState("");
  const [toastMsg, setToastMsg] = useState<{ t: string; kind?: ToastKind } | null>(null);
  const [loading, setLoading] = useState(false);
  const [showHow, setShowHow] = useState(false);

  const toast = useCallback((m: string, kind?: ToastKind) => {
    setToastMsg({ t: m, kind });
    setTimeout(() => setToastMsg(null), TOAST_MS);
  }, []);
  const refresh = useCallback(async () => {
    const [s, h] = await Promise.all([api<Summary>("/summary"), api<Health>("/health")]);
    setSummary(s);
    setHealth(h);
    setLoadError("");
  }, []);
  const boot = useCallback(() => {
    setLoadError("");
    refresh().catch((e) => setLoadError(errMsg(e)));
  }, [refresh]);
  useEffect(() => {
    let live = true;
    Promise.all([api<Summary>("/summary"), api<Health>("/health")])
      .then(([sm, h]) => { if (live) { setSummary(sm); setHealth(h); } })
      .catch((e) => { if (live) setLoadError(errMsg(e)); });
    return () => { live = false; };
  }, []);

  const goTab = (t: string) => {
    setTab(t);
    try { localStorage.setItem("mc_tab", t); } catch { /* storage unavailable: tab just won't persist */ }
    window.scrollTo(0, 0);
  };
  const loadDemo = async () => {
    setLoading(true);
    try {
      await api("/demo/load", { method: "POST" });
      await refresh();
      goTab("home");
      toast("Demo loaded: a CSV, a PDF statement and bank SMS, with goals and subscriptions.");
    } catch (e) { toast(errMsg(e)); } finally { setLoading(false); }
  };
  const reset = async () => {
    try { await api("/reset", { method: "POST" }); await refresh(); toast("Cleared."); } catch (e) { toast(errMsg(e)); }
  };

  const empty = !!summary?.empty;
  const ai = health?.ai?.available;
  const badge = !health ? "..." : !health.ai_enabled ? "AI off - rules mode" : ai === false ? "AI busy - rules fallback" : "Gemini connected";
  const disclaimer = health?.disclaimer || FALLBACK_DISCLAIMER;

  const header = (
    <header className="top">
      <div className="logo"><i aria-hidden="true">&#8377;</i> Money Coach</div>
      <span className={"badge " + (health && (!health.ai_enabled || ai === false) ? "off" : "")}>{badge}</span>
      <div className="spacer" />
      <button className="btn sm ghost" onClick={() => setShowHow(true)} aria-haspopup="dialog">How it works</button>
      {summary && !empty && <button className="btn sm muted" onClick={reset}>Clear data</button>}
      {summary && !empty && <button className="btn sm ghost" onClick={loadDemo} disabled={loading}>{loading ? "Loading..." : "Reload demo"}</button>}
    </header>
  );

  const footer = (
    <>
      {toastMsg && <div className={"toast " + (toastMsg.kind || "")} role="status" aria-live="polite">{toastMsg.kind === "learn" && <b>Learned rule </b>}{toastMsg.t}</div>}
      {showHow && <HowItWorks onClose={() => setShowHow(false)} />}
      <footer className="disclaimer">{disclaimer}</footer>
    </>
  );

  if (!summary) {
    return (
      <div className="app">
        {header}
        <main id="main">
          {loadError ? <ErrorBox message={loadError} onRetry={boot} /> : (
            <div className="state" role="status" aria-live="polite">
              <span className="spinner" aria-hidden="true" />
              Loading your money model...
              <span className="cold-hint">Waking up the server - free hosting can take about 30 seconds on the first visit. Thanks for waiting!</span>
            </div>
          )}
        </main>
        {footer}
      </div>
    );
  }

  if (empty && tab !== "tx") {
    return (
      <div className="app">
        {header}
        <main id="main">
          <section className="hero">
            <span className="badge">Personal finance coach &middot; made for India</span>
            <h1>Your money, understood <br className="hide-m" />- and it adapts when life changes.</h1>
            <p>Drop in a bank statement or paste your UPI/bank SMS. The coach learns your habits and corrections, tracks subscriptions and AutoPay mandates, and models what-ifs and life events, without ever picking a stock for you.</p>
            <div className="row" style={{ justifyContent: "center", gap: 12 }}>
              <button className="btn big" onClick={loadDemo} disabled={loading}>{loading ? "Loading demo..." : "Try with demo data"}</button>
              <button className="btn big ghost" onClick={() => goTab("tx")}>Use my own statement</button>
            </div>
            <div className="hero-feats">
              <div><b>CSV &middot; PDF &middot; SMS</b><span>messy formats, Indian banks</span></div>
              <div><b>Learns your fixes</b><span>one correction becomes a rule</span></div>
              <div><b>Life-event simulator</b><span>job loss, EMI, hike, rent</span></div>
              <div><b>Agentic coach</b><span>proposes, you confirm</span></div>
            </div>
            <p className="small mute" style={{ marginTop: 18 }}>No signup. Demo loads in one click. Educational only - never investment advice.</p>
          </section>
        </main>
        {footer}
      </div>
    );
  }

  const ctx: Ctx = { refresh, toast, summary: empty ? EMPTY_SUMMARY : summary, goTab };
  return (
    <div className="app">
      <a className="skip" href="#main">Skip to content</a>
      {header}
      <nav className="tabs" aria-label="Sections">
        {TABS.map(([k, l]) => (
          <button key={k} aria-current={tab === k ? "page" : undefined} className={tab === k ? "on" : ""} onClick={() => goTab(k)}>{l}</button>
        ))}
      </nav>
      <main id="main">
        <h1 className="sr-only">{TABS.find(([k]) => k === tab)?.[1] ?? "Dashboard"}</h1>
        {empty ? <Transactions {...ctx} /> : <>
          {tab === "home" && <Dashboard {...ctx} />}
          {tab === "coach" && <Coach {...ctx} />}
          {tab === "life" && <LifeEvents {...ctx} />}
          {tab === "whatif" && <WhatIf {...ctx} />}
          {tab === "subs" && <Subscriptions {...ctx} />}
          {tab === "tx" && <Transactions {...ctx} />}
          {tab === "plan" && <Plan {...ctx} />}
          {tab === "timeline" && <TimelinePage {...ctx} />}
          {tab === "review" && <Review {...ctx} />}
        </>}
      </main>
      {footer}
    </div>
  );
}
