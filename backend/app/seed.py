"""One-click demo: loads the bundled sample CSV, PDF and SMS through the real ingestion pipeline,
then seeds profile, goals, budgets and subscription usage."""
import os

from . import db, ingest, planner, timeline

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
        "emergency_fund": 180000, "emergency_target_months": 6, "emergency_monthly": 6000,
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
    # curated, back-dated history so the timeline tells the story of how the model evolved
    db.run("DELETE FROM events WHERE uid=?", (uid,))
    for d, kind, title, detail, why in [
        ("2026-08-01", "income", "Profile created: income ₹85,000/month", "", "Set up from your first bank statement."),
        ("2026-08-03", "goal", "New goal: Goa trip ₹60,000 by 31 Mar 2027", "₹7,500/month planned", "Added in Plan."),
        ("2026-08-20", "emergency", "Emergency fund target set to 6 months of essentials", "currently ₹1,80,000",
         "You wanted a safety net before bigger goals."),
        ("2026-09-10", "goal", "New goal: New laptop ₹90,000 by 31 Jul 2027", "₹6,000/month planned", "Added in Plan."),
        ("2026-10-05", "goal", "New goal: Japan vacation ₹2,50,000 by 31 Dec 2027", "₹5,000/month planned",
         "Added after the freelance income came in."),
        ("2026-10-12", "budget", "Dining budget set to ₹5,500", "", "Dining was your fastest-growing category."),
        ("2026-11-01", "import", "Imported 48 transactions from SMS", "November so far",
         "Pasted bank SMS re-computed your averages, subscriptions and nudges."),
    ]:
        timeline.log(uid, kind, title, detail, why, on=d)
    return results
