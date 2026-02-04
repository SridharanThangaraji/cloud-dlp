import re
import json
from pathlib import Path

class DLPDetector:
    def __init__(self):
        policy_path = Path(__file__).parent / "policies.json"
        with open(policy_path) as f:
            self.rules = json.load(f)

    def scan(self, text: str):
        detected = []
        for name, pattern in self.rules.items():
            if re.search(pattern, text):
                detected.append(name)
        return detected

