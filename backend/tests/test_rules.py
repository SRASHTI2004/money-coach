from app import categorize, db, ingest


def add(desc, amt=-300, date="2026-10-01"):
    return ingest.store("t", [{"date": date, "description": desc, "amount": amt, "source": "csv"}], "csv")


def test_builtin_categories():
    assert categorize.builtin_category("UPI-SWIGGY-order", -300) == "Dining"
    assert categorize.builtin_category("NEFT-ACME SALARY", 85000) == "Income"
    assert categorize.builtin_category("BIGBASKET", -900) == "Groceries"


def test_merchant_key_stable_across_sources():
    k = categorize.merchant_key
    assert k("UPI-SWIGGY-swiggy.order@axisbank-412398765") == k("SMS: Swiggy/313271411 (UPI)") == "swiggy"


def test_correction_learns_rule_and_applies_to_existing_and_future():
    for d in ("2026-08-03", "2026-09-03"):
        add("UPI-KAMAT UPAHAR-kamat@okaxis", date=d)
    tx = db.rows("SELECT * FROM transactions WHERE uid='t'")
    assert all(t["category"] == "Other" for t in tx)
    res = categorize.learn_rule("t", tx[0]["id"], "Dining")
    assert res["rule_created"] and res["also_updated"] == 1
    assert {t["category"] for t in db.rows("SELECT * FROM transactions WHERE uid='t'")} == {"Dining"}
    add("SMS: Kamat Upahar (UPI)", date="2026-10-03")  # future txn, different text, same merchant
    new = db.rows("SELECT * FROM transactions WHERE uid='t' AND date='2026-10-03'")[0]
    assert new["category"] == "Dining" and new["cat_source"] == "rule"


def test_explicit_fix_wins_for_that_transaction():
    add("UPI-RANDOM SHOP-x@ybl", date="2026-08-01")
    add("UPI-RANDOM SHOP-x@ybl", date="2026-09-01")
    a, b = db.rows("SELECT * FROM transactions WHERE uid='t' ORDER BY date")
    categorize.learn_rule("t", a["id"], "Shopping")
    categorize.learn_rule("t", b["id"], "Health")
    cats = {t["date"]: t["category"] for t in db.rows("SELECT * FROM transactions WHERE uid='t'")}
    assert cats["2026-09-01"] == "Health"


def test_duplicate_upload_skipped():
    r1 = add("UPI-ZOMATO-z@icici")
    r2 = add("UPI-ZOMATO-z@icici")
    assert r1["added"] == 1 and r2["added"] == 0 and r2["duplicates_skipped"] == 1
