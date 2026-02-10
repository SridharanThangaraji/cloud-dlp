from fastapi import FastAPI, UploadFile, File
from dlp_engine.detector import DLPDetector
from services.logger import log_event
from services.storage import upload_to_cloud
from database.models import SessionLocal, UploadLog
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Cloud DLP System")
detector = DLPDetector()

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_MIME_TYPES = {"text/plain", "application/json", "text/csv", "application/pdf"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    # 1. File size check
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        return {
            "status": "ERROR",
            "reason": ["File too large (Max 5MB)"]
        }

    # 2. MIME type check
    if file.content_type not in ALLOWED_MIME_TYPES:
        return {
            "status": "ERROR",
            "reason": [f"Unsupported file type: {file.content_type}"]
        }

    text = content.decode(errors="ignore")

    try:
        findings = detector.scan(text)
    except Exception as e:
        return {
            "status": "ERROR",
            "reason": [f"Scan error: {str(e)}"]
        }

    if findings:
        log_event(file.filename, "BLOCKED", findings)
        return {
            "status": "BLOCKED",
            "reason": findings
        }

    log_event(file.filename, "ALLOWED", [])
    
    # 3. Cloud Storage Integration
    try:
        storage_path = upload_to_cloud(file.filename, content)
    except Exception as e:
         return {
            "status": "ERROR",
            "reason": [f"Storage error: {str(e)}"]
        }

    return {
        "status": "ALLOWED",
        "storage_path": storage_path
    }

@app.get("/logs")
def get_logs():
    db = SessionLocal()
    logs = db.query(UploadLog).all()
    db.close()

    return [
        {
            "filename": log.filename,
            "status": log.status,
            "reason": log.reason,
            "timestamp": log.timestamp
        }
        for log in logs
    ]

