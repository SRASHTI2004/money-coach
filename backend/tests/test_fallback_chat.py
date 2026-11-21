from app import coach, seed


def test_fallback_rent_increase_without_currency_symbol():
    seed.load_demo("t")
    r = coach.chat("t", "what if my rent goes up by 3000?")
    assert [t["tool"] for t in r["tools"]] == ["run_what_if"]
    assert "-₹3,000" in r["reply"] or "₹3,000" in r["reply"]


def test_fallback_income_drop_percent():
    seed.load_demo("t")
    r = coach.chat("t", "what if my income drops 10%?")
    assert r["tools"][0]["tool"] == "run_what_if" and "-" in r["reply"]
