import { useEffect, useRef, useState } from "react";
import { api, errMsg } from "./api";
import { type Ctx, Md } from "./parts";
import type { ChatHistory, ChatReply, Proposal, Step } from "./types";

interface Msg { role: "user" | "model"; text: string; tools?: Step[]; ai?: boolean; guard?: boolean; cached?: boolean }
interface Adjustment { category: string; percent?: number; amount?: number }

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

const argText = (a: Record<string, unknown>): string => {
  if (!a || !Object.keys(a).length) return "";
  if (Array.isArray(a.adjustments)) {
    return (a.adjustments as Adjustment[]).map((x) =>
      `${x.category} ${x.percent !== undefined ? (x.percent > 0 ? "+" : "") + x.percent + "%" : ((x.amount ?? 0) > 0 ? "+" : "") + "₹" + x.amount}`).join(", ");
  }
  return Object.entries(a).filter(([k]) => k !== "reason").map(([k, v]) => `${k}=${String(v)}`).join(", ");
};

function Steps({ tools }: { tools: Step[] }) {
  return (
    <div className="steps">
      <div className="steps-h">How the coach got this answer</div>
      <ol>
        {tools.map((t, i) => (
          <li className="step" key={i}>
            <span className="step-n" aria-hidden="true">{i + 1}</span>
            <div>
              <b>{TOOL_LABEL[t.tool] || t.tool}</b> <code>{t.tool}({argText(t.args)})</code>
              {t.result && <div className="small mute">&rarr; {t.result}</div>}
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}

export default function Coach({ refresh, toast, summary }: Ctx) {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [props, setProps] = useState<Proposal[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api<ChatHistory>("/chat/history").then((h) => { setMsgs(h.messages); setProps(h.proposals); }).catch(() => undefined);
  }, [summary]);
  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }); }, [msgs, busy]);

  const send = async (m: string) => {
    if (!m.trim() || busy) return;
    setMsgs((x) => [...x, { role: "user", text: m }]);
    setText("");
    setBusy(true);
    try {
      const r = await api<ChatReply>("/chat", { body: { message: m } });
      setMsgs((x) => [...x, { role: "model", text: r.reply, tools: r.tools, ai: r.ai, guard: r.guardrail, cached: r.cached }]);
      setProps(r.proposals);
    } catch (e) {
      setMsgs((x) => [...x, { role: "model", text: "Sorry, I couldn't answer that just now. " + errMsg(e) }]);
    } finally { setBusy(false); }
  };
  const decide = async (p: Proposal, ok: boolean) => {
    try {
      await api(`/proposals/${p.id}/${ok ? "confirm" : "reject"}`, { method: "POST" });
      setProps((x) => x.filter((y) => y.id !== p.id));
      toast(ok ? "Applied: " + p.description : "Dismissed.");
      if (ok) await refresh();
    } catch (e) { toast(errMsg(e)); }
  };

  return (
    <section className="card" aria-labelledby="coach-h">
      <h2 id="coach-h">Ask your coach</h2>
      <p className="small mute" style={{ marginTop: -6 }}>It reads your data through tools, runs what-ifs, and can <b>propose</b> changes, but nothing changes until you press Confirm. It never picks stocks, funds or other securities.</p>
      <div className="chat" role="log" aria-live="polite" aria-label="Conversation">
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
        <div className="proposal" key={p.id} role="group" aria-label="Proposed change">
          <div className="small mute" style={{ textTransform: "uppercase", letterSpacing: ".4px" }}>Proposed change - not applied yet</div>
          <div style={{ fontWeight: 600, margin: "2px 0" }}>{p.description}</div>
          {p.reason && <div className="small mute">{p.reason}</div>}
          <div className="row" style={{ marginTop: 8 }}>
            <button className="btn sm" onClick={() => decide(p, true)}>Confirm</button>
            <button className="btn sm muted" onClick={() => decide(p, false)}>Dismiss</button>
          </div>
        </div>
      ))}
      <div className="chips" role="group" aria-label="Suggested questions">{SUGGEST.map((s) => <button key={s} className="chip" onClick={() => send(s)}>{s}</button>)}</div>
      <form className="row" onSubmit={(e) => { e.preventDefault(); send(text); }}>
        <label className="sr-only" htmlFor="coach-input">Ask the coach</label>
        <input id="coach-input" style={{ flex: 1, minWidth: 180 }} value={text} maxLength={1000} onChange={(e) => setText(e.target.value)} placeholder="Ask about your money..." />
        <button className="btn" disabled={busy}>Send</button>
      </form>
    </section>
  );
}
