from app import analytics as an
from app import db, ingest


def put(rows):
    ingest.store("t", [{"date": d, "description": n, "amount": a, "source": "csv"} for d, n, a in rows], "csv")


def test_detects_monthly_and_price_change():
    put([("2026-08-05", "UPI-NETFLIX-n@icici", -649), ("2026-09-05", "UPI-NETFLIX-n@icici", -649),
         ("2026-10-05", "UPI-NETFLIX-n@icici", -649), ("2026-11-05", "UPI-NETFLIX-n@icici", -799)])
    n = next(s for s in an.detect_recurring("t") if s["merchant"] == "netflix")
    assert n["cadence"] == "monthly" and n["amount"] == 799
    assert n["price_change"]["old"] == 649 and n["price_change"]["pct"] == 23.1
    assert any(a["type"] == "price_change" for a in n["alerts"])


def test_irregular_merchant_not_recurring():
    put([("2026-08-02", "UPI-SWIGGY-s@x", -300), ("2026-08-05", "UPI-SWIGGY-s@x", -420),
         ("2026-08-19", "UPI-SWIGGY-s@x", -250), ("2026-09-09", "UPI-SWIGGY-s@x", -500)])
    assert not [s for s in an.detect_recurring("t") if s["merchant"] == "swiggy"]


def test_variable_bill_is_recurring_but_no_price_alert():
    put([("2026-08-06", "UPI-BESCOM-ELECTRICITY BILL", -1700), ("2026-09-06", "UPI-BESCOM-ELECTRICITY BILL", -2300),
         ("2026-10-06", "UPI-BESCOM-ELECTRICITY BILL", -1900), ("2026-11-06", "UPI-BESCOM-ELECTRICITY BILL", -2400)])
    b = next(s for s in an.detect_recurring("t") if s["merchant"] == "bescom")
    assert not b["fixed_amount"] and b["price_change"] is None


def test_unused_alert_from_last_used():
    put([(f"2026-{m:02d}-12", "UPI-CULT.FIT GYM MEMBERSHIP", -1499) for m in (8, 9, 10, 11)])
    db.run("INSERT INTO sub_meta(uid,merchant,last_used) VALUES('t','cultfit','2026-09-02')")
    g = next(s for s in an.detect_recurring("t") if s["merchant"] == "cultfit")
    assert any(a["type"] == "unused" for a in g["alerts"])


def test_overlap_alert_two_streaming():
    rows = []
    for m in (8, 9, 10, 11):
        rows += [(f"2026-{m:02d}-05", "UPI-NETFLIX-n@i", -649), (f"2026-{m:02d}-07", "UPI-HOTSTAR-h@i", -299)]
    put(rows)
    subs = an.detect_recurring("t")
    assert all(any(a["type"] == "overlap" for a in s["alerts"]) for s in subs if s["merchant"] in ("netflix", "hotstar"))


def test_inr_format():
    assert an.inr(1234567) == "₹12,34,567" and an.inr(950) == "₹950" and an.inr(-100000) == "-₹1,00,000"
