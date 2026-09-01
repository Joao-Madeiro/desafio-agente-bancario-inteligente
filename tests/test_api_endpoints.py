import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_health_check_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"

def test_clients_endpoint():
    response = client.get("/api/clients")
    assert response.status_code == 200
    data = response.json()
    assert "clients" in data
    assert len(data["clients"]) > 0

def test_requests_endpoint():
    response = client.get("/api/requests")
    assert response.status_code == 200
    data = response.json()
    assert "requests" in data

def test_score_rules_endpoint():
    response = client.get("/api/score-rules")
    assert response.status_code == 200
    data = response.json()
    assert "rules" in data
    assert len(data["rules"]) == 4

def test_exchange_rates_endpoint():
    response = client.get("/api/exchange-rates")
    assert response.status_code == 200
    data = response.json()
    assert "quotes" in data
    assert "USD" in data["quotes"]

def test_reset_endpoint():
    response = client.post("/api/reset")
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
