"""
Collects items from FEEDS and writes a normalized items.json.
- Safe to run locally or in a job; server.py does NOT import this.
- Requires: feedparser, requests (see requirements.txt).

By default, writes to items.out.json to avoid overwriting your curated items.json.
Change OUT_FILE if you want it to write directly to 'items.json'.
"""

import json
import time
from pathlib import Path
import feedparser

try:
    from feeds import FEEDS
except Exception:
    FEEDS = []

OUT_FILE = Path("items.json")  # change to Path("items.json") if desired
MAX_PER_FEED = 10


def entry_date(e):
    # Return YYYY-MM-DD string if available
    if hasattr(e, "published_parsed") and e.published_parsed:
        tm = e.published_parsed
        return f"{tm.tm_year:04d}-{tm.tm_mon:02d}-{tm.tm_mday:02d}"
    if getattr(e, "updated", ""):
        return e.updated.split("T")[0][:10]
    return ""


def collect():
    items = []
    for f in FEEDS:
        src = f.get("source", "").strip() or "Unknown"
        url = f.get("url", "").strip()
        if not url:
            continue
        parsed = feedparser.parse(url)
        for e in parsed.entries[:MAX_PER_FEED]:
            title = getattr(e, "title", "Untitled")
            link = getattr(e, "link", "")
            date = entry_date(e)
            items.append({
                "title": title,
                "link": link,
                "source": src,
                "date": date
            })
        # polite pause
        time.sleep(0.2)

    # sort by date desc where possible; undated at bottom
    def sort_key(it):
        return it.get("date") or "0000-00-00"

    items.sort(key=sort_key, reverse=True)
    payload = {"items": items}
    OUT_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {len(items)} items to {OUT_FILE}")


if __name__ == "__main__":
    collect()
