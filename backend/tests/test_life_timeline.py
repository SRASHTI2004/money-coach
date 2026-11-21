from app import db, ingest, lifeevents, parsing, planner, seed, timeline


def basic():
    rows = []
    for m in (8, 9, 10):
        rows += [(f"2026-{m:02d}-01", "NEFT-ACME SALARY", 100000), (f"2026-{m:02d}-05", "UPI-RENT-LANDLORD", -30000),
                 (f"2026-{m:02d}-10", "UPI-SWIGGY-s@x", -10000), (f"2026-{m:02d}-11", "BIGBASKET", -10000)]
    ingest.store("t", [{"date": d, "description": n, "amount": a, "source": "csv"} for d, n, a in rows], "csv")
    db.run("INSERT INTO goals(uid,name,target_amount,saved,target_date,monthly_contrib) "
           "VALUES('t','Trip',100000,0,'2027-12-31',10000)")
    planner.save_profile("t", {"monthly_income": 100000, "emergency_fund": 150000, "emergency_monthly": 10000,
                               "emergency_target_months": 6})


def test_no_events_matches_baseline():
    basic()
    sim = lifeevents.simulate("t", [])
    assert sim["after"]["ef"] == sim["before"]["ef"] and sim["goals"][0]["shift_months"] == 0


def test_job_loss_drains_emergency_fund_and_delays_goal():
    basic()
    sim = lifeevents.simulate("t", [{"type": "job_loss", "months": 3, "start": 1}])
    a = sim["after"]
    # spend 50k + (SIP 0) per month with zero income: fund falls 150k -> 0 in 3 months
    assert a["ef"][3] == 0 and a["ef_depleted_month"] == 3
    assert sim["goals"][0]["shift_months"] and sim["goals"][0]["shift_months"] >= 3


def test_salary_hike_pulls_goal_forward_and_never_negative_fund():
    basic()
    sim = lifeevents.simulate("t", [{"type": "salary_change", "percent": 20, "start": 1}])
    assert sim["goals"][0]["shift_months"] <= 0
    assert min(sim["after"]["ef"]) >= 0


def test_events_combine():
    basic()
    one = lifeevents.simulate("t", [{"type": "rent_increase", "amount": 10000}])
    two = lifeevents.simulate("t", [{"type": "rent_increase", "amount": 10000},
                                    {"type": "new_emi", "amount": 15000, "months": 12}])
    assert two["after"]["free"][0] == one["after"]["free"][0] - 15000
    assert two["after"]["free"][12] == one["after"]["free"][12]  # EMI over after 12 months


def test_autopay_sms_and_mandate_notice():
    msg = ("UPI Mandate: Rs.119.00 debited from A/c XX4821 on 07-11-26 for Spotify India via UPI AutoPay. Ref 1.\n\n"
           "Your UPI AutoPay mandate of Rs.349.00 for Hotstar will be debited on 07-12-26. Maintain balance.")
    rows, _ = parsing.parse_sms(msg)
    assert len(rows) == 1 and "AutoPay" in rows[0]["description"] and rows[0]["amount"] == -119
    m = parsing.parse_mandates(msg)
    assert m == [{"merchant_name": "Hotstar", "amount": 349.0, "date": "2026-12-07"}]


def test_timeline_has_logged_and_detected_events():
    seed.load_demo("t")
    kinds = {e["kind"] for e in timeline.build("t")}
    titles = " ".join(e["title"] for e in timeline.build("t"))
    assert {"goal", "price", "cancelled", "income"} <= kinds
    assert "Audible" in titles and "Netflix" in titles


def test_autopay_marks_subscription_and_mandate_nudge():
    from app import analytics as an
    from app import nudges
    seed.load_demo("t")
    subs = {s["merchant"]: s for s in an.detect_recurring("t")}
    assert subs["spotify"]["autopay"] is True
    assert any(n["id"] == "mandate:hotstar" for n in nudges.generate("t"))
