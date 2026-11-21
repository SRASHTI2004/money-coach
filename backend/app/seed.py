"""One-click demo: loads the bundled sample CSV, PDF and SMS through the real ingestion pipeline,
then seeds profile, goals, budgets and subscription usage."""
import os

from . import db, ingest, planner

SAMPLES = os.environ.get("SAMPLES_DIR", os.path.join(os.path.dirname(__file__), "..", "..", "samples"))


def load_demo(uid):
    db.wipe_user(uid)
    results = []
    for fn in ("hdfc_aug_sep_2026.csv", "icici_oct_2026_statement.pdf", "sms_nov_2026.txt"):
        with open(os.path.join(SAMPLES, fn), "rb") as f:
            results.append({"file": fn, **ingest.ingest(uid, fn, f.read())})
    planner.save_profile(uid, {
        "monthly_income": 85000,
        "fixed_costs": [{"name": "Rent", "amount": 22000}, {"name": "Laptop EMI", "amount": 3500},
                        {"name": "Broadband + mobile", "amount": 1578}, {"name": "LIC premium", "amount": 1250}],
        "emergency_fund": 120000, "emergency_target_months": 6, "emergency_monthly": 6000,
        "budgets": {"Dining": 5500, "Groceries": 10000, "Transport": 3500, "Shopping": 4000,
                    "Entertainment": 1000, "Subscriptions": 3500},
    })
    for name, target, saved, tdate, contrib in [
        ("Goa trip", 60000, 30000, "2027-03-31", 7500),
        ("New laptop", 90000, 45000, "2027-07-31", 6000),
        ("Japan vacation", 250000, 40000, "2027-12-31", 5000)]:
        db.run("INSERT INTO goals(uid,name,target_amount,saved,target_date,monthly_contrib) VALUES(?,?,?,?,?,?)",
               (uid, name, target, saved, tdate, contrib))
    for merchant, last in [("cultfit", "2026-09-02"), ("hotstar", "2026-08-20"), ("netflix", "2026-11-18"),
                           ("spotify", "2026-11-20"), ("icloud", "2026-11-21")]:
        db.run("INSERT OR REPLACE INTO sub_meta(uid,merchant,last_used) VALUES(?,?,?)", (uid, merchant, last))
    return results
