"""Input validation, upload limits, error shape, headers, rate limiting."""
from fastapi.testclient import TestClient

from app.api import common
from app.config import AI_REQUESTS_PER_MINUTE, MAX_UPLOAD_BYTES
from app.main import app

c = TestClient(app)
H = {"X-User": "t"}


def test_upload_rejects_wrong_type_size_and_fake_pdf():
    r = c.post("/api/upload", files={"file": ("evil.exe", b"MZ")}, headers=H)
    assert r.status_code == 415 and "Unsupported" in r.json()["detail"]
    r = c.post("/api/upload", files={"file": ("big.csv", b"x" * (MAX_UPLOAD_BYTES + 10))}, headers=H)
    assert r.status_code == 413
    r = c.post("/api/upload", files={"file": ("fake.pdf", b"not a pdf")}, headers=H)
    assert r.status_code == 415


def test_validation_errors_are_one_readable_shape():
    r = c.post("/api/goals", json={"name": "", "target_amount": -5, "target_date": "not-a-date"}, headers=H)
    assert r.status_code == 422 and isinstance(r.json()["detail"], str) and r.json()["detail"].startswith("Invalid input")
    r = c.put("/api/profile", json={"budgets": {"Nonsense": 5}}, headers=H)
    assert r.status_code == 422
    r = c.put("/api/profile", json={"monthly_income": -1}, headers=H)
    assert r.status_code == 422
    assert c.post("/api/chat", json={"message": "   "}, headers=H).status_code == 422
    assert c.post("/api/chat", json={"message": "x" * 5000}, headers=H).status_code == 422
    assert c.post("/api/life-events", json={"events": [{"type": "hack"}]}, headers=H).status_code == 422
    assert c.post("/api/simulate", json={"adjustments": [{"category": "Dining", "percent": -500}]}, headers=H).status_code == 422


def test_http_errors_use_detail_shape():
    r = c.patch("/api/transactions/999999", json={"category": "Dining"}, headers=H)
    assert r.status_code == 404 and r.json() == {"detail": "Transaction not found"}
    assert c.patch("/api/transactions/1", json={"category": "Nope"}, headers=H).status_code == 400


def test_security_headers_present():
    r = c.get("/api/health")
    assert r.headers["x-content-type-options"] == "nosniff" and r.headers["x-frame-options"] == "DENY"
    assert "default-src 'self'" in r.headers["content-security-policy"]


def test_uid_header_is_sanitised():
    assert common.user_id("../../etc/passwd") == "etcpasswd"
    assert common.user_id(None) == "demo" and len(common.user_id("a" * 500)) == 64


def test_ai_endpoints_are_rate_limited():
    h = {"X-User": "rate-test"}
    codes = [c.post("/api/chat", json={"message": "hi"}, headers=h).status_code for _ in range(AI_REQUESTS_PER_MINUTE + 3)]
    assert 429 in codes and codes[0] == 200
    common._hits.pop("rate-test", None)


def test_static_path_traversal_is_blocked():
    r = c.get("/..%2f..%2fpyproject.toml")
    assert r.status_code in (200, 404) and "ruff" not in r.text


def test_health_endpoint_is_lightweight_and_supports_head():
    r = c.get("/api/health")
    assert r.status_code == 200 and r.json()["ok"] is True and "disclaimer" in r.json()
    assert c.head("/api/health").status_code == 200
