#!/usr/bin/env python3
"""
Run the entire Cloud DLP project in a single process.

One server (FastAPI on port 8000) serves both:
  - API: /health, /stats, /upload, /assets, /logs, etc.
  - Frontend: / (index.html, script.js, style.css)

Usage (from project root):
  python run.py

Requires: pip install -r backend/requirements.txt  (or backend/.venv)

Then open: http://127.0.0.1:8000

Stop with Ctrl+C.
"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT, "backend")
PORT = int(os.environ.get("PORT", "8000"))
VENV_PYTHON = os.path.join(BACKEND_DIR, ".venv", "bin", "python")


def main():
    if not os.path.isdir(BACKEND_DIR):
        print("Error: backend/ not found. Run from project root.")
        sys.exit(1)
    if not os.path.isdir(os.path.join(ROOT, "frontend")):
        print("Error: frontend/ not found. Run from project root.")
        sys.exit(1)
    # Use venv Python only if we're not already running with it (avoid re-exec loop)
    if os.path.isfile(VENV_PYTHON):
        try:
            venv_real = os.path.realpath(VENV_PYTHON)
            exe_real = os.path.realpath(sys.executable)
            if venv_real != exe_real:
                os.execv(VENV_PYTHON, [VENV_PYTHON, __file__] + sys.argv[1:])
                return
        except Exception:
            pass
    sys.path.insert(0, BACKEND_DIR)
    os.chdir(BACKEND_DIR)

    import uvicorn
    print("Cloud DLP — single server")
    print("Open: http://127.0.0.1:{}".format(PORT))
    print("Stop: Ctrl+C\n")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=PORT,
        log_level="info",
    )


if __name__ == "__main__":
    main()
