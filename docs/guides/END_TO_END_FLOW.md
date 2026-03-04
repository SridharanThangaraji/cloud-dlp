# Cloud DLP — End-to-End Flow & Logic

This document describes the complete flow and logic from the UI through the backend to storage and back.

---

## 1. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  FRONTEND (static: index.html + script.js)                                   │
│  • Dashboard, Upload, Assets, Audit Logs                                     │
│  • Calls API_BASE = http://127.0.0.1:8000                                   │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │ HTTP (fetch)
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  BACKEND (FastAPI: main.py)                                                  │
│  • /health, /stats, /upload, /assets, /assets/{id}, /assets/{id}/verify      │
│  • /logs                                                                     │
└───┬─────────────┬─────────────┬─────────────┬─────────────┬─────────────────┘
    │             │             │             │             │
    ▼             ▼             ▼             ▼             ▼
┌────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐
│ DLP    │  │ Logger   │  │ Crypto   │  │ Storage  │  │ Database     │
│ Engine │  │ (audit)  │  │ (encrypt │  │ (files)  │  │ (SQLite)     │
│        │  │          │  │ + hash)  │  │          │  │              │
└────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────────┘
     │             │             │             │             │
     │             │             │             │             │
     ▼             ▼             ▼             ▼             ▼
  policies.json  upload_logs   .encryption_key  cloud_storage/  dlp_logs.db
                               (or env)         *.bin           stored_assets
```

---

## 2. Upload Flow (End-to-End)

This is the main flow: user selects a file → backend validates, scans, optionally encrypts and stores → UI shows result.

### 2.1 Frontend (script.js)

| Step | Logic |
|------|--------|
| 1 | User selects file via `<input type="file">` or drag-and-drop on `#dropZone`. File name shown in `#fileNameDisplay`. |
| 2 | User clicks **Upload** → `uploadFile()` runs. |
| 3 | If no file: toast "Please select a file", return. |
| 4 | Build `FormData`, append `file` key with the one file. |
| 5 | Disable upload button, show "Scanning…" in `#uploadResult`. |
| 6 | `POST` to `http://127.0.0.1:8000/upload` with `body: formData`. |
| 7 | Parse JSON response. If `!response.ok`: show error from `getErrorMsg(data, response)`, refresh logs/stats, return. |
| 8 | If `data.status === "BLOCKED"`: show "Blocked – sensitive data: …" (reason list), set result class `blocked`. |
| 9 | If `data.status === "ERROR"`: show "Error – …", set result class `error`. |
| 10 | If allowed: show "Encrypted and stored." + hash if present, set class `allowed`, toast success, clear file input, refresh assets and stats. |
| 11 | In all cases after success/block/error: call `loadLogs()`. Re-enable button in `finally`. |

### 2.2 Backend — POST /upload (main.py)

| Step | Logic |
|------|--------|
| 1 | Read full body: `content = await file.read()`. |
| 2 | **Size check**: if `len(content) > MAX_FILE_SIZE` (5MB) → `log_event(filename, "ERROR", ["File too large"])`, raise `HTTPException(400, detail={"status":"ERROR", "reason":["File too large (Max 5MB)"]})`. |
| 3 | **MIME check**: `content_type = file.content_type or ""`. If not in `ALLOWED_MIME_TYPES` (text/plain, application/json, text/csv, application/pdf) → log ERROR with unsupported type, raise `HTTPException(400, …)`. |
| 4 | Decode body to text: `text = content.decode(errors="ignore")`. |
| 5 | **DLP scan**: `findings = detector.scan(text)`. On exception → log ERROR "Scan error", raise `HTTPException(500, …)`. |
| 6 | If `findings` non-empty → `log_event(filename, "BLOCKED", findings)`, return `{"status": "BLOCKED", "reason": findings}`. **Flow stops here; file is not stored.** |
| 7 | If no findings → `log_event(filename, "ALLOWED", [])`. |
| 8 | **Encrypt and hash**: `encrypted, file_hash = encrypt_and_hash(content)`. Hash is SHA-256 of the **encrypted** bytes (for integrity of stored file). |
| 9 | **Store**: `storage_path = store_encrypted(encrypted)`. Writes to `backend/cloud_storage/<uuid>.bin`. On `ValueError` (invalid filename) → 400; other exception → log "Storage error", 500. |
| 10 | **Persist metadata**: open DB session, create `StoredAsset(filename=..., file_hash=..., storage_path=...)`, add, flush to get `asset_id`. |
| 11 | Return `{"status": "ALLOWED", "message": "Encrypted and stored", "asset_id", "file_hash", "storage_path"}`. |

### 2.3 DLP Engine (dlp_engine/detector.py)

| Step | Logic |
|------|--------|
| 1 | On init: load `dlp_engine/policies.json` → dict `{ "email": regex, "password": regex, "phone": regex }`. |
| 2 | `scan(text)`: if `text` is None or not str → return `[]`. |
| 3 | For each rule name and pattern: if `re.search(pattern, text)` matches, append rule name to `detected`. |
| 4 | Return list of detected category names (e.g. `["email","phone"]`). |

**Policies (policies.json):**

- **email**: `[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+`
- **password**: `(?i)(password|pwd)[\s:=]+.{6,}` (password/pwd followed by 6+ chars)
- **phone**: `\b[6-9][0-9]{9}\b` (10-digit Indian-style number)

### 2.4 Logger (services/logger.py)

| Step | Logic |
|------|--------|
| 1 | `log_event(filename, status, reason)` opens a DB session. |
| 2 | Create `UploadLog(filename=filename, status=status, reason=",".join(reason) or "NONE")`. |
| 3 | `db.add(entry)`, then context manager commits and closes. |

All upload outcomes (ALLOWED, BLOCKED, ERROR) are recorded in `upload_logs` for audit.

### 2.5 Crypto (services/crypto.py)

| Step | Logic |
|------|--------|
| 1 | **Key**: from env `CLOUD_DLP_ENCRYPTION_KEY` (base64) or file `backend/.encryption_key`. If missing, generate Fernet key and write to file. |
| 2 | `encrypt_and_hash(content)`: Fernet-encrypt `content`, then SHA-256(encrypted_bytes). Return `(encrypted_bytes, hex_digest)`. |
| 3 | `verify_hash(content, expected_hex)`: return `hashlib.sha256(content).hexdigest() == expected_hex`. Used when verifying stored file integrity. |

### 2.6 Storage (services/storage.py)

| Step | Logic |
|------|--------|
| 1 | `store_encrypted(encrypted_content, extension=".bin")`: ensure `backend/cloud_storage/` exists. |
| 2 | Generate unique name `{uuid4().hex}.bin`, write encrypted bytes, return absolute path. |
| 3 | `_safe_basename` / `upload_to_cloud`: used for non-encrypted uploads; upload flow uses only `store_encrypted` (no original filename in path to avoid path traversal). |

---

## 3. Dashboard Flow (/stats)

- **Frontend**: On showing Dashboard page or init, `loadStats()` fetches `GET /stats`, then fills `#statTotal`, `#statAllowed`, `#statBlocked`, `#statErrors`, `#statAssets`. On failure shows "—".
- **Backend**: `get_stats()` opens one DB session, loads all `UploadLog`, computes total / allowed / blocked / errors **inside the session** (to avoid DetachedInstanceError), gets `StoredAsset.count()`, returns `{ total_uploads, allowed, blocked, errors, stored_assets }`.

---

## 4. Assets Flow

### 4.1 List assets — GET /assets

- **Frontend**: On Assets page, `loadAssets()` fetches `GET /assets`, renders table: filename, hash (short + copy button), date, Verify / Delete buttons. Empty state if no assets.
- **Backend**: One session, `StoredAsset.order_by(created_at.desc()).all()`, return list of `{ id, filename, file_hash, storage_path, created_at }` (all built inside session).

### 4.2 Verify asset — GET /assets/{asset_id}/verify

- **Frontend**: Click "Verify" → `verifyAsset(id)` → `GET /assets/{id}/verify` → show "✓ OK" or reason (e.g. "Hash mismatch") in `#verify-{id}`.
- **Backend**: Load asset in session; if missing → 404. Read `storage_path` and `file_hash` inside session. Read file from disk, `verify_hash(file_bytes, file_hash)`. Return `{ verified: bool, reason }`.

### 4.3 Delete asset — DELETE /assets/{asset_id}

- **Frontend**: Confirm dialog, then `DELETE /assets/{id}`. On success: toast, `loadAssets()`, `loadStats()`.
- **Backend**: In session, get asset by id; if not found → 404. Copy `storage_path`, delete row. After session close, `Path(storage_path).unlink()` if file exists. Return `{ status: "deleted" }`.

---

## 5. Audit Logs Flow — GET /logs

- **Frontend**: On Logs page or refresh, `loadLogs()` fetches `GET /logs`. Optional filter by status (dropdown); render rows: filename, status badge, reason, time. Refreshes every 10s when Logs page is active.
- **Backend**: One session, `UploadLog.all()`, return list of `{ filename, status, reason, timestamp }` (built inside session).

---

## 6. Health Check — GET /health

- **Frontend**: On load and every 15s, `checkHealth()` calls `GET /health`. Updates "Connected" / "Offline" / "Error" and health dot.
- **Backend**: Return `{"status": "ok"}`.

---

## 7. Data Stored Where

| Data | Location |
|------|----------|
| Audit log rows | SQLite `dlp_logs.db` → table `upload_logs` |
| Stored asset metadata | SQLite `dlp_logs.db` → table `stored_assets` |
| Encrypted file bodies | `backend/cloud_storage/<uuid>.bin` |
| Encryption key | `backend/.encryption_key` or env `CLOUD_DLP_ENCRYPTION_KEY` |
| DLP rules | `backend/dlp_engine/policies.json` |

---

## 8. Summary Table (Backend Routes)

| Method | Route | Purpose |
|--------|--------|---------|
| GET | /health | Liveness |
| GET | /stats | Dashboard counts (uploads by status, stored_assets) |
| POST | /upload | Validate → DLP scan → log → if clean: encrypt, hash, store, log, return asset info |
| GET | /assets | List stored assets |
| GET | /assets/{id}/verify | Integrity check (recompute hash vs DB) |
| DELETE | /assets/{id} | Delete DB row and on-disk file |
| GET | /logs | List audit log entries |

All upload attempts are logged; only DLP-clean uploads are encrypted, hashed, and stored; the hash protects integrity of the stored (encrypted) blob.
