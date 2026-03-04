"""Central configuration for the Cloud DLP backend.

This module groups runtime configuration in one place so the rest of the
codebase can import it instead of hard-coding values in multiple files.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Set


# Base directories
BACKEND_DIR: Path = Path(__file__).resolve().parent
PROJECT_ROOT: Path = BACKEND_DIR.parent


# --- API / limits ---

API_VERSION: str = "0.2.0"

# Maximum upload size (bytes) and allowed MIME types for the /upload endpoint.
MAX_FILE_SIZE: int = 5 * 1024 * 1024  # 5 MB
ALLOWED_MIME_TYPES: Set[str] = {
    "text/plain",
    "application/json",
    "text/csv",
    "application/pdf",
}


# --- Database ---

# SQLite database is stored inside backend/ by default, but can be overridden
# with CLOUD_DLP_DATABASE_URL for deployments/tests.
DB_PATH: Path = BACKEND_DIR / "dlp_logs.db"
_DEFAULT_DATABASE_URL = f"sqlite:///{DB_PATH}"
DATABASE_URL: str = os.environ.get("CLOUD_DLP_DATABASE_URL", _DEFAULT_DATABASE_URL)


# --- Storage / encryption ---

# Directory used by storage services for persisted (encrypted) assets.
# Can be overridden with CLOUD_DLP_STORAGE_DIR.
_DEFAULT_STORAGE_DIR = BACKEND_DIR / "cloud_storage"
_storage_dir_env = os.environ.get("CLOUD_DLP_STORAGE_DIR")
CLOUD_STORAGE_DIR: Path = (
    Path(_storage_dir_env).expanduser().resolve()
    if _storage_dir_env
    else _DEFAULT_STORAGE_DIR
)

# Symmetric encryption key configuration for Fernet:
# - environment variable name
# - fallback key file location (git-ignored)
ENCRYPTION_KEY_ENV: str = "CLOUD_DLP_ENCRYPTION_KEY"
ENCRYPTION_KEY_FILE: Path = BACKEND_DIR / ".encryption_key"

