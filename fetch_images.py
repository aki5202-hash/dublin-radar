#!/usr/bin/env python3
"""Download a real source image for each listing, or write a category placeholder.

Never attach an image from a different event. Refresh runs should call this
(via build.py) so new items also get images.
"""

from __future__ import annotations

import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parent
IMAGES = ROOT / "images"
DATA = ROOT / "data.json"
FONT_BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FONT_REG = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
IG_UA = "facebookexternalhit/1.1"
TIMEOUT = 20
MAX_BYTES = 8 * 1024 * 1024
MAX_WIDTH = 800
WORKERS = 5

CAT_COLORS = {
    "食": (255, 107, 61),
    "衣": (255, 61, 138),
    "住": (200, 255, 61),
    "行": (92, 225, 255),
    "育": (201, 166, 255),
    "樂": (255, 225, 74),
}
CAT_HINT = {
    "食": "美食飲品",
    "衣": "時尚衣著",
    "住": "居家設計",
    "行": "出行探路",
    "育": "學習工作坊",
    "樂": "娛樂活動",
}

# Pages that list many events: their og:image is usually not this item.
LISTING_URL_RE = re.compile(
    r"("
    r"nialler9\.com/the-nialler9-dublin-gig-guide|"
    r"totallydublin\.ie/events/?$|"
    r"templebardublin\.ie/temple-bar-events-|"
    r"eventbrite\.[^/]+/d/|"
    r"meetup\.com/find|"
    r"visitdublin\.com/whats-on/?$"
    r")",
    re.I,
)

SKIP_NAME_RE = re.compile(
    r"(logo|favicon|sprite|icon|avatar|pixel|tracking|1x1|spacer|placeholder|badge|button|wordmark|crest)",
    re.I,
)
STOP = {
    "the", "and", "for", "with", "from", "live", "in", "of", "at", "to", "a", "an",
    "by", "on", "de", "la", "el", "presents", "present", "show", "tour", "dublin",
    "ireland", "irish",
}

_font_index: Optional[int] = None


def cjk_index() -> int:
    global _font_index
    if _font_index is not None:
        return _font_index
    probe = "重"
    for i in range(8):
        try:
            font = ImageFont.truetype(FONT_BOLD, 40, index=i)
            img = Image.new("L", (80, 80), 0)
            ImageDraw.Draw(img).text((0, 0), probe, fill=255, font=font)
            if max(img.getdata()) > 0:
                _font_index = i
                return i
        except Exception:
            continue
    _font_index = 0
    return 0


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size, index=cjk_index())


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-IE,en;q=0.9,zh-TW;q=0.8",
    })
    return s


def significant_tokens(name: str) -> list[str]:
    tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9'’_-]{1,}", name)
    out = []
    for t in tokens:
        tl = re.sub(r"[^A-Za-z0-9]", "", t).lower()
        if len(tl) < 3 or tl in STOP:
            continue
        out.append(tl)
    return out


def title_matches(name: str, title: str) -> bool:
    if not title:
        return False
    hay = title.lower()
    tokens = significant_tokens(name)
    if not tokens:
        return False
    hits = [t for t in tokens if t in hay]
    if not hits:
        return False
    if len(tokens) == 1:
        return True
    # One distinctive token (Heathers, Magnificent) is enough.
    if any(len(t) >= 6 for t in hits):
        return True
    return len(hits) >= min(2, len(tokens))


def looks_like_listing(url: str, title: str, name: str) -> bool:
    if LISTING_URL_RE.search(url or ""):
        return True
    # If the page title does not mention this item, do not trust og:image / json-ld.
    if not title_matches(name, title or ""):
        return True
    return False


def absolutize(page_url: str, src: str) -> Optional[str]:
    if not src:
        return None
    src = src.strip().strip("\"'")
    if src.startswith("data:") or src.startswith("javascript:"):
        return None
    if src.startswith("//"):
        return "https:" + src
    return urljoin(page_url, src)


def jsonld_images(soup: BeautifulSoup) -> list[str]:
    found = []

    def walk(obj):
        if isinstance(obj, dict):
            typ = obj.get("@type") or obj.get("type") or ""
            if isinstance(typ, list):
                typ = " ".join(str(x) for x in typ)
            typ = str(typ).lower()
            for key in ("image", "thumbnailUrl", "poster", "imageUrl"):
                val = obj.get(key)
                if isinstance(val, str):
                    found.append((typ, val))
                elif isinstance(val, dict) and val.get("url"):
                    found.append((typ, val["url"]))
                elif isinstance(val, list):
                    for v in val:
                        if isinstance(v, str):
                            found.append((typ, v))
                        elif isinstance(v, dict) and v.get("url"):
                            found.append((typ, v["url"]))
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for v in obj:
                walk(v)

    for tag in soup.find_all("script", attrs={"type": re.compile(r"ld\+json", re.I)}):
        raw = tag.string or tag.get_text() or ""
        raw = raw.strip()
        if not raw:
            continue
        try:
            walk(json.loads(raw))
        except Exception:
            continue
    # Prefer images attached to Event/ImageObject later; just return urls in order.
    return [u for _, u in found]


def extract_candidates(page_url: str, html: str, item: dict) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    og_title = soup.find("meta", property="og:title") or soup.find("meta", attrs={"property": "og:title"})
    if og_title and og_title.get("content"):
        title = og_title["content"].strip() or title

    cands: list[str] = []

    def add(src: Optional[str]):
        absu = absolutize(page_url, src or "")
        if not absu or absu in cands:
            return
        if SKIP_NAME_RE.search(absu) or SKIP_NAME_RE.search(Path(urlparse(absu).path).name):
            return
        cands.append(absu)

    if looks_like_listing(page_url, title, item["name"]):
        return []

    if not looks_like_listing(page_url, title, item["name"]):
        for prop in ("og:image", "og:image:secure_url", "twitter:image", "twitter:image:src"):
            tag = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop}) or soup.find(
                "meta", attrs={"property": prop}
            )
            if tag and tag.get("content"):
                add(tag["content"])
        link = soup.find("link", attrs={"rel": re.compile(r"image_src", re.I)})
        if link and link.get("href"):
            add(link["href"])
        for u in jsonld_images(soup):
            add(u)
        # First official hero / show poster on a page that is about this item.
        for sel in (
            "img.show-item__img",
            "img.show-item",
            "img.show-images__bg",
            "picture.show-item img",
            "img.wp-post-image",
            ".event-header img",
            ".event-hero img",
            ".hero img",
        ):
            nodes = soup.select(sel)
            if not nodes:
                continue
            img = nodes[0]
            add(img.get("src") or img.get("data-src"))
            srcset = img.get("srcset") or img.get("data-srcset") or ""
            parts = [p.strip().split(" ")[0] for p in srcset.split(",") if p.strip()]
            if parts:
                add(parts[-1])
            parent = img.find_parent("picture")
            if parent:
                sources = parent.find_all("source")
                if sources:
                    ss = sources[0].get("srcset") or ""
                    sp = [p.strip().split(" ")[0] for p in ss.split(",") if p.strip()]
                    if sp:
                        add(sp[-1])
            break

    # Venue-specific artwork whose filename mentions the event (3Arena, etc.)
    tokens = significant_tokens(item["name"])
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or img.get("data-lazy-src") or ""
        alt = (img.get("alt") or "") + " " + (img.get("title") or "") + " " + src
        if SKIP_NAME_RE.search(src) or SKIP_NAME_RE.search(alt):
            continue
        # Only keep if the image itself is clearly about this event.
        hay = alt.lower()
        if tokens and sum(1 for t in tokens if t in hay) >= (1 if len(tokens) == 1 else min(2, len(tokens))):
            add(src)
            srcset = img.get("srcset") or img.get("data-srcset") or ""
            # Prefer the largest in srcset.
            parts = [p.strip().split(" ")[0] for p in srcset.split(",") if p.strip()]
            for p in parts[-1:]:
                add(p)

    # 3Arena / similar: /images/uploads/events/JUNGLE_...
    for m in re.finditer(r"https?://[^\"'\s>]+\.(?:jpg|jpeg|png|webp)", html, re.I):
        u = m.group(0)
        if SKIP_NAME_RE.search(u):
            continue
        path = urlparse(u).path.lower()
        if "/events/" in path or "/event/" in path or "/shows/" in path or "/show/" in path or "/whats-on/" in path:
            if tokens and any(t in path for t in tokens):
                add(u)

    return cands


def download_image(sess: requests.Session, url: str, referer: str) -> Optional[Image.Image]:
    try:
        headers = {"Referer": referer, "Accept": "image/avif,image/webp,image/*,*/*;q=0.8"}
        if "instagram.com" in (url or "").lower() or "cdninstagram.com" in (url or "").lower() or "instagram.com" in (referer or "").lower():
            headers["User-Agent"] = IG_UA
        with sess.get(url, headers=headers, timeout=TIMEOUT, stream=True, allow_redirects=True) as r:
            if r.status_code != 200:
                return None
            ctype = (r.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            if ctype and not ctype.startswith("image/") and ctype not in ("application/octet-stream",):
                return None
            buf = BytesIO()
            total = 0
            for chunk in r.iter_content(65536):
                if not chunk:
                    continue
                total += len(chunk)
                if total > MAX_BYTES:
                    return None
                buf.write(chunk)
        raw = buf.getvalue()
        if len(raw) < 2000:
            return None
        img = Image.open(BytesIO(raw))
        img.load()
        if img.width < 200 or img.height < 200:
            return None
        # Skip near-square tiny logos already handled; also skip very wide tracking pixels.
        if img.width < 240 and img.height < 240:
            return None
        return img
    except Exception:
        return None


def process_photo(img: Image.Image) -> Image.Image:
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        bg = Image.new("RGB", img.size, (12, 10, 18))
        rgba = img.convert("RGBA")
        bg.paste(rgba, mask=rgba.split()[-1])
        img = bg
    else:
        img = img.convert("RGB")
    w, h = img.size
    if w > MAX_WIDTH:
        nh = max(1, round(h * (MAX_WIDTH / w)))
        img = img.resize((MAX_WIDTH, nh), Image.Resampling.LANCZOS)
    # Cap extreme vertical posters so cards stay reasonable, without cropping a different scene.
    if img.height > 1400:
        ratio = 1400 / img.height
        img = img.resize((max(1, round(img.width * ratio)), 1400), Image.Resampling.LANCZOS)
    return img


def save_photo(img: Image.Image, dest_stem: Path) -> Path:
    webp = dest_stem.with_suffix(".webp")
    try:
        img.save(webp, "WEBP", quality=80, method=6)
        if webp.stat().st_size > 0:
            # Remove sibling jpg if we switched formats.
            jpg = dest_stem.with_suffix(".jpg")
            if jpg.exists():
                jpg.unlink()
            return webp
    except Exception:
        pass
    jpg = dest_stem.with_suffix(".jpg")
    img.save(jpg, "JPEG", quality=82, optimize=True)
    return jpg


def placeholder_path(category: str) -> Path:
    return IMAGES / f"placeholder-{category}.webp"


def make_placeholder(category: str) -> Path:
    IMAGES.mkdir(exist_ok=True)
    path = placeholder_path(category)
    accent = CAT_COLORS.get(category, (200, 200, 200))
    W, H = 800, 500
    img = Image.new("RGB", (W, H), (14, 12, 20))
    draw = ImageDraw.Draw(img, "RGBA")
    # Soft gradient wash in the category colour.
    overlay = Image.new("RGB", (W, H), (14, 12, 20))
    od = ImageDraw.Draw(overlay)
    for y in range(H):
        t = y / max(1, H - 1)
        r = int(14 * (1 - t) + accent[0] * 0.18 * t)
        g = int(12 * (1 - t) + accent[1] * 0.18 * t)
        b = int(20 * (1 - t) + accent[2] * 0.18 * t)
        od.line([(0, y), (W, y)], fill=(r, g, b))
    img = Image.blend(img, overlay, 0.85)
    # Radial-ish disc
    blob = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(blob)
    bd.ellipse((W - 420, -80, W + 80, 420), fill=accent + (55,))
    bd.ellipse((-160, H - 300, 280, H + 140), fill=accent + (35,))
    img = img.convert("RGBA")
    img = Image.alpha_composite(img, blob).convert("RGB")
    img = img.filter(ImageFilter.GaussianBlur(radius=0.4))
    draw = ImageDraw.Draw(img)
    f_big = font(FONT_BOLD, 168)
    f_mid = font(FONT_BOLD, 36)
    f_sml = font(FONT_REG, 22)
    char = category
    bbox = draw.textbbox((0, 0), char, font=f_big)
    cw, ch = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((W - cw) / 2, 110 - bbox[1]), char, font=f_big, fill=accent)
    hint = CAT_HINT.get(category, "")
    hb = draw.textbbox((0, 0), hint, font=f_mid)
    hw = hb[2] - hb[0]
    draw.text(((W - hw) / 2, 300), hint, font=f_mid, fill=(246, 236, 215))
    cap = "暫無活動官方圖片 · 都柏林活動雷達"
    cb = draw.textbbox((0, 0), cap, font=f_sml)
    draw.text(((W - (cb[2] - cb[0])) / 2, 360), cap, font=f_sml, fill=(154, 146, 127))
    img.save(path, "WEBP", quality=82, method=6)
    return path


def relpath(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def ensure_placeholders() -> dict[str, Path]:
    IMAGES.mkdir(exist_ok=True)
    out = {}
    for cat in CAT_COLORS:
        out[cat] = make_placeholder(cat)
    return out


def existing_source_file(item_id: str) -> Optional[Path]:
    for ext in (".webp", ".jpg", ".jpeg", ".png"):
        p = IMAGES / f"{item_id}{ext}"
        if p.exists() and p.stat().st_size > 1000:
            return p
    return None



def page_title(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    og_title = soup.find("meta", property="og:title") or soup.find("meta", attrs={"property": "og:title"})
    if og_title and og_title.get("content"):
        title = og_title["content"].strip() or title
    return title


def fetch_page(sess: requests.Session, url: str):
    last = None
    for attempt in range(4):
        try:
            headers = {}
            if "instagram.com" in (url or "").lower():
                headers["User-Agent"] = IG_UA
            r = sess.get(url, timeout=TIMEOUT, allow_redirects=True, headers=headers or None)
        except Exception:
            time.sleep(1.0 + attempt)
            continue
        last = r
        title = page_title(r.text or "") if r.ok else ""
        challenge = "one moment, please" in title.lower() or "just a moment" in title.lower()
        if r.status_code == 200 and r.text and not challenge and len(r.text) > 15000:
            return r
        time.sleep(1.0 + attempt)
    return last


def fetch_one(item: dict, sess: requests.Session, refresh: bool) -> dict:
    """Return image fields for this item."""
    placeholders = {c: placeholder_path(c) for c in CAT_COLORS}
    cat = item.get("category") or "樂"
    fallback = {
        "image": relpath(placeholders.get(cat, placeholders["樂"])),
        "imageKind": "placeholder",
        "imageCredit": "分類示意（無活動官方圖片）",
        "imageOrigin": "",
    }
    existing = existing_source_file(item["id"])
    if existing and not refresh and item.get("imageKind") == "source":
        return {
            "image": relpath(existing),
            "imageKind": "source",
            "imageCredit": item.get("imageCredit") or f"圖片來源：{item.get('sourceName') or '出處頁面'}",
            "imageOrigin": item.get("imageOrigin") or "",
        }

    source = item.get("source") or ""
    if not source.startswith("http"):
        return fallback

    try:
        r = fetch_page(sess, source)
        if r is None or r.status_code != 200 or not r.text:
            return fallback
        page_url = r.url
        cands = extract_candidates(page_url, r.text, item)
    except Exception:
        return fallback

    for url in cands[:8]:
        img = download_image(sess, url, page_url)
        if img is None:
            continue
        try:
            out = process_photo(img)
            dest = save_photo(out, IMAGES / item["id"])
            return {
                "image": relpath(dest),
                "imageKind": "source",
                "imageCredit": f"圖片來源：{item.get('sourceName') or '出處頁面'}",
                "imageOrigin": url,
            }
        except Exception:
            continue
    return fallback


def apply_fields(items: list[dict], results: dict[str, dict]) -> None:
    for item in items:
        fields = results.get(item["id"])
        if not fields:
            continue
        item["image"] = fields["image"]
        item["imageKind"] = fields["imageKind"]
        item["imageCredit"] = fields["imageCredit"]
        if fields.get("imageOrigin"):
            item["imageOrigin"] = fields["imageOrigin"]
        elif "imageOrigin" in item and fields["imageKind"] != "source":
            item.pop("imageOrigin", None)


def run(refresh: bool = False) -> dict:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    items = data["items"]
    ensure_placeholders()
    sess = session()
    results: dict[str, dict] = {}
    # Serial-ish with a small pool; be polite to source sites.
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = {pool.submit(fetch_one, item, sess, refresh): item["id"] for item in items}
        done = 0
        for fut in as_completed(futs):
            iid = futs[fut]
            try:
                results[iid] = fut.result()
            except Exception as exc:
                print(f"  ! {iid}: {type(exc).__name__}: {exc}", file=sys.stderr)
                item = next(x for x in items if x["id"] == iid)
                cat = item.get("category") or "樂"
                results[iid] = {
                    "image": relpath(placeholder_path(cat)),
                    "imageKind": "placeholder",
                    "imageCredit": "分類示意（無活動官方圖片）",
                    "imageOrigin": "",
                }
            done += 1
            kind = results[iid]["imageKind"]
            print(f"  [{done}/{len(items)}] {iid}: {kind} -> {results[iid]['image']}")

    apply_fields(items, results)
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    src_n = sum(1 for x in items if x.get("imageKind") == "source")
    ph_n = sum(1 for x in items if x.get("imageKind") != "source")
    print(f"Images: {src_n} from source, {ph_n} placeholders, {len(items)} total")
    return data


def main(argv: list[str]) -> int:
    refresh = "--refresh-images" in argv
    t0 = time.time()
    run(refresh=refresh)
    print(f"Done in {time.time() - t0:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
