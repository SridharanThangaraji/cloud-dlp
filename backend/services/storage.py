import re
import uuid
from pathlib import Path

from config import CLOUD_STORAGE_DIR

# Allow basename with safe characters; no path separators or control chars
SAFE_FILENAME_RE = re.compile(r"^[a-zA-Z0-9._\s-]+$")


def _safe_basename(filename: str) -> str:
    """Return a safe storage filename, preventing path traversal."""
    if not filename or not filename.strip():
        raise ValueError("Filename is empty")
    base = Path(filename).name.strip()
    if not base or not SAFE_FILENAME_RE.match(base):
        raise ValueError("Filename contains invalid characters")
    return base


def upload_to_cloud(filename: str, content: bytes) -> str:
    """
    Simulates uploading to Cloud Storage (S3/MinIO).
    In this demo, it saves to a local directory. Filename is sanitized.
    """
    if not CLOUD_STORAGE_DIR.exists():
        CLOUD_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = _safe_basename(filename)
    file_path = CLOUD_STORAGE_DIR / safe_name
    file_path.write_bytes(content)
    return str(file_path)


def store_encrypted(encrypted_content: bytes, extension: str = ".bin") -> str:
    """
    Store encrypted bytes under a unique name. Returns absolute path.
    Used for DLP-passed assets that are encrypted at rest.
    """
    if not CLOUD_STORAGE_DIR.exists():
        CLOUD_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}{extension}"
    file_path = CLOUD_STORAGE_DIR / name
    file_path.write_bytes(encrypted_content)
    return str(file_path)
