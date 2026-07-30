import json
import re
from pathlib import Path

COLLECTION = Path("collections/Akseptasi.postman_collection.json")
OUTPUT = Path("payloads")

OUTPUT.mkdir(exist_ok=True)


def sanitize_filename(name):
    name = name.lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    return name.strip("_")


def process_items(items):
    for item in items:

        if "item" in item:
            process_items(item["item"])
            continue

        request = item.get("request", {})
        body = request.get("body", {})

        if body.get("mode") != "raw":
            continue

        raw = body.get("raw")

        if not raw:
            continue

        try:
            payload = json.loads(raw)
        except Exception:
            continue

        filename = sanitize_filename(item["name"]) + ".json"

        with open(OUTPUT / filename, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4, ensure_ascii=False)

        print(f"Generated : {filename}")


with open(COLLECTION, encoding="utf-8") as f:
    collection = json.load(f)

process_items(collection["item"])

print("Done")