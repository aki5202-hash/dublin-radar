#!/usr/bin/env python3
"""Validate data.json, optionally fetch images, and inject the fallback block in index.html."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
START = "<!-- DATA:START -->"
END = "<!-- DATA:END -->"
REQUIRED = ("lastUpdated", "timezone", "items")
ITEM_REQUIRED = (
    "id",
    "kind",
    "tier",
    "name",
    "category",
    "start",
    "dateLabel",
    "venue",
    "area",
    "hook",
    "rating",
    "source",
    "sourceName",
    "image",
    "imageKind",
    "imageCredit",
)


def load_data(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    for key in REQUIRED:
        if key not in data:
            raise SystemExit(f"data.json missing key: {key}")
    if data["timezone"] != "Europe/Dublin":
        raise SystemExit("timezone must be Europe/Dublin")
    if not isinstance(data["items"], list) or not data["items"]:
        raise SystemExit("data.json items must be a non-empty list")
    seen = set()
    for i, item in enumerate(data["items"]):
        missing = [k for k in ITEM_REQUIRED if k not in item]
        if missing:
            raise SystemExit(f"item {i} ({item.get('id')}) missing: {', '.join(missing)}")
        if item["id"] in seen:
            raise SystemExit(f"duplicate id: {item['id']}")
        seen.add(item["id"])
        if item["kind"] not in ("event", "opening"):
            raise SystemExit(f"item {item.get('id')} has bad kind: {item['kind']}")
        if item["tier"] not in ("mainstream", "niche"):
            raise SystemExit(f"item {item.get('id')} has bad tier: {item['tier']}")
        if item["category"] not in list("食衣住行育樂"):
            raise SystemExit(f"item {item.get('id')} has bad category: {item['category']}")
        if item["imageKind"] not in ("source", "placeholder"):
            raise SystemExit(f"item {item.get('id')} has bad imageKind: {item['imageKind']}")
        image_path = item["image"]
        if not isinstance(image_path, str) or not image_path.startswith("images/") or ".." in image_path:
            raise SystemExit(f"item {item.get('id')} has bad image path: {image_path}")
        abs_image = ROOT / image_path
        if not abs_image.is_file() or abs_image.stat().st_size < 200:
            raise SystemExit(f"item {item.get('id')} image file missing or empty: {image_path}")
        if item["imageKind"] == "source":
            stem = Path(image_path).stem
            if stem != item["id"]:
                raise SystemExit(
                    f"item {item['id']} source image must be images/{item['id']}.ext, got {image_path}"
                )
        else:
            if Path(image_path).stem != f"placeholder-{item['category']}":
                raise SystemExit(
                    f"item {item['id']} placeholder must be images/placeholder-{item['category']}.ext"
                )
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
    parser = argparse.ArgumentParser(description="Validate data, fetch images, inject fallback HTML.")
    parser.add_argument(
        "--skip-images",
        action="store_true",
        help="Do not fetch images; only validate existing files and inject HTML.",
    )
    parser.add_argument(
        "--refresh-images",
        action="store_true",
        help="Re-download source images even if a local file already exists.",
    )
    args = parser.parse_args()

    if not args.skip_images:
        from fetch_images import run as fetch_images

        fetch_images(refresh=args.refresh_images)

    data_path = ROOT / "data.json"
    html_path = ROOT / "index.html"
    data = load_data(data_path)
    html = html_path.read_text(encoding="utf-8")
    html_path.write_text(inject(data, html), encoding="utf-8")
    events = sum(1 for x in data["items"] if x["kind"] == "event")
    openings = sum(1 for x in data["items"] if x["kind"] == "opening")
    mainstream = sum(1 for x in data["items"] if x["tier"] == "mainstream")
    niche = sum(1 for x in data["items"] if x["tier"] == "niche")
    source_img = sum(1 for x in data["items"] if x["imageKind"] == "source")
    placeholders = sum(1 for x in data["items"] if x["imageKind"] == "placeholder")
    print(
        f"Injected {len(data['items'])} items "
        f"({events} events, {openings} openings; {mainstream} mainstream, {niche} niche; "
        f"{source_img} real images, {placeholders} placeholders) from data.json "
        f"into {html_path.name}. lastUpdated={data['lastUpdated']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
