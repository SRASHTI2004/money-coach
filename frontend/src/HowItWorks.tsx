import { useEffect, useRef } from "react";

const AI_DOES = [
  "Reads text the parsers cannot (odd statement layouts, unusual SMS)",
  "Labels unknown merchants (e.g. a local tiffin centre as Dining)",
  "Writes the monthly review and explains nudges and life-event results in plain language",
  "Runs the coach chat: it calls tools, then explains what they returned",
];
const CODE_DOES = [
  "All money maths: totals, averages, free cash, goal dates, drift",
  "Finding subscriptions, price changes, cancelled plans and UPI AutoPay mandates",
  "The what-if and life-event simulators (month by month)",
  "Learning your category corrections as rules",
];

/** Modal explaining what Gemini does vs what plain code does, and the safety rules. */
export default function HowItWorks({ onClose }: { onClose: () => void }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const prev = document.activeElement as HTMLElement | null;
    ref.current?.querySelector<HTMLElement>("button")?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "Tab" && ref.current) {  // keep focus inside the dialog
        const f = ref.current.querySelectorAll<HTMLElement>("button, a[href]");
        const first = f[0], last = f[f.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    };
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("keydown", onKey); prev?.focus(); };
  }, [onClose]);

  return (
    <div className="modal-bg" onClick={onClose}>
      <div className="modal" role="dialog" aria-modal="true" aria-labelledby="hiw-title" ref={ref} onClick={(e) => e.stopPropagation()}>
        <div className="row" style={{ marginBottom: 6 }}>
          <h2 id="hiw-title" style={{ flex: 1, marginBottom: 0 }}>How Money Coach works</h2>
          <button className="btn sm muted" onClick={onClose} aria-label="Close">Close</button>
        </div>
        <div className="grid g2 stack" style={{ marginTop: 12 }}>
          <section aria-labelledby="hiw-ai">
            <h3 id="hiw-ai"><span className="badge">Gemini (AI)</span></h3>
            <ul>{AI_DOES.map((t) => <li key={t}>{t}</li>)}</ul>
          </section>
          <section aria-labelledby="hiw-code">
            <h3 id="hiw-code"><span className="badge info">Plain code</span></h3>
            <ul>{CODE_DOES.map((t) => <li key={t}>{t}</li>)}</ul>
          </section>
        </div>
        <h3>Safety rules</h3>
        <ul>
          <li><b>Confirm before change:</b> the coach can only propose a budget or goal change. Nothing is applied until you press Confirm.</li>
          <li><b>Never recommends securities:</b> asked which stock or fund to buy, it explains concepts and risk and names no product. Checked in code on both the question and the answer.</li>
          <li><b>Sample data only:</b> the demo uses made-up transactions; nothing real is needed to try it. Your own uploads stay in this app&apos;s database under an anonymous id.</li>
          <li><b>If AI is down:</b> built-in rules take over and the header badge says so.</li>
        </ul>
        <p className="small mute">Educational information and scenario modelling only. Not investment, tax or legal advice.</p>
      </div>
    </div>
  );
}
