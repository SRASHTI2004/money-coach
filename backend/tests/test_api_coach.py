from fastapi.testclient import TestClient

from app.main import app

c = TestClient(app)
H = {"X-User": "t"}


def test_demo_load_then_dashboard():
    r = c.post("/api/demo/load", headers=H)
    assert r.status_code == 200 and sum(x["added"] for x in r.json()["loaded"]) > 150
    s = c.get("/api/summary", headers=H).json()
    assert not s["empty"] and len(s["months"]) == 4
    assert any(n["id"] == "budget:Dining" for n in c.get("/api/nudges", headers=H).json())
    subs = c.get("/api/subscriptions", headers=H).json()["items"]
    assert any(a["type"] == "price_change" for x in subs for a in x["alerts"])


def test_correction_endpoint_creates_rule():
    c.post("/api/demo/load", headers=H)
    tx = next(t for t in c.get("/api/transactions", headers=H).json() if t["category"] == "Dining")
    assert c.patch(f"/api/transactions/{tx['id']}", json={"category": "Shopping"}, headers=H).json()["rule_created"]
    assert c.get("/api/rules", headers=H).json()


def test_chat_proposal_requires_confirm():
    c.post("/api/demo/load", headers=H)
    r = c.post("/api/chat", json={"message": "what if i trim dining out by 20 percent please"}, headers=H).json()
    assert r["tools"][0]["tool"] == "run_what_if"
    prop = r["proposals"][0]
    assert c.get("/api/profile", headers=H).json()["budgets"]["Dining"] == 5500  # not applied yet
    c.post(f"/api/proposals/{prop['id']}/confirm", headers=H)
    assert c.get("/api/profile", headers=H).json()["budgets"]["Dining"] < 5500


def test_simulate_endpoint_and_review_fallback():
    c.post("/api/demo/load", headers=H)
    sim = c.post("/api/simulate", json={"adjustments": [{"category": "Dining", "percent": -30}]}, headers=H).json()
    assert sim["delta_free_cash"] > 0 and sim["summary"]
    rv = c.get("/api/review", headers=H).json()
    assert rv["narrative"]
