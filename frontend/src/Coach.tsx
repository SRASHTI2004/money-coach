import { useEffect, useRef, useState } from "react";
import { api } from "./api";
import { Ctx, Md } from "./parts";

type Msg = { role: "user" | "model"; text: string; tools?: any[]; ai?: boolean; guard?: boolean };

const SUGGEST = [
  "What if I cut dining out by 30%?",
  "What if my rent goes up by 3000?",
  "Why am I over budget on dining?",
  "Which subscriptions should I look at?",
  "Which mutual fund should I buy?",
  "Am I on track for my goals?",
];

export default function Coach({ refresh, toast, summary }: Ctx) {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [props, setProps] = useState<any[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api("/chat/history").then((h) => { setMsgs(h.messages); setProps(h.proposals); }).catch(() => {});
  }, [summary]);
  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs, busy]);

  const send = async (m: string) => {
    if (!m.trim() || busy) return;
    setMsgs((x) => [...x, { role: "user", text: m }]); setText(""); setBusy(true);
    try {
      const r = await api("/chat", { body: { message: m } });
      setMsgs((x) => [...x, { role: "model", text: r.reply, tools: r.tools, ai: r.ai, guard: r.guardrail }]);
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
      <p className="small mute" style={{ marginTop: -6 }}>It can read your profile, run what-ifs, list subscriptions and explain nudges. It can <b>propose</b> changes, but nothing changes until you press Confirm. It never picks stocks, funds or other securities.</p>
      <div className="chat">
        {msgs.length === 0 && <div className="mute small">Try one of the questions below.</div>}
        {msgs.map((m, i) => (
          <div key={i} className={"msg " + m.role + (m.guard ? " guard" : "")}>
            {m.role === "model" ? <Md text={m.text} /> : m.text}
            {m.role === "model" && m.guard && <div className="tools">Guardrail: educational answer only - no product recommendations</div>}
            {m.tools && m.tools.length > 0 && <div className="tools">Coach used: {m.tools.map((t, j) => <span key={j}>{t.tool}</span>)}</div>}
            {m.role === "model" && m.ai === false && !m.guard && m.tools !== undefined && <div className="tools">Answered by built-in rules (AI offline)</div>}
          </div>
        ))}
        {busy && <div className="msg model mute">Thinking...</div>}
        <div ref={end} />
      </div>
      {props.map((p) => (
        <div className="proposal" key={p.id}>
          <b>Proposed change</b>
          <div>{p.description}</div>
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
