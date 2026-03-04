import pytest
import sys
import os

# Add the backend directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dlp_engine.detector import DLPDetector

@pytest.fixture
def detector():
    return DLPDetector()

def test_scan_safe_text(detector):
    text = "This is a safe message with no sensitive data."
    findings = detector.scan(text)
    assert findings == []

def test_scan_email(detector):
    text = "My email is test@example.com"
    findings = detector.scan(text)
    assert "email" in findings

def test_scan_phone(detector):
    text = "Call me at 9876543210"
    findings = detector.scan(text)
    assert "phone" in findings

def test_scan_password(detector):
    text = "My password is: secret123"
    findings = detector.scan(text)
    assert "password" in findings

def test_scan_multiple(detector):
    text = "Contact me at test@example.com or 9876543210"
    findings = detector.scan(text)
    assert "email" in findings
    assert "phone" in findings


def test_scan_none_returns_empty(detector):
    """Guard against None or non-string input."""
    assert detector.scan(None) == []
