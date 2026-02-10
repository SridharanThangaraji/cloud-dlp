import os
from pathlib import Path

STORAGE_PATH = Path(__file__).parent.parent / "cloud_storage"

def upload_to_cloud(filename: str, content: bytes):
    """
    Simulates uploading to Cloud Storage (S3/MinIO).
    In this demo, it saves to a local directory.
    """
    if not STORAGE_PATH.exists():
        STORAGE_PATH.mkdir(parents=True, exist_ok=True)
    
    file_path = STORAGE_PATH / filename
    with open(file_path, "wb") as f:
        f.write(content)
    
    return str(file_path)
