import json
from pathlib import Path


def load_payload(filename):
    payload_path = Path("payloads") / filename

    with open(payload_path, "r", encoding="utf-8") as f:
        return json.load(f)