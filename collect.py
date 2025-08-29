import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any
import re

import feedparser
import requests

# ---- Read config from feeds.py but don't require optional names -------------
try:
    import feeds as _cfg  # type: ignore
except Exception as e:
    raise SystemExit(f"feeds.py is required next to collect.py: {e}")

FEEDS_META = getattr(_cfg, "FEEDS_META", [])
STATIC_LINKS = getattr(_cfg, "STATIC_LINKS", [])

# Optional filters – all safe defaults
KEYWORDS_POSITIVE: List[str] = [t.lower() for t in getattr(_cfg, "KEYWORDS_POSITIVE", [])]
SPORT_TOKENS: List[str] = [t.lower() for t in getattr(_cfg, "SPORT_TOKENS", [])]
KEYWORDS_EXCLUDE: List[str] = [t.lower() for t in getattr(_cfg, "KEYWORDS_EXCLUDE", [])]

TOTAL_CAP: int = int(getattr(_cfg, "TOTAL_CAP", 200))
PER_FEED_CAP: int = int(getattr(_cfg, "PER_FEED_CAP", 60))

ITEMS_PATH = Path("items.json")


def http_get(url: str) -> bytes:
    """Simple GET with a short timeout."""
    r = requests.get(url, timeout=12, headers={"User-Agent": "feed-collector/1.0"})
    r.raise_for_status()
    return r.content


def parse_date_struct(struct_time) -> datetime:
    try:
        return datetime.fromtimestamp(time.mktime(struct_time), tz=timezone.utc)
    except Exception:
        return datetime.now(tz=timezone.utc)


def normalize_text(*parts: str) -> str:
    t = " ".join([p or "" for p in parts])
    return re.sub(r"\s+", " ", t).strip()


def on_topic(title: str, summary: str, tags: List[str]) -> bool:
    t = normalize_text(title, summary, " ".join(tags)).lower()

    # Hard excludes first
    if KEYWORDS_EXCLUDE:
        for bad in KEYWORDS_EXCLUDE:
            if bad and bad in t:
                return False

    # If SPORT_TOKENS defined, require at least one
    if SPORT_TOKENS:
        if not any(tok in t for tok in SPORT_TOKENS if tok):
            return False

    # If positives defined, require at least one to appear
    if KEYWORDS_POSITIVE:
        if not any(p in t for p in KEYWORDS_POSITIVE if p):
            return False

    return True


def collect() -> Dict[str, Any]:
    items: List[Dict[str, Any]] = []

    for src in FEEDS_META:
        url = src.get("url")
        name = src.get("name") or src.get("source") or "Source"
        if not url:
            continue

        try:
            raw = http_get(url)
            feed = feedparser.parse(raw)
        except Exception:
            continue

        count = 0
        for e in feed.entries:
            title = getattr(e, "title", "").strip()
            link = getattr(e, "link", "").strip()
            if not title or not link:
                continue

            # summary/description/body text
            summary = getattr(e, "summary", "") or getattr(e, "description", "")
            tags = [getattr(t, "term", "") for t in getattr(e, "tags", []) or []]

            if not on_topic(title, summary, tags):
                continue

            # pick best date available
            dt = None
            for key in ("published_parsed", "updated_parsed", "created_parsed"):
                if getattr(e, key, None):
                    dt = parse_date_struct(getattr(e, key))
                    break
            if not dt:
                dt = datetime.now(tz=timezone.utc)

            items.append({
                "title": title,
                "link": link,
                "source": name,
                "date": dt.isoformat(),
                "description": summary.strip()[:400],
            })

            count += 1
            if count >= PER_FEED_CAP:
                break

    # Deduplicate by link or title (case-insensitive)
    seen = set()
    deduped: List[Dict[str, Any]] = []
    for it in items:
        key = (it["link"].lower(), it["title"].lower())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(it)

    # Sort newest first
    deduped.sort(key=lambda x: x.get("date", ""), reverse=True)

    # Cap total
    deduped = deduped[:TOTAL_CAP]

    return {"items": deduped}


def main():
    data = collect()
    ITEMS_PATH.write_text(json.dumps(data, ensure_ascii=False))
    print(f"[collector] wrote {len(data['items'])} items to {ITEMS_PATH}")


if __name__ == "__main__":
    main()
