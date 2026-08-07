from fastapi.testclient import TestClient

from trading_system.api import app

client = TestClient(app)


def test_health() -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_backtest_endpoint() -> None:
    response = client.post(
        "/backtests",
        json={
            "strategy": "sma_crossover",
            "years": 1,
            "parameters": {"short_window": 10, "long_window": 30},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["strategy"] == "sma_crossover"
    assert "metrics" in payload
