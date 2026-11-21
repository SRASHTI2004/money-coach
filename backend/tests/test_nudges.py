from app import ingest, nudges, planner


def test_budget_drift_math():
    assert nudges.budget_drift(6000, 5000, 10, 30)["level"] == "over"
    d = nudges.budget_drift(3000, 5000, 10, 30)  # 300/day -> 9000 projected
    assert d["level"] == "drift" and round(d["projected"]) == 9000
    assert nudges.budget_drift(1000, 5000, 10, 30) is None
    assert nudges.budget_drift(1000, 5000, 3, 30) is None  # too early in the month to extrapolate
    assert nudges.budget_drift(3000, 5000, 10, 30, prorate=False) is None  # fixed-date bills are not pro-rated


def test_generate_over_budget_nudge():
    rows = [("2026-10-01", "NEFT-ACME SALARY", 100000), ("2026-11-02", "NEFT-ACME SALARY", 100000)]
    rows += [(f"2026-10-{d:02d}", "UPI-SWIGGY-s@x", -100) for d in (3, 9)]
    rows += [(f"2026-11-{d:02d}", "UPI-SWIGGY-s@x", -1500) for d in (3, 8, 12, 15)]
    ingest.store("t", [{"date": d, "description": n, "amount": a, "source": "csv"} for d, n, a in rows], "csv")
    planner.save_profile("t", {"budgets": {"Dining": 5000}})
    n = next(x for x in nudges.generate("t") if x["id"] == "budget:Dining")
    assert n["severity"] == "alert" and "6,000" in n["body"]
