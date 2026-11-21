"""Deterministic parsers for messy Indian bank data: CSV, PDF text, transaction SMS.
Each returns a list of dicts {date, description, amount, source}; amount<0 = money out.
Gemini is only used (in ingest.py) when these parsers recover too little."""
import csv
import io
import re
from datetime import datetime

DATE_FORMATS = ["%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y", "%Y-%m-%d", "%d %b %Y", "%d-%b-%Y", "%d-%b-%y",
                "%d %b %y", "%d %B %Y", "%d.%m.%Y", "%d/%b/%Y", "%b %d %Y", "%d%b%Y", "%d%b%y"]
DATE_RE = r"(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}|\d{4}-\d{2}-\d{2}|\d{1,2}[ \-/]?[A-Za-z]{3,9}[ \-/,]*\d{2,4})"


def parse_date(s):
    s = (s or "").strip().replace(",", " ")
    s = re.sub(r"\s+", " ", s)
    for f in DATE_FORMATS:
        try:
            return datetime.strptime(s, f).date().isoformat()
        except ValueError:
            continue
    return None


def parse_amount(s):
    """'1,23,456.78' -> 123456.78 ; '(500)' / '-500' / '500 Dr' -> -500 ; '' -> None."""
    if s is None:
        return None
    t = str(s).strip()
    if not t or t in {"-", "--", "nan"}:
        return None
    neg = (t.startswith("(") and t.endswith(")")) or t.startswith("-") or bool(re.search(r"(?i)\bdr\.?$", t))
    t = re.sub(r"(?i)(rs\.?|inr|₹|cr\.?|dr\.?)", "", t)
    t = re.sub(r"[^\d.]", "", t)
    if not t or t == ".":
        return None
    try:
        v = float(t)
    except ValueError:
        return None
    return -v if neg else v


# ---------------------------------------------------------------- CSV
_HDR = {
    "date": ["date", "txn date", "transaction date", "value date", "posting date", "tran date"],
    "desc": ["description", "narration", "particulars", "details", "transaction details", "remarks",
             "transaction remarks", "merchant"],
    "debit": ["debit", "withdrawal", "withdrawals", "withdrawal amt.", "withdrawal amt", "dr", "debit amount",
              "paid out"],
    "credit": ["credit", "deposit", "deposits", "deposit amt.", "deposit amt", "cr", "credit amount", "paid in"],
    "amount": ["amount", "transaction amount", "amt"],
    "type": ["type", "dr/cr", "cr/dr", "transaction type"],
}


def _col(headers, key):
    hl = [h.strip().lower() for h in headers]
    for cand in _HDR[key]:
        if cand in hl:
            return hl.index(cand)
    if key in ("date", "desc"):
        for i, h in enumerate(hl):
            if any(c in h for c in _HDR[key] if len(c) > 3):
                return i
    return None


def parse_csv(text: str):
    text = text.lstrip("﻿")
    lines = text.splitlines()
    start = 0  # banks prepend account summaries; find the header row
    for i, ln in enumerate(lines[:40]):
        low = ln.lower()
        if "date" in low and any(k in low for k in ("desc", "narr", "partic", "detail", "remark")):
            start = i
            break
    body = "\n".join(lines[start:])
    try:
        dialect = csv.Sniffer().sniff(body[:2000], delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    reader = list(csv.reader(io.StringIO(body), dialect))
    if not reader:
        return []
    ci = {k: _col(reader[0], k) for k in _HDR}
    if ci["date"] is None or ci["desc"] is None:
        return []
    out = []
    for r in reader[1:]:
        g = lambda k: r[ci[k]] if ci[k] is not None and ci[k] < len(r) else None
        d = parse_date(g("date"))
        if not d:
            continue
        desc = re.sub(r"\s+", " ", g("desc") or "").strip()
        amt = None
        deb, cre = parse_amount(g("debit")), parse_amount(g("credit"))
        if deb or cre:
            amt = (abs(cre) if cre else 0) - (abs(deb) if deb else 0)
        elif ci["amount"] is not None:
            a = parse_amount(g("amount"))
            if a is not None:
                t = (g("type") or "").lower()
                raw = str(g("amount") or "")
                if "dr" in t or "debit" in t or re.search(r"(?i)dr\.?\s*$", raw):
                    a = -abs(a)
                elif "cr" in t or "credit" in t or re.search(r"(?i)cr\.?\s*$", raw):
                    a = abs(a)
                amt = a
        if amt:
            out.append({"date": d, "description": desc, "amount": round(amt, 2), "source": "csv"})
    return out


# ---------------------------------------------------------------- PDF text
_NUM = r"\(?-?[\d,]+\.\d{2}\)?(?:\s?(?:Dr|Cr)\.?)?"
OUT_WORDS = re.compile(r"(?i)\b(upi|pos|atm|nach|emi|debit|paid|purchase|withdrawal|bill|chq|imps|sent)\b")
IN_WORDS = re.compile(r"(?i)\b(salary|credit|interest|refund|cashback|received|deposit|reversal|dividend)\b")


def parse_pdf_text(text: str):
    """Statement lines like: 05/09/2026 UPI-SWIGGY-ORDER 412.00 85,200.50 (amount + running balance).
    Direction is inferred from the running balance when present, else Dr/Cr suffix, else keywords."""
    out, prev_bal = [], None
    for raw in text.splitlines():
        line = re.sub(r"\s+", " ", raw).strip()
        m = re.match(DATE_RE + r"\s+(.*)$", line)
        if not m:
            continue
        d = parse_date(m.group(1))
        rest = m.group(2)
        nums = list(re.finditer(_NUM, rest))
        if not d or not nums:
            continue
        desc = re.sub(r"\s+", " ", rest[:nums[0].start()]).strip(" -|")
        desc = re.sub(r"^" + DATE_RE + r"\s+", "", desc)  # leading value-date column
        vals = [parse_amount(n.group()) for n in nums]
        first = nums[0].group().strip()
        explicit = -1 if re.search(r"(?i)dr\.?$", first) else 1 if re.search(r"(?i)cr\.?$", first) else None
        if len(vals) >= 2:
            amt, bal = abs(vals[-2]), abs(vals[-1])
            sign = None
            if prev_bal is not None:
                if abs(prev_bal + amt - bal) < 0.02:
                    sign = 1
                elif abs(prev_bal - amt - bal) < 0.02:
                    sign = -1
            if sign is None:
                sign = explicit or (1 if IN_WORDS.search(desc) and not OUT_WORDS.search(desc) else -1)
            amt *= sign
            prev_bal = bal
        else:
            sign = explicit or (1 if IN_WORDS.search(desc) else -1)
            amt = abs(vals[0]) * sign
        if desc and amt:
            out.append({"date": d, "description": desc, "amount": round(amt, 2), "source": "pdf"})
    return out


def parse_pdf_bytes(data: bytes):
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(data))
    best, best_text = [], ""
    for mode in ("layout", "plain"):  # layout keeps table columns on one line
        try:
            text = "\n".join((p.extract_text(extraction_mode=mode) or "") for p in reader.pages)
        except Exception:
            continue
        rows = parse_pdf_text(text)
        if len(rows) > len(best) or not best_text:
            best, best_text = rows, text
        if len(rows) >= 3:
            break
    return best, best_text


# ---------------------------------------------------------------- SMS
_AMT = r"(?:rs\.?|inr|₹)\s*([\d,]+(?:\.\d{1,2})?)"
_DEBIT = re.compile(r"(?i)\b(debited|spent|withdrawn|sent|purchase|paid)\b")
_CREDIT = re.compile(r"(?i)\b(credited|received|deposited|refund(?:ed)?)\b")


def _sms_date(s):
    m = re.search(r"(?i)(?:on|dt|date)[:\s]*" + DATE_RE, s) or re.search(DATE_RE, s)
    return parse_date(m.group(1)) if m else None


def _sms_merchant(s):
    pats = [
        r"(?i)\bVPA\s+[^()@]*\(([^)]+)\)",
        r"(?i)\bVPA\s+([\w.\-]+@[\w]+)(?:\s*\(([^)]+)\))?",
        r"(?i)\bInfo[:\s]*(?:UPI[/-])?([A-Za-z][A-Za-z0-9 &*._\-/]{2,40}?)(?:\.|\s+Avl|\s+Bal|$)",
        r"(?i)\bat\s+([A-Za-z][A-Za-z0-9 &*._\-]{2,30}?)(?:\s+on\b|\s+Avl|\s+Bal|\.|,|$)",
        r"(?i)\bto\s+(?!your|a/c|ac\b)([A-Za-z][A-Za-z0-9 &*._\-]{2,30}?)(?:\s+on\b|\s+Ref|\s+UPI|\s+Avl|\.|,|$)",
        r"(?i)\bfrom\s+(?!a/c|ac\b)([A-Za-z][A-Za-z0-9 &*._\-]{2,30}?)(?:\s+on\b|\s+Ref|\s+UPI|\s+Avl|\.|,|$)",
        r"(?i)\bfor\s+([A-Za-z][A-Za-z0-9 &*._\-]{2,30}?)(?:\.|,|\s+via\b|$)",
        r"(?i)\bby\s+([A-Za-z][A-Za-z0-9 &*._\-]{2,30}?)(?:\.|,|$)",
    ]
    for p in pats:
        m = re.search(p, s)
        if m:
            name = (m.group(2) if m.lastindex and m.lastindex >= 2 and m.group(2) else m.group(1)).strip()
            return re.sub(r"/\d+$", "", name)
    return None


def parse_sms(text: str):
    """Messages separated by blank lines, else one per line. Returns (parsed, unparsed_chunks)."""
    chunks = [c.strip() for c in re.split(r"\n\s*\n", text.strip()) if c.strip()]
    if len(chunks) == 1:
        chunks = [c.strip() for c in text.strip().splitlines() if c.strip()]
    out, failed = [], []
    for ch in chunks:
        s = re.sub(r"\s+", " ", ch)
        am = re.search(_AMT, s, re.I)
        if not am:  # promos / OTP-only texts are noise; money-looking ones count as failures
            if re.search(r"(?i)\d+\.\d{2}|\brs\b|\binr\b", s) and re.search(r"(?i)debit|credit|spent|sent|paid|received", s):
                failed.append(ch)
            continue
        dm, cm = _DEBIT.search(s), _CREDIT.search(s)
        if re.search(r"(?i)\botp\b|do not share|will be (?:debited|credited)|is due|min(?:imum)? amount due|"
                     r"maintain sufficient", s):
            continue  # OTPs and upcoming-payment reminders are not transactions
        if dm and cm:
            is_debit = dm.start() < cm.start()
        elif dm or cm:
            is_debit = bool(dm)
        else:
            failed.append(ch)
            continue
        d = _sms_date(s)
        if not d:
            failed.append(ch)
            continue
        merch = _sms_merchant(s) or ("Credit" if not is_debit else "Unknown")
        amt = parse_amount(am.group(1))
        mode = " (UPI AutoPay)" if re.search(r"(?i)auto-?pay|mandate", s) else \
            " (UPI)" if re.search(r"(?i)\bupi\b|vpa", s) else ""
        out.append({"date": d, "description": f"SMS: {merch}{mode}", "amount": round(-amt if is_debit else amt, 2),
                    "source": "sms"})
    return out, failed


def detect_format(filename: str, data: bytes):
    n = (filename or "").lower()
    if n.endswith(".pdf") or data[:4] == b"%PDF":
        return "pdf"
    t = data[:3000].decode("utf-8", "ignore").lower()
    if n.endswith((".csv", ".tsv")) or ("date" in t and ("desc" in t or "narr" in t or "partic" in t)
                                         and t.count(",") + t.count("\t") > 5):
        return "csv"
    return "sms"


_MANDATE = re.compile(r"(?i)(?:auto-?pay|mandate).{0,40}?(?:rs\.?|inr|₹)\s*([\d,]+(?:\.\d{1,2})?)\s+for\s+"
                      r"([A-Za-z][A-Za-z0-9 &._\-]{1,30}?)\s+(?:will be|is scheduled to be|is due to be)\s+debited\s+on\s+"
                      + DATE_RE)


def parse_mandates(text: str):
    """Upcoming UPI AutoPay notices ('mandate of Rs.799 for Netflix will be debited on 05-12-26')."""
    out = []
    for ch in [c.strip() for c in re.split(r"\n", text) if c.strip()]:
        m = _MANDATE.search(re.sub(r"\s+", " ", ch))
        if m:
            d = parse_date(m.group(3))
            if d:
                out.append({"merchant_name": m.group(2).strip(), "amount": parse_amount(m.group(1)), "date": d})
    return out
