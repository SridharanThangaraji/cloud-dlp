# Architecture

## Overview

Cloud DLP is a small web app: a FastAPI backend that accepts file uploads, runs a rule-based DLP scan, and optionally writes allowed files to local “cloud” storage while logging every outcome to SQLite. A static frontend provides the upload UI and a live view of the audit log.

## Data flow

1. **Upload** — User selects a file; frontend sends `POST /upload` with multipart form data.
2. **Validation** — Backend checks size (≤5MB) and MIME type (plain, JSON, CSV, PDF). On failure: log event, return 400.
3. **DLP scan** — File content is decoded as text (errors ignored) and scanned against regex rules in `dlp_engine/policies.json`. If any rule matches, upload is **BLOCKED** and logged.
4. **Storage** — If allowed, content is written to `backend/cloud_storage/<filename>` and path returned. On storage failure: log event, return 500.
5. **Logs** — Every outcome (ALLOWED, BLOCKED, ERROR) is written to the `upload_logs` table via `services/logger.log_event()`.
6. **Dashboard** — Frontend polls `GET /logs` every 10s and renders the latest entries (with HTML escaping to avoid XSS).

## Components

| Component        | Role |
|-----------------|------|
| `config.py`     | Central configuration (API version, limits, DB URL, storage directory, encryption key paths). All backend modules import from here instead of hard-coding values. |
| `main.py`       | FastAPI app; `/upload`, `/logs`, `/assets`, `/stats`, `/config`, `/policies`; validation and error handling with proper HTTP status codes. |
| `database/models.py` | SQLAlchemy engine, `UploadLog` and `StoredAsset` models, `get_db_session()` context manager for safe session lifecycle. |
| `dlp_engine/detector.py` | Loads `policies.json`, exposes `scan(text)` → list of matched rule names. |
| `services/logger.py`   | Writes one row to `upload_logs` (filename, status, reason). |
| `services/storage.py`  | Writes encrypted bytes to `cloud_storage/` and returns path, using the directory from `config.py`. |
| `services/crypto.py`   | Handles Fernet encryption and SHA-256 hashing, sourcing key configuration from `config.py`. |
| Frontend        | Vanilla JS: dashboard navigation, upload form, drag-and-drop, result message, assets table, logs table with safe rendering. |

## Design choices

- **Session handling** — Database sessions are used via `get_db_session()` so that commit/rollback and `close()` always run, avoiding leaks and inconsistent state.
- **Timestamps** — Stored in UTC using `datetime.now(timezone.utc)` (timezone-aware).
- **Errors** — Client errors (too large, unsupported type) → 400 with body `{ "detail": { "status", "reason" } }`. Server errors (scan, storage) → 500 with same shape. All error outcomes are logged.
- **Security** — CORS is permissive for development. Log content and filenames are escaped in the UI to prevent XSS. No authentication or rate limiting in this demo.

## Extending

- **DLP rules** — Edit `backend/dlp_engine/policies.json` (regex per category).
- **Real cloud storage** — Replace `services/storage.py` with S3/MinIO client calls; keep the same interface (filename + bytes → path or raise) and continue to use `CLOUD_STORAGE_DIR` from `config.py`.
- **Config** — Add new settings to `backend/config.py` (e.g., auth, rate limits) and inject them into the relevant modules instead of scattering constants.
