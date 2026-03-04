# Cloud Data Leakage Prevention (DLP) System

A secure, rule-based inspection system for cloud environments. Upload files, scan them for sensitive information (emails, passwords, phone numbers), and sync to simulated cloud storage when they pass security checks.

## How to run (recommended — single server)

From the **project root** (`cloud-dlp/`):

**1. Install dependencies (one-time)**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cd ..
```

**2. Start the project**

```bash
python run.py
```

Or, if you already have the venv activated or dependencies installed globally:

```bash
python run.py
```

If `backend/.venv` exists, `run.py` will use it automatically.

**3. Open in browser**

- **http://127.0.0.1:8000**

One process serves both the API and the frontend. Stop with **Ctrl+C**.

**Optional:** use a different port:

```bash
PORT=3000 python run.py
```

---

## Features

- **Real-time security scanning** — Regex-based policies detect sensitive data before upload.
- **Dashboard UI** — Responsive interface with drag-and-drop upload and live audit logs.
- **Audit logging** — All upload attempts (allowed, blocked, errors) are persisted to SQLite.
- **Validation** — File size (max 5MB) and MIME type checks (plain text, JSON, CSV, PDF).
- **Cloud storage** — Allowed files are written to a local “cloud” directory (replace with S3/MinIO in production).

## Project structure

```text
cloud-dlp/
├── backend/
│   ├── config.py          # Central configuration: limits, DB URL, storage and crypto settings
│   ├── main.py            # FastAPI app and API routes (/upload, /logs, /assets, /stats, /config, /policies)
│   ├── requirements.txt   # Backend dependencies
│   ├── database/          # SQLAlchemy models and session handling
│   │   └── models.py
│   ├── dlp_engine/        # DLP rules (policies.json) and detector
│   │   ├── detector.py
│   │   └── policies.json
│   ├── services/          # Cross-cutting backend services
│   │   ├── crypto.py      # Fernet encryption + SHA-256 hashing
│   │   ├── logger.py      # Audit logging to SQLite
│   │   └── storage.py     # Cloud storage abstraction (local directory in this demo)
│   └── tests/             # Pytest (DLP detector and backend units)
├── frontend/
│   ├── index.html         # Single-page dashboard shell
│   ├── style.css          # Modern glassmorphism-inspired styling
│   └── script.js          # Navigation, upload flow, assets/logs dashboard
├── docs/
│   ├── README.md           # Index of docs (guides, paper, presentations)
│   ├── guides/             # ARCHITECTURE.md, END_TO_END_FLOW.md, DEMO.md
│   ├── paper/              # LaTeX paper source and PDF
│   ├── presentations/     # Slide decks (.pptx, .pdf) and ppt.md
│   ├── thesis/             # Project report
│   └── journal/            # Journal submission
├── ARCHITECTURE.md        # Design and data flow
├── CHANGELOG.md           # Version history
└── run.py                 # Single entry point that serves backend + frontend via Uvicorn
```

## Setup (alternative: backend + frontend separately)

If you prefer to run the backend and frontend separately (e.g. for development):

### Backend

From the project root:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Server runs at `http://127.0.0.1:8000`. API docs: `http://127.0.0.1:8000/docs`.

### Frontend

Open `frontend/index.html` in a browser, or serve the `frontend/` folder with any static server (e.g. `python -m http.server 3000` from `frontend/`). The dashboard uses the same host as the page for API calls when served over HTTP; if you open the file directly, it falls back to `http://127.0.0.1:8000` — ensure the backend is running.

## API

| Method | Path                      | Description |
|--------|---------------------------|-------------|
| GET    | `/`                      | Serves the SPA dashboard (`frontend/index.html`). |
| GET    | `/health`                | Health check; returns `{ "status": "ok" }`. |
| GET    | `/config`                | Public, read-only configuration (max size, allowed MIME types, API version). |
| GET    | `/policies`              | Active DLP detection rules (name → regex). |
| GET    | `/stats`                 | Aggregate stats: total uploads, allowed, blocked, errors, stored assets. |
| POST   | `/upload`                | Upload a file. Validates size/MIME, runs DLP scan, stores if allowed. Returns `{ "status": "ALLOWED" \| "BLOCKED" \| "ERROR", "reason"?, "asset_id"?, "file_hash"?, "storage_path"? }`. Client errors (size/type) → 400; server errors (scan/storage) → 500. |
| GET    | `/assets`                | Lists stored encrypted assets (id, filename, hash, created_at, storage_path). |
| DELETE | `/assets/{asset_id}`     | Deletes a stored asset record and underlying encrypted file. |
| GET    | `/assets/{asset_id}/verify` | Recomputes hash of stored file and compares with DB; returns `{ "verified": bool, "reason": str }`. |
| GET    | `/logs`                  | Returns all audit log entries (filename, status, reason, timestamp). |

## Testing

```bash
cd backend
.venv/bin/pytest -v
```

## Docker

You can run Cloud DLP in Docker on **Linux**, **macOS**, or **Windows** (Docker Desktop).

### Build image

From the project root (`cloud-dlp/`):

```bash
docker build -t cloud-dlp -f docker/Dockerfile .
```

### Run container

```bash
docker run --rm -p 8000:8000 --name cloud-dlp-app cloud-dlp
```

Then open:

- `http://127.0.0.1:8000` — dashboard UI and API (same on Windows/macOS/Linux).

To change the port:

```bash
docker run --rm -e PORT=3000 -p 3000:3000 cloud-dlp
```

## Configuration

- **Central config:** `backend/config.py` holds the primary settings (API version, max file size, allowed MIME types, DB URL, storage directory, and encryption key configuration).
- **Database:** SQLite at `backend/dlp_logs.db` (URL built from `DATABASE_URL` in `config.py` and used by `database/models.py`).
- **Storage:** Allowed files are written under `backend/cloud_storage/` (location configured via `CLOUD_STORAGE_DIR` in `config.py` and used by `services/storage.py`).
- **Encryption:** Symmetric Fernet key is loaded from `CLOUD_DLP_ENCRYPTION_KEY` (env var) or `backend/.encryption_key` (see `services/crypto.py` and `config.py`).
- **Limits:** Max file size and allowed MIME types are defined in `config.py` and surfaced via `/config`. DLP rules are in `backend/dlp_engine/policies.json`.

## License

MIT
