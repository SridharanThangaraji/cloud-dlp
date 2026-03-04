# Cloud DLP - How to run the demo

## From project root (`cloud-dlp/`)

Use **two terminals**, both started from the project root:

```bash
cd ~/workspace/cloud-dlp
```

### Terminal 1 – start the backend

```bash
cd backend && .venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
```

Leave this running. If you see "address already in use", either stop whatever is using port 8000, or pick another port (e.g. 8765) and in Terminal 2 run:

```bash
BASE_URL=http://127.0.0.1:8765 ./demo.sh
```

### Terminal 2 – run the API demo script

From the **same project root** (so `demo.sh` is in the current directory):

```bash
cd ~/workspace/cloud-dlp
./demo.sh
```

### Browser – UI demo

1. With the backend still running on port **8000**, open `frontend/index.html` in your browser (e.g. double-click or `xdg-open frontend/index.html`).
2. Upload a file and click "Run Security Scan". Try a plain text file (allowed) and a file containing an email like `user@example.com` (blocked).

## One-liner (API demo only)

From project root, with backend already running on 8000:

```bash
./demo.sh
```

## If `./demo.sh` says "no such file or directory"

You are probably inside `backend/`. Go back to the project root first:

```bash
cd ~/workspace/cloud-dlp
./demo.sh
```
