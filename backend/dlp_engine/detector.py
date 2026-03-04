import re
import json
from pathlib import Path
from typing import List

class DLPDetector:
    """
    A tool to scan text for sensitive information based on regex rules.
    """
    def __init__(self):
        policy_path = Path(__file__).parent / "policies.json"
        with open(policy_path) as f:
            self.rules = json.load(f)

    def scan(self, text: str) -> List[str]:
        """
        Scans the provided text against configured policies.

        Args:
            text: The content to scan (must be string; None/empty returns []).

        Returns:
            A list of detected sensitive data category names.
        """
        if text is None or not isinstance(text, str):
            return []
        detected = []
        for name, pattern in self.rules.items():
            if re.search(pattern, text):
                detected.append(name)
        return detected

