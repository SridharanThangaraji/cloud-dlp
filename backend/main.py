from fastapi import FastAPI, UploadFile, File
from dlp_engine.detector import DLPDetector
from services.logger import log_event
from database.models import SessionLocal, UploadLog
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Cloud DLP System")
detector = DLPDetector()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    content = await file.read()
    text = content.decode(errors="ignore")

    findings = detector.scan(text)

    if findings:
        log_event(file.filename, "BLOCKED", findings)
        return {
            "status": "BLOCKED",
            "reason": findings
        }

    log_event(file.filename, "ALLOWED", [])
    return {
        "status": "ALLOWED"
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

