import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import Coach from "./Coach";
import Dashboard from "./Dashboard";
import Plan from "./Plan";
import Review from "./Review";
import Subscriptions from "./Subscriptions";
import Transactions from "./Transactions";
import WhatIf from "./WhatIf";

const TABS: [string, string][] = [
  ["home", "Dashboard"], ["tx", "Transactions"], ["subs", "Subscriptions"], ["plan", "Plan & goals"],
  ["whatif", "What-if"], ["review", "Monthly review"], ["coach", "Coach"],
];

export default function App() {
  const [tab, setTab] = useState(() => { try { return localStorage.getItem("mc_tab") || "home"; } catch { return "home"; } });
  const [summary, setSummary] = useState<any>(null);
  const [health, setHealth] = useState<any>(null);
  const [toastMsg, setToastMsg] = useState("");
  const [loading, setLoading] = useState(false);

  const toast = useCallback((m: string) => { setToastMsg(m); setTimeout(() => setToastMsg(""), 4500); }, []);
  const refresh = useCallback(async () => { setSummary(await api("/summary")); setHealth(await api("/health")); }, []);
  useEffect(() => { refresh().catch(() => toast("Could not reach the server")); }, [refresh, toast]);
  const goTab = (t: string) => { setTab(t); try { localStorage.setItem("mc_tab", t); } catch {} window.scrollTo(0, 0); };

  const loadDemo = async () => {
    setLoading(true);
    try { await api("/demo/load", { method: "POST" }); await refresh(); toast("Demo data loaded: 3 files, 3 months of transactions, goals and subscriptions."); goTab("home"); }
    catch (e: any) { toast(e.message); } finally { setLoading(false); }
  };
  const reset = async () => { await api("/reset", { method: "POST" }); await refresh(); toast("Cleared."); };

  const ctx = { refresh, toast, summary, goTab };
  const empty = summary?.empty;
  const ai = health?.ai?.available;

  return (
    <div className="app">
      <header className="top">
        <div className="logo"><i>&#8377;</i> Money Coach</div>
        <span className={"badge " + (health && !health.ai_enabled ? "off" : ai === false ? "off" : "")}>
          {!health ? "..." : !health.ai_enabled ? "AI off - rules mode" : ai === false ? "AI busy - rules fallback" : "Gemini connected"}
        </span>
        <div className="spacer" />
        {!empty && summary && <button className="btn sm muted" onClick={reset}>Clear data</button>}
        <button className="btn sm" onClick={loadDemo} disabled={loading}>{loading ? "Loading demo..." : "Load demo data"}</button>
      </header>

      {!summary ? <p className="mute">Loading...</p> : empty && tab !== "tx" ? (
        <div className="card empty">
          <h1>Your money, understood.</h1>
          <p className="mute" style={{ maxWidth: 520, margin: "0 auto 18px" }}>
            Upload a bank statement (CSV or PDF) or paste bank SMS, and the coach builds a living model of your money:
            categories, subscriptions, goals, what-if scenarios and nudges when you drift.
          </p>
          <div className="row" style={{ justifyContent: "center" }}>
            <button className="btn" onClick={loadDemo} disabled={loading}>{loading ? "Loading..." : "Load demo data (one click)"}</button>
            <button className="btn ghost" onClick={() => goTab("tx")}>Upload my own</button>
          </div>
        </div>
      ) : (
        <>
          <nav className="tabs">{TABS.map(([k, l]) => <button key={k} className={tab === k ? "on" : ""} onClick={() => goTab(k)}>{l}</button>)}</nav>
          {empty ? <Transactions {...ctx} summary={{ months: [] }} /> : <>
            {tab === "home" && <Dashboard {...ctx} />}
            {tab === "tx" && <Transactions {...ctx} />}
            {tab === "subs" && <Subscriptions {...ctx} />}
            {tab === "plan" && <Plan {...ctx} />}
            {tab === "whatif" && <WhatIf {...ctx} />}
            {tab === "review" && <Review {...ctx} />}
            {tab === "coach" && <Coach {...ctx} />}
          </>}
        </>
      )}
      {toastMsg && <div className="toast" role="status">{toastMsg}</div>}
      <div className="disclaimer">{health?.disclaimer || "Educational information and scenario modelling only - not investment advice. This coach never recommends specific stocks, funds or securities."}</div>
    </div>
  );
}
