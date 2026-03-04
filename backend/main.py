from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from config import ALLOWED_MIME_TYPES, API_VERSION, MAX_FILE_SIZE
from database.models import StoredAsset, UploadLog, get_db_session
from dlp_engine.detector import DLPDetector
from services.crypto import encrypt_and_hash, verify_hash
from services.logger import log_event
from services.storage import store_encrypted

app = FastAPI(
    title="Cloud DLP System",
    description="Upload files for DLP scanning; allowed files are stored and all events are logged.",
    version=API_VERSION,
)
detector = DLPDetector()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> Dict[str, str]:
    """Health check for load balancers and monitoring."""
    return {"status": "ok"}


@app.get("/config")
def get_config() -> Dict[str, Any]:
    """Public config for UI: limits and allowed types (read-only)."""
    return {
        "max_file_size_mb": MAX_FILE_SIZE // (1024 * 1024),
        "allowed_mime_types": sorted(ALLOWED_MIME_TYPES),
        "version": API_VERSION,
    }


@app.get("/policies")
def get_policies() -> Dict[str, str]:
    """Return active DLP detection rules (name → regex pattern). Read-only."""
    return dict(detector.rules)


@app.get("/stats")
def get_stats() -> Dict[str, Any]:
    """Dashboard stats: total uploads, by status, and stored assets count."""
    with get_db_session() as db:
        logs = db.query(UploadLog).all()
        total = len(logs)
        allowed = sum(1 for l in logs if l.status == "ALLOWED")
        blocked = sum(1 for l in logs if l.status == "BLOCKED")
        errors = sum(1 for l in logs if l.status == "ERROR")
        assets_count = db.query(StoredAsset).count()
    return {
        "total_uploads": total,
        "allowed": allowed,
        "blocked": blocked,
        "errors": errors,
        "stored_assets": assets_count,
    }


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Handle file upload: validate, run DLP scan, and store if allowed.

    Returns:
        Dict with "status" ("ALLOWED" | "BLOCKED" | "ERROR") and optional
        "reason" or "storage_path". Client errors (size, type) return 400;
        server errors (scan, storage) return 500.
    """
    content = await file.read()

    # 1. File size check
    if len(content) > MAX_FILE_SIZE:
        log_event(file.filename, "ERROR", ["File too large"])
        raise HTTPException(
            status_code=400,
            detail={"status": "ERROR", "reason": ["File too large (Max 5MB)"]},
        )

    # 2. MIME type check
    content_type = file.content_type or ""
    if content_type not in ALLOWED_MIME_TYPES:
        log_event(file.filename, "ERROR", [f"Unsupported type: {content_type or 'unknown'}"])
        raise HTTPException(
            status_code=400,
            detail={
                "status": "ERROR",
                "reason": [f"Unsupported file type: {content_type or 'unknown'}"],
            },
        )

    text = content.decode(errors="ignore")

    try:
        findings = detector.scan(text)
    except Exception as e:
        log_event(file.filename, "ERROR", [f"Scan error: {str(e)}"])
        raise HTTPException(
            status_code=500,
            detail={"status": "ERROR", "reason": [f"Scan error: {str(e)}"]},
        ) from e

    if findings:
        log_event(file.filename, "BLOCKED", findings)
        return {"status": "BLOCKED", "reason": findings}

    log_event(file.filename, "ALLOWED", [])

    try:
        encrypted, file_hash = encrypt_and_hash(content)
        storage_path = store_encrypted(encrypted)
    except ValueError as e:
        log_event(file.filename, "ERROR", [f"Invalid filename: {str(e)}"])
        raise HTTPException(
            status_code=400,
            detail={"status": "ERROR", "reason": [f"Invalid filename: {str(e)}"]},
        ) from e
    except Exception as e:
        log_event(file.filename, "ERROR", [f"Storage error: {str(e)}"])
        raise HTTPException(
            status_code=500,
            detail={"status": "ERROR", "reason": [f"Storage error: {str(e)}"]},
        ) from e

    with get_db_session() as db:
        asset = StoredAsset(
            filename=file.filename,
            file_hash=file_hash,
            storage_path=storage_path,
        )
        db.add(asset)
        db.flush()
        asset_id = asset.id

    return {
        "status": "ALLOWED",
        "message": "Encrypted and stored",
        "asset_id": asset_id,
        "file_hash": file_hash,
        "storage_path": storage_path,
    }


@app.get("/assets")
def list_assets() -> List[Dict[str, Any]]:
    """List all stored (encrypted) assets with id, filename, hash, created_at."""
    with get_db_session() as db:
        assets = db.query(StoredAsset).order_by(StoredAsset.created_at.desc()).all()
        return [
            {
                "id": a.id,
                "filename": a.filename,
                "file_hash": a.file_hash,
                "storage_path": a.storage_path,
                "created_at": a.created_at,
            }
            for a in assets
        ]


@app.delete("/assets/{asset_id}")
def delete_asset(asset_id: int) -> Dict[str, str]:
    """Remove stored asset from DB and delete file from disk."""
    with get_db_session() as db:
        asset = db.query(StoredAsset).filter(StoredAsset.id == asset_id).first()
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")
        storage_path = asset.storage_path
        db.delete(asset)
    path = Path(storage_path)
    if path.exists():
        try:
            path.unlink()
        except OSError:
            pass
    return {"status": "deleted", "message": "Asset removed"}


@app.get("/assets/{asset_id}/verify")
def verify_asset(asset_id: int) -> Dict[str, Any]:
    """Recompute hash of stored file and compare to DB. Returns verified: true/false."""
    with get_db_session() as db:
        asset = db.query(StoredAsset).filter(StoredAsset.id == asset_id).first()
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")
        storage_path = asset.storage_path
        file_hash = asset.file_hash
    path = Path(storage_path)
    if not path.exists():
        return {"verified": False, "reason": "File missing on storage"}
    content = path.read_bytes()
    ok = verify_hash(content, file_hash)
    return {"verified": ok, "reason": "Hash matches" if ok else "Hash mismatch"}


@app.get("/logs")
def get_logs() -> List[Dict[str, Any]]:
    """
    Retrieves security audit logs from the database.

    Returns:
        A list of log entries (filename, status, reason, timestamp).
    """
    with get_db_session() as db:
        logs = db.query(UploadLog).all()
        return [
            {
                "filename": log.filename,
                "status": log.status,
                "reason": log.reason,
                "timestamp": log.timestamp,
            }
            for log in logs
        ]


# Serve frontend static files (must be last so API routes take precedence)
_FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if _FRONTEND_DIR.is_dir():
    from fastapi.staticfiles import StaticFiles
    @app.get("/", response_class=FileResponse)
    def serve_index():
        return FileResponse(_FRONTEND_DIR / "index.html")
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIR), html=True), name="frontend")
