from database.models import SessionLocal, UploadLog

def log_event(filename, status, reason):
    db = SessionLocal()
    entry = UploadLog(
        filename=filename,
        status=status,
        reason=",".join(reason) if reason else "NONE"
    )
    db.add(entry)
    db.commit()
    db.close()

