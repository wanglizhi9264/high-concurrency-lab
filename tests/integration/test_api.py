from fastapi.testclient import TestClient

from concurrency_lab.main import create_app


def test_real_readiness():
    with TestClient(create_app()) as client:
        assert client.get("/health/live").status_code == 200
        assert client.get("/health/ready").json() == {
            "status": "ready",
            "checks": {"mysql": "ok", "redis": "ok"},
        }
