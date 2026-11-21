import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import Coach from "./Coach";
import Dashboard from "./Dashboard";
import LifeEvents from "./LifeEvents";
import Plan from "./Plan";
import Review from "./Review";
import Subscriptions from "./Subscriptions";
import TimelinePage from "./TimelinePage";
import Transactions from "./Transactions";
import WhatIf from "./WhatIf";

const TABS: [string, string][] = [
  ["home", "Dashboard"], ["coach", "Coach"], ["life", "Life events"], ["whatif", "What-if"], ["subs", "Subscriptions"],
  ["tx", "Transactions"], ["plan", "Plan & goals"], ["timeline", "Timeline"], ["review", "Monthly review"],
];

function initialTab() {
  try {
    const q = new URLSearchParams(window.location.search).get("tab");
    if (q) return q;
    return localStorage.getItem("mc_tab") || "home";
  } catch { return "home"; }
}

export default function App() {
  const [tab, setTab] = useState(initialTab);
  const [summary, setSummary] = useState<any>(null);
  const [health, setHealth] = useState<any>(null);
  const [toastMsg, setToastMsg] = useState<{ t: string; kind?: string } | null>(null);
  const [loading, setLoading] = useState(false);

  const toast = useCallback((m: string, kind?: string) => { setToastMsg({ t: m, kind }); setTimeout(() => setToastMsg(null), 5500); }, []);
  const refresh = useCallback(async () => { setSummary(await api("/summary")); setHealth(await api("/health")); }, []);
  useEffect(() => { refresh().catch(() => toast("Could not reach the server")); }, [refresh, toast]);
  const goTab = (t: string) => { setTab(t); try { localStorage.setItem("mc_tab", t); } catch {} window.scrollTo(0, 0); };

  const loadDemo = async () => {
    setLoading(true);
    try { await api("/demo/load", { method: "POST" }); await refresh(); goTab("home"); toast("Demo loaded: a CSV, a PDF statement and bank SMS, with goals and subscriptions."); }
    catch (e: any) { toast(e.message); } finally { setLoading(false); }
  };
  const reset = async () => { await api("/reset", { method: "POST" }); await refresh(); toast("Cleared."); };

  const ctx = { refresh, toast, summary, goTab } as any;
  const empty = summary?.empty;
  const ai = health?.ai?.available;

  const header = (
    <header className="top">
      <div className="logo"><i>&#8377;</i> Money Coach</div>
      <span className={"badge " + (health && (!health.ai_enabled || ai === false) ? "off" : "")}>
        {!health ? "..." : !health.ai_enabled ? "AI off - rules mode" : ai === false ? "AI busy - rules fallback" : "Gemini connected"}
      </span>
      <div className="spacer" />
      {!empty && summary && <button className="btn sm muted" onClick={reset}>Clear data</button>}
      {!empty && summary && <button className="btn sm ghost" onClick={loadDemo} disabled={loading}>{loading ? "Loading..." : "Reload demo"}</button>}
    </header>
  );

  if (summary && empty && tab !== "tx") {
    return (
      <div className="app">
        {header}
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
        <div className="disclaimer">{health?.disclaimer || "Educational information and scenario modelling only - not investment advice. This coach never recommends specific stocks, funds or securities."}</div>
        {toastMsg && <div className="toast" role="status">{toastMsg.t}</div>}
      </div>
    );
  }

  return (
    <div className="app">
      {header}
      {!summary ? <p className="mute">Loading...</p> : (
        <>
          <nav className="tabs">{TABS.map(([k, l]) => <button key={k} className={tab === k ? "on" : ""} onClick={() => goTab(k)}>{l}</button>)}</nav>
          {empty ? <Transactions {...ctx} summary={{ months: [] }} /> : <>
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
        </>
      )}
      {toastMsg && <div className={"toast " + (toastMsg.kind || "")} role="status">{toastMsg.kind === "learn" && <b>Learned rule </b>}{toastMsg.t}</div>}
      <div className="disclaimer">{health?.disclaimer || "Educational information and scenario modelling only - not investment advice. This coach never recommends specific stocks, funds or securities."}</div>
    </div>
  );
}
