from fastapi.testclient import TestClient

from backend.main import app


def test_health_dashboard_and_frontend_routes() -> None:
    with TestClient(app) as client:
        assert client.get("/api/health").json() == {"status": "ok"}

        response = client.get("/api/dashboard?days=30")
        assert response.status_code == 200
        data = response.json()
        assert data["kpis"]["revenue"] > 0
        assert len(data["trend"]) == 30
        assert len(data["forecast"]) == 7
        quarter = client.get("/api/dashboard?days=90").json()
        assert quarter["kpis"]["revenue_change_pct"] is not None
        assert quarter["kpis"]["previous_revenue"] > 0
        assert client.get("/api/dashboard?days=30").json()["anomalies"]
        assert client.get("/").status_code == 200


def test_dashboard_rejects_unsupported_periods() -> None:
    with TestClient(app) as client:
        assert client.get("/api/dashboard?days=2").status_code == 400


def test_question_rejects_whitespace_only_input() -> None:
    with TestClient(app) as client:
        response = client.post("/api/ai/ask", json={"question": "   "})
        assert response.status_code == 422


def test_ai_summary_uses_selected_dashboard_period(monkeypatch) -> None:
    observed_periods = []

    def explain(dashboard, question=None):
        observed_periods.append(dashboard["period_days"])
        return "Summary"

    monkeypatch.setattr("backend.main.explain_dashboard", explain)
    with TestClient(app) as client:
        response = client.post("/api/ai/summary?days=7")

    assert response.status_code == 200
    assert observed_periods == [7]
