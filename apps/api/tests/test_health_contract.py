from fastapi.testclient import TestClient

from app.main import app


def test_liveness_reports_api_service() -> None:
    client = TestClient(app)

    response = client.get("/healthz/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "api"}


def test_health_can_skip_dependency_checks(monkeypatch) -> None:
    monkeypatch.setenv("ATLAS_HEALTH_SKIP_DEPENDENCIES", "true")
    client = TestClient(app)

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json()["dependencies"] == "skipped"


def test_mvp_contract_keeps_private_default_and_canonical_statuses() -> None:
    client = TestClient(app)

    response = client.get("/dev/mvp-contract")

    assert response.status_code == 200
    body = response.json()
    assert body["default_privacy"] == "private"
    assert body["upload_transport"] == "api-mediated"
    assert body["playback_delivery"] == "api-proxied-hls"
    assert body["smoke_coverage"]["upload_process_playback_metadata"] == "implemented-by-wave-3-smoke"
    assert body["smoke_coverage"]["bad_upload_failed_state"] == "implemented-by-wave-3-smoke"
    assert body["video_status_values"] == [
        "draft",
        "uploading",
        "uploaded",
        "queued",
        "probing",
        "processing",
        "ready",
        "failed",
    ]
