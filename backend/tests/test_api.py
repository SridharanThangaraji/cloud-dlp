import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

# Ensure the backend package root is on sys.path so `main` and other modules import.
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from main import app  # noqa: E402

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_config_endpoint_matches_settings():
    from config import API_VERSION, MAX_FILE_SIZE, ALLOWED_MIME_TYPES

    r = client.get("/config")
    assert r.status_code == 200
    data = r.json()
    assert data["version"] == API_VERSION
    assert data["max_file_size_mb"] == MAX_FILE_SIZE // (1024 * 1024)
    assert set(data["allowed_mime_types"]) == set(ALLOWED_MIME_TYPES)


def test_policies_endpoint():
    r = client.get("/policies")
    assert r.status_code == 200
    data = r.json()
    # policies.json should define at least one rule
    assert isinstance(data, dict)
    assert data


def test_upload_blocked_for_sensitive_content(tmp_path):
    content = b"My password is: secret123"
    files = {"file": ("secret.txt", content, "text/plain")}
    r = client.post("/upload", files=files)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "BLOCKED"
    assert "password" in ",".join(data.get("reason", []))


def test_upload_too_large_rejected(monkeypatch):
    from config import MAX_FILE_SIZE

    # Build a payload just over the configured limit
    large_content = b"x" * (MAX_FILE_SIZE + 1)
    files = {"file": ("big.txt", large_content, "text/plain")}
    r = client.post("/upload", files=files)
    assert r.status_code == 400
    data = r.json()
    assert data["detail"]["status"] == "ERROR"
    assert any("File too large" in msg for msg in data["detail"]["reason"])


def test_stats_and_logs_endpoints():
    # Call stats before doing anything; keys should exist, counts >= 0
    stats_resp = client.get("/stats")
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    for key in ["total_uploads", "allowed", "blocked", "errors", "stored_assets"]:
        assert key in stats
        assert stats[key] >= 0

    # Logs endpoint always returns a list
    logs_resp = client.get("/logs")
    assert logs_resp.status_code == 200
    logs = logs_resp.json()
    assert isinstance(logs, list)
    if logs:
        sample = logs[0]
        assert {"filename", "status", "reason", "timestamp"} <= sample.keys()


def test_root_serves_index_html():
    resp = client.get("/")
    assert resp.status_code == 200
    content_type = resp.headers.get("content-type", "")
    assert "text/html" in content_type


def test_assets_lifecycle_and_verify():
    # Upload a clearly safe document that should pass DLP
    safe_content = b"This is a safe document with no sensitive information at all."
    files = {"file": ("asset_safe.txt", safe_content, "text/plain")}
    upload_resp = client.post("/upload", files=files)
    assert upload_resp.status_code == 200
    body = upload_resp.json()
    assert body["status"] == "ALLOWED"
    asset_id = body["asset_id"]

    # Asset should appear in /assets listing
    assets_resp = client.get("/assets")
    assert assets_resp.status_code == 200
    assets = assets_resp.json()
    assert isinstance(assets, list)
    assert any(a["id"] == asset_id for a in assets)

    # Verify endpoint should confirm integrity
    verify_resp = client.get(f"/assets/{asset_id}/verify")
    assert verify_resp.status_code == 200
    verify_data = verify_resp.json()
    assert verify_data["verified"] is True

    # Delete endpoint should remove the asset
    delete_resp = client.delete(f"/assets/{asset_id}")
    assert delete_resp.status_code == 200
    delete_body = delete_resp.json()
    assert delete_body["status"] == "deleted"

    # Verifying again should now return 404 (asset not found)
    missing_verify_resp = client.get(f"/assets/{asset_id}/verify")
    assert missing_verify_resp.status_code == 404


def test_verify_reports_missing_file_on_disk(tmp_path):
    """
    If the DB entry exists but the underlying file is missing, verify
    should return verified: false with a clear reason.
    """
    # Upload a safe asset
    content = b"Another safe file for integrity check."
    files = {"file": ("asset_missing.txt", content, "text/plain")}
    upload_resp = client.post("/upload", files=files)
    assert upload_resp.status_code == 200
    body = upload_resp.json()
    assert body["status"] == "ALLOWED"
    asset_id = body["asset_id"]
    storage_path = body["storage_path"]

    # Remove the underlying file from disk
    path = Path(storage_path)
    if path.exists():
        path.unlink()

    verify_resp = client.get(f"/assets/{asset_id}/verify")
    assert verify_resp.status_code == 200
    verify_data = verify_resp.json()
    assert verify_data["verified"] is False
    assert "missing" in verify_data["reason"].lower()

