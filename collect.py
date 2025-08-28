"""
collect.py — fetch articles from FEEDS and write normalized items.json.

Updates:
- Stronger YouTube handling (extract video IDs, better description fields).
- Tighter filtering to MBB only (football/WBB/other sports filtered out).
- Still newest-first (then by a small relevance score).
- Safe timeouts + real UA; non-fatal on feed hiccups.
"""

from pathlib import Path
import time, json, re
from html import unescape
from typing import List, Dict, Tuple
import requests, feedparser

from feeds import FEEDS_META, KEYWORDS_INCLUDE, KEYWORDS_EXCLUDE

OUT_FILE = Path("items.json")
MAX_PER_FEED = 60
TOTAL_MAX = 500
TIMEOUT = 15
UA = "Mozilla/5.0 (X11; Linux x86_64) PurdueMBBBot/1.3 (+https://example.local)"

INC = [k.lower() for k in KEYWORDS_INCLUDE]
EXC = [k.lower() for k in KEYWORDS_EXCLUDE]

YOUTUBE_CHANNEL_SOURCES = {"youtube – field of 68", "youtube – sleepers media"}

def text_ok(txt: str) -> bool:
    """Return True if text passes exclude filters and matches at least one include keyword."""
    t = (txt or "").lower()
    if any(x in t for x in EXC):
        return False
    return (not INC) or any(x in t for x in INC)

def norm_date(e) -> str:
    """Return YYYY-MM-DD or ''."""
    if getattr(e, "published_parsed", None):
        tm = e.published_parsed
        return f"{tm.tm_year:04d}-{tm.tm_mon:02d}-{tm.tm_mday:02d}"
    if getattr(e, "updated", None):
        return e.updated.split("T")[0][:10]
    return ""

def clean_html(s: str) -> str:
    return unescape(re.sub("<[^>]+>", " ", s or "").strip())

def parse_feed(url: str):
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT)
        r.raise_for_status()
        return feedparser.parse(r.content)
    except Exception:
        return feedparser.parse(url)  # best-effort fallback

def yt_watch_link(entry) -> str:
    """
    Build a reliable YouTube link.
    Prefer media:group->yt:videoid when available; else use entry.link.
    """
    video_id = None
    # feedparser maps tags; try common locations
    if "yt_videoid" in entry:
        video_id = entry.get("yt_videoid")
    else:
        mg = entry.get("media_group") or {}
        if isinstance(mg, dict):
            video_id = mg.get("yt_videoid")
    if video_id:
        return f"https://www.youtube.com/watch?v={video_id}"
    return (getattr(entry, "link", "") or "").strip()

def harvest_text_fields(e) -> str:
    """Combine likely text fields for keyword filtering."""
    parts = [
        getattr(e, "title", ""),
        getattr(e, "summary", "") or getattr(e, "description", ""),
    ]
    # Some feeds expose extra media fields
    for key in ("media_description", "media_title"):
        v = e.get(key) if isinstance(e, dict) else None
        if v:
            parts.append(v)
    return " ".join([clean_html(p) for p in parts if p])

def score_item(title: str, desc: str, source: str) -> int:
    """Simple relevance score — title hits weigh more."""
    t = (title or "").lower()
    d = (desc or "").lower()
    s = 0
    if "purdue" in t: s += 5
    s += sum(2 for k in INC if k in t)   # title hits
    s += sum(1 for k in INC if k in d)   # summary/media hits
    if "purdue athletics" in source.lower(): s += 2
    if "youtube" in source.lower(): s += 1
    return s

def collect() -> List[Dict]:
    ranked: List[Tuple[Dict, int]] = []
    seen_link, seen_title = set(), set()

    for f in FEEDS_META:
        name, url = f["name"], f["url"]
        parsed = parse_feed(url)
        pulled = 0

        for e in parsed.entries:
            title = (getattr(e, "title", "") or "").strip()

            # Build robust link (especially for YouTube)
            link = (getattr(e, "link", "") or "").strip()
            src_name_lower = name.lower()
            if "youtube" in src_name_lower:
                link = yt_watch_link(e) or link

            # Combine multiple text fields for filtering
            desc = clean_html(getattr(e, "summary", "") or getattr(e, "description", ""))
            blob = harvest_text_fields(e)
            blob_all = f"{title} {blob}"

            if not title or not link:
                continue
            if not text_ok(blob_all):
                continue

            key_title = re.sub(r"\s+", " ", title.lower())
            if link in seen_link or key_title in seen_title:
                continue

            item = {
                "title": title,
                "link": link,
                "source": name,
                "date": norm_date(e),
                "description": (desc[:280] + ("…" if len(desc) > 280 else "")) if desc else ""
            }
            score = score_item(title, desc, name)

            ranked.append((item, score))
            seen_link.add(link)
            seen_title.add(key_title)
            pulled += 1
            if pulled >= MAX_PER_FEED:
                break

        print(f"[collector] {name}: {pulled} items")
        time.sleep(0.2)  # be polite

    # newest-first across everything, then by score; undated at bottom
    def date_key(it: Dict) -> str:
        return it.get("date") or "0000-00-00"

    ranked.sort(key=lambda pair: (date_key(pair[0]), pair[1]), reverse=True)

    items = [it for it, _ in ranked][:TOTAL_MAX]
    return items

def main():
    try:
        items = collect()
    except Exception as e:
        print(f"[collector] ERROR: {e}")
        items = []
    payload = {"items": items}
    OUT_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"[collector] Wrote {len(items)} items to {OUT_FILE}")

if __name__ == "__main__":
    main()
