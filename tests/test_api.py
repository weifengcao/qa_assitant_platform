from app.api import app
from fastapi.testclient import TestClient


def _headers(roles: str = "Viewer") -> dict[str, str]:
    return {
        "X-Org-Id": "demo",
        "X-User-Id": "u1",
        "X-Roles": roles,
    }


def test_health_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert "version" in payload
    assert "build_sha" in payload


def test_packs_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/packs")
    assert response.status_code == 200
    packs = response.json()["packs"]
    assert any(pack["pack_id"] == "sample_service" for pack in packs)


def test_chat_how_to_returns_citations() -> None:
    client = TestClient(app)
    response = client.post(
        "/chat",
        headers=_headers(),
        json={"message": "How do I rotate an API key?"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["trace_id"]
    assert payload["citations"]


def test_chat_stats_returns_action() -> None:
    client = TestClient(app)
    response = client.post(
        "/chat",
        headers=_headers(),
        json={"message": "What is the request volume last 24h?"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["actions"]
    assert payload["actions"][0]["tool"] == "sample.stats.request_volume_24h"


def test_chat_deny_pattern_returns_warning() -> None:
    client = TestClient(app)
    response = client.post(
        "/chat",
        headers=_headers(),
        json={"message": "Please export all raw ids"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert any("deny_patterns" in warning for warning in payload["warnings"])
