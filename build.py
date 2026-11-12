#!/usr/bin/env python3
"""Inject data.json into the fallback <script id="fallback-data"> block in index.html."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
START = "<!-- DATA:START -->"
END = "<!-- DATA:END -->"
REQUIRED = ("lastUpdated", "timezone", "items")
ITEM_REQUIRED = ("id", "kind", "name", "category", "start", "dateLabel", "venue", "area", "hook", "rating", "source", "sourceName")


def load_data(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    for key in REQUIRED:
        if key not in data:
            raise SystemExit(f"data.json missing key: {key}")
    if data["timezone"] != "Europe/Dublin":
        raise SystemExit("timezone must be Europe/Dublin")
    if not isinstance(data["items"], list) or not data["items"]:
        raise SystemExit("data.json items must be a non-empty list")
    for i, item in enumerate(data["items"]):
        missing = [k for k in ITEM_REQUIRED if k not in item]
        if missing:
            raise SystemExit(f"item {i} ({item.get('id')}) missing: {', '.join(missing)}")
        if item["kind"] not in ("event", "opening"):
            raise SystemExit(f"item {item.get('id')} has bad kind: {item['kind']}")
        if item["category"] not in list("食衣住行育樂"):
            raise SystemExit(f"item {item.get('id')} has bad category: {item['category']}")
    return data


def inject(data: dict, html: str) -> str:
    # Escape U+003C so a field can never close the <script> tag.
    payload = json.dumps(data, ensure_ascii=False, indent=2).replace("<", "\\u003c")
    block = (
        f"{START}\n"
        f'<script type="application/json" id="fallback-data">\n'
        f"{payload}\n"
        f"</script>\n"
        f"{END}"
    )
    i = html.find(START)
    j = html.find(END)
    if i < 0 or j < 0 or j < i:
        raise SystemExit("index.html is missing <!-- DATA:START --> / <!-- DATA:END --> markers")
    return html[:i] + block + html[j + len(END) :]


def main() -> int:
    data_path = ROOT / "data.json"
    html_path = ROOT / "index.html"
    data = load_data(data_path)
    html = html_path.read_text(encoding="utf-8")
    html_path.write_text(inject(data, html), encoding="utf-8")
    events = sum(1 for x in data["items"] if x["kind"] == "event")
    openings = sum(1 for x in data["items"] if x["kind"] == "opening")
    print(
        f"Injected {len(data['items'])} items "
        f"({events} events, {openings} openings) from data.json "
        f"into {html_path.name}. lastUpdated={data['lastUpdated']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
