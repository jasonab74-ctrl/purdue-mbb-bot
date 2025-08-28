"""
collect.py — fetch articles from FEEDS and write normalized items.json.

- Uses a real User-Agent + requests to avoid blocks; passes bytes to feedparser.
- Applies KEYWORDS_INCLUDE/EXCLUDE to title+summary (keeps basketball-only).
- Deduplicates by link and normalized title.
- Bounded per-feed and globally so startup is quick.
"""

from pathlib import Path
import time, json, re
from typing import List, Dict
import requests, feedparser

from feeds import FEEDS_META, KEYWORDS_INCLUDE, KEYWORDS_EXCLUDE

OUT_FILE = Path("items.json")
MAX_PER_FEED = 20
TOTAL_MAX = 250
TIMEOUT = 15
UA = "Mozilla/5.0 (X11; Linux x86_64) PurdueMBBBot/1.0 (+https://example.local)"

INC = [k.lower() for k in KEYWORDS_INCLUDE]
EXC = [k.lower() for k in KEYWORDS_EXCLUDE]

def text_ok(txt: str) -> bool:
    t = (txt or "").lower()
    if any(x in t for x in EXC):
        return False
    return (not INC) or any(x in t for x in INC)

def norm_date(e) -> str:
    if getattr(e, "published_parsed", None):
        tm = e.published_parsed
        return f"{tm.tm_year:04d}-{tm.tm_mon:02d}-{tm.tm_mday:02d}"
    if getattr(e, "updated", None):
        return e.updated.split("T")[0][:10]
    return ""

def clean_html(s: str) -> str:
    return re.sub("<[^>]+>", "", s or "").strip()

def parse_feed(url: str):
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT)
        r.raise_for_status()
        return feedparser.parse(r.content)
    except Exception:
        return feedparser.parse(url)  # last-ditch attempt

def collect() -> List[Dict]:
    items: List[Dict] = []
    seen_link, seen_title = set(), set()

    for f in FEEDS_META:
        name, url = f["name"], f["url"]
        parsed = parse_feed(url)
        count = 0
        for e in parsed.entries:
            title = (getattr(e, "title", "") or "").strip()
            link = (getattr(e, "link", "") or "").strip()
            desc = clean_html(getattr(e, "summary", "") or getattr(e, "description", ""))
            blob = f"{title} {desc}"

            if not title or not link:
                continue
            if not text_ok(blob):
                continue

            key_title = re.sub(r"\s+", " ", title.lower())
            if link in seen_link or key_title in seen_title:
                continue

            items.append({
                "title": title,
                "link": link,
                "source": name,
                "date": norm_date(e),
                "description": (desc[:280] + ("…" if len(desc) > 280 else "")) if desc else ""
            })
            seen_link.add(link)
            seen_title.add(key_title)
            count += 1
            if count >= MAX_PER_FEED:
                break
        time.sleep(0.2)  # be polite

    # newest first; undated at bottom
    items.sort(key=lambda it: it.get("date") or "0000-00-00", reverse=True)
    return items[:TOTAL_MAX]

def main():
    try:
        items = collect()
    except Exception:
        items = []
    payload = {"items": items}
    OUT_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {len(items)} items to {OUT_FILE}")

if __name__ == "__main__":
    main()
