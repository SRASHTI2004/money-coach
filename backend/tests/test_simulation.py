from app import db, ingest, planner


def seed():
    rows = []
    for m in (8, 9, 10):
        rows += [(f"2026-{m:02d}-01", "NEFT-ACME SALARY", 100000), (f"2026-{m:02d}-05", "UPI-RENT-LANDLORD", -30000),
                 (f"2026-{m:02d}-10", "UPI-SWIGGY-s@x", -10000), (f"2026-{m:02d}-11", "BIGBASKET", -10000)]
    ingest.store("t", [{"date": d, "description": n, "amount": a, "source": "csv"} for d, n, a in rows], "csv")
    db.run("INSERT INTO goals(uid,name,target_amount,saved,target_date,monthly_contrib) "
           "VALUES('t','Trip',100000,0,'2027-06-30',10000)")
    planner.save_profile("t", {"monthly_income": 100000, "emergency_fund": 0, "emergency_monthly": 0,
                               "emergency_target_months": 0})


def test_baseline_math():
    seed()
    s = planner.snapshot("t")
    assert s["income"] == 100000 and s["spend"] == 50000 and s["free_cash"] == 50000


def test_cut_dining_30pct():
    seed()
    sim = planner.simulate("t", [{"category": "Dining", "percent": -30}])
    assert sim["after"]["by_cat"]["Dining"] == 7000
    assert sim["delta_free_cash"] == 3000 and sim["delta_yearly"] == 36000


def test_rent_increase_reduces_free_cash():
    seed()
    sim = planner.simulate("t", [{"category": "Rent", "amount": 5000}])
    assert sim["delta_free_cash"] == -5000 and sim["after"]["free_cash"] == 45000


def test_income_change_and_new_expense():
    seed()
    sim = planner.simulate("t", [{"category": "Income", "percent": -10}, {"category": "Car loan", "amount": 8000}])
    assert sim["after"]["income"] == 90000 and sim["after"]["free_cash"] == 90000 - 58000


def test_goal_slips_when_free_cash_drops():
    seed()
    sim = planner.simulate("t", [{"category": "Rent", "amount": 45000}])  # only 5k free vs 10k planned
    g = sim["goal_changes"][0]
    assert sim["after"]["goals"]["items"][0]["contribution"] == 5000
    assert g["after_on_track"] is False


def test_surplus_routed_to_goal_that_is_behind():
    seed()
    db.run("UPDATE goals SET monthly_contrib=2000 WHERE uid='t'")
    g = planner.snapshot("t")["goals"]["items"][0]
    assert g["contribution"] > 2000  # leftover free cash lifts the lagging goal
    assert g["contribution"] <= g["required_monthly"] + 0.01


def test_cut_never_negative():
    seed()
    assert planner.snapshot("t", [{"category": "Dining", "percent": -150}])["by_cat"]["Dining"] == 0
