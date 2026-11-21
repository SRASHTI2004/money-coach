"""The bundled gemini_cache.json makes the demo instant and AI-quality even with the AI disabled (tests run DISABLE_AI=1)."""
from fastapi.testclient import TestClient

from app.main import app

c = TestClient(app)
H = {"X-User": "t"}


def test_demo_categorisation_and_review_come_from_cache():
    r = c.post("/api/demo/load", headers=H).json()["loaded"]
    assert sum(x["categorized_by"].get("ai", 0) for x in r) >= 7  # unknown merchants labelled by (cached) Gemini
    assert not [t for t in c.get("/api/transactions", headers=H).json() if t["category"] == "Other"]
    rv = c.get("/api/review", headers=H).json()
    assert rv["ai"] is True and len(rv["narrative"]) > 200


def test_cached_coach_answer_with_tool_steps():
    c.post("/api/demo/load", headers=H)
    r = c.post("/api/chat", json={"message": "What if I cut dining out by 30%?"}, headers=H).json()
    assert r["cached"] and r["ai"] and r["tools"][0]["tool"] == "run_what_if" and r["tools"][0]["result"]


def test_cached_proposal_still_needs_confirm():
    c.post("/api/demo/load", headers=H)
    r = c.post("/api/chat", json={"message": "Set my dining budget to 4000 and explain why"}, headers=H).json()
    assert r["cached"] and len(r["proposals"]) == 1
    assert c.get("/api/profile", headers=H).json()["budgets"]["Dining"] == 5500
    c.post(f"/api/proposals/{r['proposals'][0]['id']}/confirm", headers=H)
    assert c.get("/api/profile", headers=H).json()["budgets"]["Dining"] == 4000
    kinds = [e["title"] for e in c.get("/api/timeline", headers=H).json()]
    assert any("Dining budget" in k and "4,000" in k for k in kinds)  # the timeline records the confirmed change


def test_guardrail_not_cached_and_never_names_product():
    c.post("/api/demo/load", headers=H)
    r = c.post("/api/chat", json={"message": "Which mutual fund should I buy?"}, headers=H).json()
    assert r["guardrail"] and r["tools"] == [] and not r["cached"]
