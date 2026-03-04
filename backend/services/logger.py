from database.models import UploadLog, get_db_session


def log_event(filename: str, status: str, reason: list) -> None:
    """Record an upload event in the audit log."""
    with get_db_session() as db:
        entry = UploadLog(
            filename=filename,
            status=status,
            reason=",".join(reason) if reason else "NONE",
        )
        db.add(entry)

