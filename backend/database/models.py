from contextlib import contextmanager
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()


def utc_now():
    """Current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


class UploadLog(Base):
    """
    Database model for storing file upload and security scan result logs.
    """
    __tablename__ = "upload_logs"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String)
    status = Column(String)
    reason = Column(String)
    timestamp = Column(DateTime, default=utc_now)


class StoredAsset(Base):
    """
    Encrypted assets stored after passing DLP. file_hash is SHA-256 of stored
    (encrypted) content for integrity verification.
    """
    __tablename__ = "stored_assets"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    file_hash = Column(String(64), nullable=False)  # SHA-256 hex
    storage_path = Column(String, nullable=False)
    created_at = Column(DateTime, default=utc_now)


@contextmanager
def get_db_session():
    """Context manager for database sessions. Ensures close and rollback on error."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

Base.metadata.create_all(bind=engine)

