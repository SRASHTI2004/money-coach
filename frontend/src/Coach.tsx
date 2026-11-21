import { useEffect, useRef, useState } from "react";
import { api } from "./api";
import { Ctx, Md } from "./parts";

type Step = { tool: string; args: any; result?: string };
type Msg = { role: "user" | "model"; text: string; tools?: Step[]; ai?: boolean; guard?: boolean; cached?: boolean };

const SUGGEST = [
  "What if I cut dining out by 30%?",
  "Why am I over budget on dining?",
  "Set my dining budget to 4000 and explain why",
  "Which subscriptions should I look at?",
  "Am I on track for my goals?",
  "Which mutual fund should I buy?",
];

const TOOL_LABEL: Record<string, string> = {
  get_profile: "Read your profile", run_what_if: "Ran a what-if simulation", list_subscriptions: "Listed your subscriptions",
  list_nudges: "Checked your nudges", explain_nudge: "Explained a nudge", get_spending_summary: "Read your monthly summary",
  propose_change: "Drafted a change for you to confirm",
};

const argText = (a: any) => {
  if (!a || !Object.keys(a).length) return "";
  if (a.adjustments) return a.adjustments.map((x: any) => `${x.category} ${x.percent !== undefined ? (x.percent > 0 ? "+" : "") + x.percent + "%" : (x.amount > 0 ? "+" : "") + "₹" + x.amount}`).join(", ");
  return Object.entries(a).filter(([k]) => k !== "reason").map(([k, v]) => `${k}=${v}`).join(", ");
};

function Steps({ tools }: { tools: Step[] }) {
  return (
    <div className="steps">
      <div className="steps-h">How the coach got this answer</div>
      {tools.map((t, i) => (
        <div className="step" key={i}>
          <span className="step-n">{i + 1}</span>
          <div>
            <b>{TOOL_LABEL[t.tool] || t.tool}</b> <code>{t.tool}({argText(t.args)})</code>
            {t.result && <div className="small mute">&rarr; {t.result}</div>}
          </div>
        </div>
      ))}
    </div>
  );
}

export default function Coach({ refresh, toast, summary }: Ctx) {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [props, setProps] = useState<any[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api("/chat/history").then((h) => { setMsgs(h.messages); setProps(h.proposals); }).catch(() => {});
  }, [summary]);
  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }); }, [msgs, busy]);

  const send = async (m: string) => {
    if (!m.trim() || busy) return;
    setMsgs((x) => [...x, { role: "user", text: m }]); setText(""); setBusy(true);
    try {
      const r = await api("/chat", { body: { message: m } });
      setMsgs((x) => [...x, { role: "model", text: r.reply, tools: r.tools, ai: r.ai, guard: r.guardrail, cached: r.cached }]);
      setProps(r.proposals);
    } catch (e: any) { toast(e.message); } finally { setBusy(false); }
  };
  const decide = async (p: any, ok: boolean) => {
    await api(`/proposals/${p.id}/${ok ? "confirm" : "reject"}`, { method: "POST" });
    setProps((x) => x.filter((y) => y.id !== p.id));
    toast(ok ? "Applied: " + p.description : "Dismissed.");
    if (ok) await refresh();
  };

  return (
    <div className="card">
      <h2>Ask your coach</h2>
      <p className="small mute" style={{ marginTop: -6 }}>It reads your data through tools, runs what-ifs, and can <b>propose</b> changes, but nothing changes until you press Confirm. It never picks stocks, funds or other securities.</p>
      <div className="chat">
        {msgs.length === 0 && <div className="mute small">Try one of the questions below.</div>}
        {msgs.map((m, i) => (
          <div key={i} className={"msg " + m.role + (m.guard ? " guard" : "")}>
            {m.role === "model" && m.guard && <div className="guard-badge">&#128737; Guardrail active &middot; educational answer, no product named</div>}
            {m.role === "model" ? <Md text={m.text} /> : m.text}
            {m.tools && m.tools.length > 0 && <Steps tools={m.tools} />}
            {m.role === "model" && !m.guard && m.tools !== undefined && (
              <div className="tools">{m.cached ? "Gemini answer with tools (pre-computed for the demo data)" : m.ai ? "Answered by Gemini with tools" : "Answered by built-in rules (AI offline)"}</div>)}
          </div>
        ))}
        {busy && <div className="msg model mute">Thinking and using tools...</div>}
        <div ref={end} />
      </div>
      {props.map((p) => (
        <div className="proposal" key={p.id}>
          <div className="small mute" style={{ textTransform: "uppercase", letterSpacing: ".4px" }}>Proposed change - not applied yet</div>
          <div style={{ fontWeight: 600, margin: "2px 0" }}>{p.description}</div>
          {p.reason && <div className="small mute">{p.reason}</div>}
          <div className="row" style={{ marginTop: 8 }}>
            <button className="btn sm" onClick={() => decide(p, true)}>Confirm</button>
            <button className="btn sm muted" onClick={() => decide(p, false)}>Dismiss</button>
          </div>
        </div>
      ))}
      <div className="chips">{SUGGEST.map((s) => <button key={s} className="chip" onClick={() => send(s)}>{s}</button>)}</div>
      <form className="row" onSubmit={(e) => { e.preventDefault(); send(text); }}>
        <input style={{ flex: 1, minWidth: 180 }} value={text} onChange={(e) => setText(e.target.value)} placeholder="Ask about your money..." />
        <button className="btn" disabled={busy}>Send</button>
      </form>
    </div>
  );
}
