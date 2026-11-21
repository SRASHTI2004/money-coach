import { useEffect, useRef, useState } from "react";
import { api, CAT_SRC, dateFmt, errMsg, inr, monthName, SRC_LABEL } from "./api";
import { type Ctx, Empty, ErrorBox, Loading, useApi } from "./parts";
import type { CorrectionResult, ImportReport, Rule, Tx } from "./types";

const MAX_ROWS = 300;
const SAMPLE_SMS = [
  "Rs.380.00 debited from A/c XX4821 on 22-11-26 to VPA swiggy@axisbank (Swiggy) Ref 331204455671. -HDFC Bank",
  "Sent Rs.215.00 from HDFC Bank A/c *4821 to Uber India on 22Nov26 UPI Ref 331299120044",
  "UPI Mandate: Rs.119.00 debited from A/c XX4821 on 22-11-26 for Spotify India via UPI AutoPay. Ref 331200771120. -HDFC Bank",
  "Rs.5,500.00 credited to A/c XX4821 on 22-11-26 by NEFT-FREELANCE-DESIGN CLIENT. Avl Bal Rs.61,200.",
].join("\n\n");
const NON_BUDGET_SOURCES = ["", "sms", "pdf", "csv"];

export default function Transactions({ refresh, toast, summary }: Ctx) {
  const [f, setF] = useState({ month: "", category: "", q: "" });
  const [srcF, setSrcF] = useState("");
  const [paste, setPaste] = useState("");
  const [busy, setBusy] = useState(false);
  const [report, setReport] = useState<ImportReport | null>(null);
  const file = useRef<HTMLInputElement>(null);
  const qs = new URLSearchParams({ limit: String(MAX_ROWS), ...Object.fromEntries(Object.entries(f).filter(([, v]) => v)) }).toString();
  const txs = useApi<Tx[]>("/transactions?" + qs, summary);
  const rules = useApi<Rule[]>("/rules", summary);
  const [cats, setCats] = useState<string[]>([]);
  useEffect(() => { api<string[]>("/categories").then(setCats).catch(() => setCats([])); }, []);

  const upload = async (fl: File) => {
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("file", fl);
      setReport(await api<ImportReport>("/upload", { form: fd }));
      await refresh();
    } catch (e) { toast(errMsg(e)); } finally { setBusy(false); if (file.current) file.current.value = ""; }
  };
  const doPaste = async () => {
    setBusy(true);
    try {
      setReport(await api<ImportReport>("/paste", { body: { text: paste } }));
      setPaste("");
      await refresh();
    } catch (e) { toast(errMsg(e)); } finally { setBusy(false); }
  };
  const fix = async (t: Tx, category: string) => {
    try {
      const r = await api<CorrectionResult>("/transactions/" + t.id, { method: "PATCH", body: { category } });
      toast(r.rule_created
        ? `"${r.merchant}" -> ${category}.` + (r.also_updated ? ` Also re-labelled ${r.also_updated} other transaction(s).` : "") + " Future ones will follow automatically."
        : "Updated.", r.rule_created ? "learn" : undefined);
      await refresh();
    } catch (e) { toast(errMsg(e)); }
  };

  const list = (txs.data ?? []).filter((t) => !srcF || t.source === srcF);
  return (
    <>
      <section className="card" aria-labelledby="add-h">
        <h2 id="add-h">Add transactions</h2>
        <p className="small mute" style={{ marginTop: -6 }}>Bank CSV or PDF statements (up to 8 MB), or paste bank SMS. Messy layouts are fine - unreadable parts go to Gemini.</p>
        <label className="f">Choose a statement file (.csv, .pdf, .txt)
          <input ref={file} type="file" accept=".csv,.pdf,.txt,.tsv" onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])} disabled={busy} />
        </label>
        <label className="f" style={{ marginTop: 10 }}>Or paste bank / UPI SMS
          <textarea rows={3} placeholder="e.g. Rs.450.00 debited from A/c XX4821 on 12-11-26 to VPA swiggy@axis ..." value={paste} onChange={(e) => setPaste(e.target.value)} />
        </label>
        <div className="row" style={{ marginTop: 8 }}>
          <button className="btn sm" disabled={busy || !paste.trim()} onClick={doPaste}>{busy ? "Reading..." : "Import pasted SMS"}</button>
          <button className="btn sm ghost" onClick={() => setPaste(SAMPLE_SMS)}>Fill sample UPI SMS</button>
        </div>
        {report && (
          <div className="small ai-note" style={{ marginTop: 10 }} role="status">
            Read as <b>{report.format.toUpperCase()}</b>: {report.parsed} found, <b>{report.added}</b> added, {report.duplicates_skipped} duplicates skipped.
            Categorised by: {Object.entries(report.categorized_by).map(([k, v]) => `${CAT_SRC[k] || k} ${v}`).join(", ") || "-"}.
            {report.notes.map((n, i) => <div key={i} className="mute">{n}</div>)}
          </div>
        )}
      </section>

      <section className="card" aria-labelledby="tx-h">
        <div className="row" style={{ marginBottom: 10 }}>
          <h2 id="tx-h" style={{ marginRight: "auto", marginBottom: 0 }}>Transactions</h2>
          <select aria-label="Filter by month" value={f.month} onChange={(e) => setF({ ...f, month: e.target.value })}>
            <option value="">All months</option>
            {summary.months.map((m) => <option key={m.month} value={m.month}>{monthName(m.month)}</option>)}
          </select>
          <select aria-label="Filter by category" value={f.category} onChange={(e) => setF({ ...f, category: e.target.value })}>
            <option value="">All categories</option>{cats.map((c) => <option key={c}>{c}</option>)}
          </select>
          <input aria-label="Search transactions" placeholder="Search" value={f.q} onChange={(e) => setF({ ...f, q: e.target.value })} style={{ width: 120 }} />
        </div>
        <div className="chips" role="group" aria-label="Filter by source">
          {NON_BUDGET_SOURCES.map((k) => {
            const n = k ? (txs.data ?? []).filter((t) => t.source === k).length : (txs.data ?? []).length;
            return <button key={k} className={"chip" + (srcF === k ? " on" : "")} aria-pressed={srcF === k} onClick={() => setSrcF(k)}>{k ? `Parsed from ${SRC_LABEL[k]}` : "All sources"} <b>{n}</b></button>;
          })}
        </div>
        <p className="small mute" style={{ marginTop: 0 }}>Wrong category? Change it - the coach learns a rule for that merchant and applies it everywhere.</p>
        {txs.loading && !txs.data && <Loading what="Loading transactions" />}
        {txs.error && <ErrorBox message={txs.error} onRetry={txs.reload} />}
        {txs.data && list.length === 0 && <Empty title="No transactions match">Try clearing the filters, or import a statement above.</Empty>}
        {list.length > 0 && (
          <div className="scroll-x">
            <table>
              <thead><tr><th scope="col">Date</th><th scope="col">Description</th><th scope="col">Category</th><th scope="col" className="n">Amount</th></tr></thead>
              <tbody>
                {list.map((t) => (
                  <tr key={t.id}>
                    <td className="small" style={{ whiteSpace: "nowrap" }}>{dateFmt(t.date)}</td>
                    <td><div className="clip" title={t.description}>{t.description}</div>
                      <div className="small mute"><span className={"src src-" + t.source}>{SRC_LABEL[t.source]}</span> categorised by {CAT_SRC[t.cat_source]}</div></td>
                    <td><select aria-label={`Category for ${t.description}`} value={t.category} onChange={(e) => fix(t, e.target.value)}>{cats.map((c) => <option key={c}>{c}</option>)}</select></td>
                    <td className={"n " + (t.amount > 0 ? "pos" : "")}>{inr(t.amount, true)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {(rules.data ?? []).length > 0 && (
        <section className="card" aria-labelledby="rules-h">
          <h2 id="rules-h">Rules you&apos;ve taught the coach</h2>
          {(rules.data ?? []).map((r) => (
            <div key={r.id} className="row small" style={{ marginBottom: 6 }}>
              <span style={{ flex: 1 }}><b>{r.pattern}</b> &rarr; {r.category} <span className="mute">(used {r.hits}x)</span></span>
              <button className="btn sm muted" onClick={async () => { await api("/rules/" + r.id, { method: "DELETE" }); rules.reload(); }}>Forget</button>
            </div>
          ))}
        </section>
      )}
    </>
  );
}
