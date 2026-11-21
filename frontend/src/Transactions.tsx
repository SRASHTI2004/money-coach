import { useEffect, useRef, useState } from "react";
import { api, dateFmt, inr, monthName } from "./api";
import { Ctx } from "./parts";

const SRC: Record<string, string> = { rule: "your rule", keyword: "built-in", ai: "Gemini", history: "learned", user: "you", none: "-" };

export default function Transactions({ refresh, toast, summary }: Ctx) {
  const [tx, setTx] = useState<any[]>([]);
  const [cats, setCats] = useState<string[]>([]);
  const [rules, setRules] = useState<any[]>([]);
  const [f, setF] = useState({ month: "", category: "", q: "" });
  const [paste, setPaste] = useState("");
  const [busy, setBusy] = useState(false);
  const [report, setReport] = useState<any>(null);
  const file = useRef<HTMLInputElement>(null);

  const load = async () => {
    const qs = new URLSearchParams(Object.entries(f).filter(([, v]) => v) as string[][]).toString();
    setTx(await api("/transactions?limit=300&" + qs));
    setRules(await api("/rules"));
  };
  useEffect(() => { api("/categories").then(setCats); }, []);
  useEffect(() => { load().catch(() => {}); }, [f, summary]);

  const upload = async (fl: File) => {
    setBusy(true);
    try { const fd = new FormData(); fd.append("file", fl); setReport(await api("/upload", { form: fd })); await refresh(); }
    catch (e: any) { toast(e.message); } finally { setBusy(false); if (file.current) file.current.value = ""; }
  };
  const doPaste = async () => {
    setBusy(true);
    try { setReport(await api("/paste", { body: { text: paste } })); setPaste(""); await refresh(); }
    catch (e: any) { toast(e.message); } finally { setBusy(false); }
  };
  const fix = async (t: any, category: string) => {
    const r = await api("/transactions/" + t.id, { method: "PATCH", body: { category } });
    toast(r.rule_created
      ? `Learned: "${r.merchant}" -> ${category}.` + (r.also_updated ? ` Also updated ${r.also_updated} other transaction(s).` : "") + " Future ones will follow."
      : "Updated.");
    await refresh();
  };

  return (
    <>
      <div className="card">
        <h2>Add transactions</h2>
        <p className="small mute" style={{ marginTop: -6 }}>Bank CSV or PDF statements, or paste bank SMS. Messy layouts are fine - unreadable parts go to Gemini.</p>
        <div className="row">
          <input ref={file} type="file" accept=".csv,.pdf,.txt,.tsv" onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])} disabled={busy} />
        </div>
        <textarea rows={3} style={{ width: "100%", marginTop: 10 }} placeholder="Paste bank SMS here, e.g. Rs.450.00 debited from A/c XX4821 on 12-11-26 to VPA swiggy@axis ..."
          value={paste} onChange={(e) => setPaste(e.target.value)} />
        <div className="row" style={{ marginTop: 8 }}>
          <button className="btn sm" disabled={busy || !paste.trim()} onClick={doPaste}>{busy ? "Reading..." : "Import pasted SMS"}</button>
        </div>
        {report && (
          <div className="small" style={{ marginTop: 10, padding: 10, background: "#eef5f3", borderRadius: 8 }}>
            Read as <b>{report.format.toUpperCase()}</b>: {report.parsed} found, <b>{report.added}</b> added, {report.duplicates_skipped} duplicates skipped.
            Categorised by: {Object.entries(report.categorized_by).map(([k, v]) => `${SRC[k] || k} ${v}`).join(", ")}.
            {report.notes.map((n: string, i: number) => <div key={i} className="mute">{n}</div>)}
          </div>
        )}
      </div>

      <div className="card">
        <div className="row" style={{ marginBottom: 10 }}>
          <h2 style={{ marginRight: "auto", marginBottom: 0 }}>Transactions</h2>
          <select value={f.month} onChange={(e) => setF({ ...f, month: e.target.value })}>
            <option value="">All months</option>
            {summary.months.map((m: any) => <option key={m.month} value={m.month}>{monthName(m.month)}</option>)}
          </select>
          <select value={f.category} onChange={(e) => setF({ ...f, category: e.target.value })}>
            <option value="">All categories</option>{cats.map((c) => <option key={c}>{c}</option>)}
          </select>
          <input placeholder="Search" value={f.q} onChange={(e) => setF({ ...f, q: e.target.value })} style={{ width: 120 }} />
        </div>
        <p className="small mute" style={{ marginTop: 0 }}>Wrong category? Change it - the coach learns a rule for that merchant and applies it everywhere.</p>
        <div className="scroll-x">
          <table>
            <thead><tr><th>Date</th><th>Description</th><th>Category</th><th className="n">Amount</th></tr></thead>
            <tbody>
              {tx.map((t) => (
                <tr key={t.id}>
                  <td className="small" style={{ whiteSpace: "nowrap" }}>{dateFmt(t.date)}</td>
                  <td><div style={{ maxWidth: 280, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={t.description}>{t.description}</div>
                    <div className="small mute">{t.source.toUpperCase()} - categorised by {SRC[t.cat_source]}</div></td>
                  <td><select value={t.category} onChange={(e) => fix(t, e.target.value)}>{cats.map((c) => <option key={c}>{c}</option>)}</select></td>
                  <td className={"n " + (t.amount > 0 ? "pos" : "")}>{inr(t.amount, true)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {rules.length > 0 && (
        <div className="card">
          <h2>Rules you've taught the coach</h2>
          {rules.map((r) => (
            <div key={r.id} className="row small" style={{ marginBottom: 6 }}>
              <span style={{ flex: 1 }}><b>{r.pattern}</b> -&gt; {r.category} <span className="mute">(used {r.hits}x)</span></span>
              <button className="btn sm muted" onClick={async () => { await api("/rules/" + r.id, { method: "DELETE" }); load(); }}>Forget</button>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
