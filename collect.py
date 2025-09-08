#!/usr/bin/env python3
"""
Purdue MBB collector — hardened for GitHub Pages

- Only Purdue MEN'S BASKETBALL articles are allowed.
- Excludes: football, volleyball, softball, baseball, soccer, hockey, WBB, etc.
- Writes items.json with:
    {
      "updated": ISO8601,
      "sources": [...fixed curated list...],
      "links":   [...fixed buttons...],
      "items":   [ {title, link, summary, source, published} ... ]
    }
- Safe to run in GitHub Actions on a schedule. Only items.json changes.
"""

import json
import time
import re
from datetime import datetime, timezone
import feedparser

from feeds import FEEDS, STATIC_LINKS, CURATED_SOURCES, TRUSTED_DOMAINS

# ---------------- Basics ----------------
NOW = datetime.now(timezone.utc)

def iso_now():
    return NOW.isoformat()

def to_iso(dt_struct):
    try:
        return datetime.fromtimestamp(time.mktime(dt_struct), tz=timezone.utc).isoformat()
    except Exception:
        return iso_now()

def clean_text(s: str) -> str:
    return (s or "").replace("\u200b", "").strip()

def domain_of(href: str) -> str:
    try:
        return re.sub(r"^https?://(www\.)?", "", href).split("/")[0].lower()
    except Exception:
        return ""

# ---------------- Filters ----------------
NEGATIVE = re.compile(
    r"\b(football|nfl|volleyball|softball|baseball|soccer|hockey|women'?s|wbb|w\s*bb)\b",
    re.I,
)
MBB_POSITIVE = re.compile(
    r"\b(men'?s\s*basketball|mbb|basketball)\b",
    re.I,
)
PURDUE = re.compile(r"\bpurdue\b", re.I)

def is_trusted(href: str) -> bool:
    d = domain_of(href)
    return any(d.endswith(t) for t in TRUSTED_DOMAINS)

def allow_item(title: str, summary: str, href: str) -> bool:
    """
    Strict allowlist:
      - Must not mention excluded sports.
      - Must reference Purdue.
      - Must look like MEN's basketball (or trusted domain leniency).
    """
    text = f"{title} {summary}"
    if NEGATIVE.search(text):
        return False

    if not PURDUE.search(text):
        if not is_trusted(href):
            return False

    if not MBB_POSITIVE.search(text):
        if not is_trusted(href):
            return False

    return True

# ---------------- Fetch & build ----------------
def fetch_feed(url: str, limit: int = 75):
    d = feedparser.parse(url)
    items = []
    for e in d.entries[:limit]:
        title = clean_text(getattr(e, "title", ""))
        link = getattr(e, "link", "")
        if not title or not link:
            continue

        summary = clean_text(
            getattr(e, "summary", "")
            or getattr(e, "description", "")
        )

        # Prefer the feed's title as source; fallback to domain
        src = clean_text(getattr(d.feed, "title", "")) or domain_of(link)

        if not allow_item(title, summary, link):
            continue

        if hasattr(e, "published_parsed") and e.published_parsed:
            published = to_iso(e.published_parsed)
        elif hasattr(e, "updated_parsed") and e.updated_parsed:
            published = to_iso(e.updated_parsed)
        else:
            published = iso_now()

        items.append({
            "title": title,
            "link": link,
            "summary": summary,
            "source": src,
            "published": published,
        })
    return items

def dedupe(items):
    seen = set()
    out = []
    for it in items:
        k = (it["title"].lower(), it["link"])
        if k in seen:
            continue
        seen.add(k)
        out.append(it)
    return out

def sort_items(items):
    return sorted(items, key=lambda it: it.get("published", ""), reverse=True)

def main():
    all_items = []
    for url in FEEDS:
        try:
            all_items.extend(fetch_feed(url))
        except Exception:
            # keep going; bad feeds shouldn't break the run
            continue

    all_items = dedupe(all_items)
    all_items = sort_items(all_items)[:150]  # cap list size for fast Pages loads

    payload = {
        "updated": iso_now(),
        "sources": CURATED_SOURCES,   # <— hardened dropdown (always present)
        "links": STATIC_LINKS,        # <— hardened quick-link buttons (always present)
        "items": all_items,
    }

    with open("items.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"[collect.py] wrote items.json with {len(all_items)} items at {payload['updated']}")

if __name__ == "__main__":
    main()
