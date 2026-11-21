"""Ingestion pipeline: detect format -> deterministic parse -> Gemini rescue for what regex missed -> categorise -> store."""
import hashlib

from . import categorize, db, gemini, parsing


def _tx_hash(t):
    return hashlib.sha1(f"{t['date']}|{t['amount']:.2f}|{t['description'].lower()}".encode()).hexdigest()


def ai_extract(text: str, kind: str, file_hash: str):
    """Last-resort: ask Gemini to turn messy text into transactions. Cached by file hash."""
    prompt = (f"Extract every bank transaction from this {kind} text from an Indian bank. Return a JSON array of "
              'objects {"date":"YYYY-MM-DD","description":str,"amount":number} where amount is NEGATIVE for money '
              "out (debit/spent/paid) and POSITIVE for money in. Skip balances, headers, OTPs and ads.\n\n"
              + text[:12000])
    res = gemini.generate(prompt, system="You are a precise bank statement parser. JSON only.", json_mode=True,
                          cache_key=f"extract|{file_hash}")
    out = []
    if isinstance(res, list):
        for r in res:
            try:
                d = parsing.parse_date(str(r["date"])) or str(r["date"])
                out.append({"date": d, "description": str(r["description"]), "amount": round(float(r["amount"]), 2),
                            "source": kind})
            except (KeyError, ValueError, TypeError):
                continue
    return out


def ingest(uid, filename: str, data: bytes, force_kind=None):
    kind = force_kind or parsing.detect_format(filename, data)
    fh = gemini.file_hash(data)
    notes, parsed, text = [], [], ""
    if kind == "pdf":
        try:
            parsed, text = parsing.parse_pdf_bytes(data)
        except Exception as e:
            notes.append(f"PDF read error: {e}")
    else:
        text = data.decode("utf-8", "ignore")
        if kind == "csv":
            parsed = parsing.parse_csv(text)
        else:
            parsed, failed = parsing.parse_sms(text)
            if failed:
                extra = ai_extract("\n\n".join(failed), "sms", fh)
                if extra:
                    notes.append(f"AI recovered {len(extra)} SMS the pattern parser could not read")
                    parsed += extra
                else:
                    notes.append(f"{len(failed)} message(s) could not be read (AI fallback unavailable or found nothing)")
    used_ai_parse = False
    if len(parsed) < 3 and text.strip() and kind in ("pdf", "csv"):
        extra = ai_extract(text, kind, fh)
        if extra:
            parsed, used_ai_parse = extra, True
            notes.append("Layout was unusual - Gemini extracted the transactions")
        elif not parsed:
            notes.append("Could not parse any transactions; AI fallback unavailable")
    return store(uid, parsed, kind, notes, used_ai_parse)


def store(uid, parsed, kind, notes=None, used_ai_parse=False):
    notes = notes or []
    seen, items = set(), []
    for t in parsed:
        t["hash"] = _tx_hash(t)
        if t["hash"] in seen:
            t["hash"] += f"#{len(seen)}"  # genuine same-day duplicates (two identical chai payments)
        seen.add(t["hash"])
        items.append(t)
    existing = {r["hash"] for r in db.rows("SELECT hash FROM transactions WHERE uid=?", (uid,))}
    new = [t for t in items if t["hash"] not in existing]
    categorize.categorize_batch(uid, new)
    for t in new:
        db.run("INSERT OR IGNORE INTO transactions(uid,date,description,amount,merchant,category,cat_source,source,hash)"
               " VALUES(?,?,?,?,?,?,?,?,?)",
               (uid, t["date"], t["description"], t["amount"], t["merchant"], t["category"], t["cat_source"],
                t.get("source", kind), t["hash"]))
    by_src = {}
    for t in new:
        by_src[t["cat_source"]] = by_src.get(t["cat_source"], 0) + 1
    return {"format": kind, "parsed": len(parsed), "added": len(new), "duplicates_skipped": len(items) - len(new),
            "categorized_by": by_src, "notes": notes, "ai_parse": used_ai_parse}
