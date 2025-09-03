#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Purdue MBB collector — RESET TO WORK
- Goal: get articles showing again, no over-filtering
- Works with FEEDS as list of dicts {"name","url"} or tuples (name,url)
- Very permissive filter: allow if text mentions Purdue/Boilermakers OR basketball signals
  (NO football/WBB exclusions right now — we’ll add back once you’re stable)
- Sort newest-first, dedupe, cap to MAX_ITEMS (50)
- Writes items.json at repo root
- Prints per-feed counts for quick verification
"""

import os
import json
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Dict, Any, List, Tuple

import feedparser

# ------------ config ------------
MAX_ITEMS = 50
ITEMS_PATH = os.path.join(os.path.dirname(__file__), "items.json")
USER_AGENT = "Mozilla/5.0 (Purdue-MBB Collector Reset)"

# ------------ import feeds ------------
try:
    from feeds import FEEDS, STATIC_LINKS  # noqa: F401
    try:
        from feeds import TRUSTED_FEEDS  # optional, ignored in this reset
    except Exception:
        TRUSTED_FEEDS = set()
except Exception as e:
    raise SystemExit(f"[collect.py] Could not import feeds.py: {e}")

def _coerce_feeds(feeds_any: Any) -> List[Tuple[str, str]]:
    """Accept FEEDS as list of dicts or tuples and return [(name,url), ...]."""
    out: List[Tuple[str, str]] = []
    for item in feeds_any:
        if isinstance(item, dict):
            name = (item.get("name") or item.get("source") or "").strip()
            url = (item.get("url") or "").strip()
        else:
            try:
                name, url = item
                name, url = (name or "").strip(), (url or "").strip()
            except Exception:
                name, url = "", ""
        if name and url:
            out.append((name, url))
    return out

FEEDS_NORM: List[Tuple[str, str]] = _coerce_feeds(FEEDS)

# ------------ permissive filter ------------
# Keep anything clearly Purdue-related OR basketball-related (no hard excludes for now)
KEEP_SIGNALS = [
    "purdue", "boilermaker", "boilermakers", "boilers",
    "basketball", "mbb", "men's basketball", "mens basketball", "men’s basketball",
    "matt painter", "painter",
    "edey", "zach edey",
    "braden smith", "fletcher loyer", "loyer",
    "trey kaufman-renn", "kaufman-renn", "tkr",
    "caleb furst", "furst",
    "mason gillis", "gillis",
    "camden heide", "myles colvin", "oscar cluff", "jack benter",
    "omer mayer", "gicarri harris", "raleigh burgess", "daniel jacobsen",
    "liam murphy", "sam king", "aaron fine", "jace rayl", "jack lusk", "c.j. cox", "cj cox",
]

def _lower_join(*parts: str) -> str:
    return " ".join(p or "" for p in parts).lower().strip()

def allow_item(title: str, summary: str, source_name: str) -> bool:
    text = _lower_join(title, summary)
    return any(tok in text for tok in KEEP_SIGNALS)

# ------------ parsing helpers ------------

def parse_when(entry: Dict[str, Any]) -> datetime:
    # Try structured first
    for key in ("published_parsed", "updated_parsed"):
        dt = entry.get(key)
        if dt:
            try:
                return datetime.fromtimestamp(time.mktime(dt), tz=timezone.utc)
            except Exception:
                pass
    # RFC2822 fallback
    for key in ("published", "updated"):
        val = entry.get(key)
        if val:
            try:
                return parsedate_to_datetime(val).astimezone(timezone.utc)
            except Exception:
                pass
    # Last resort
    return datetime.now(tz=timezone.utc)

def normalize_item(source_name: str, entry: Dict[str, Any]) -> Dict[str, Any]:
    title = (entry.get("title") or "").strip()
    link = (entry.get("link") or "").strip()
    summary = (entry.get("summary") or entry.get("description") or "").strip()
    when = parse_when(entry)
    return {
        "title": title,
        "link": link,
        "source": source_name,
        "summary": summary,
        "published": when.isoformat(),
        "published_ts": int(when.timestamp()),
    }

def dedupe(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen_links = set()
    seen_titles = set()
    out = []
    for it in items:
        key_link = (it.get("link") or "").strip().lower()
        key_title = (it.get("title") or "").strip().lower()
        if key_link and key_link in seen_links:
            continue
        if key_title and key_title in seen_titles:
            continue
        seen_links.add(key_link)
        seen_titles.add(key_title)
        out.append(it)
    return out

# ------------ fetch/collect ------------

def fetch_feed(name: str, url: str) -> List[Dict[str, Any]]:
    parsed = feedparser.parse(url, request_headers={"User-Agent": USER_AGENT})
    entries = parsed.get("entries") or []
    items: List[Dict[str, Any]] = []
    for e in entries:
        item = normalize_item(name, e)
        if allow_item(item["title"], item["summary"], name):
            items.append(item)
    return items

def collect() -> List[Dict[str, Any]]:
    all_items: List[Dict[str, Any]] = []
    for name, url in FEEDS_NORM:
        try:
            batch = fetch_feed(name, url)
            print(f"[collect] {name}: pulled {len(batch)} items")
            all_items.extend(batch)
        except Exception as ex:
            print(f"[collect] Feed failed: {name} ({url}) -> {ex}")
            continue

    # Sort newest → oldest and dedupe
    all_items.sort(key=lambda x: x.get("published_ts", 0), reverse=True)
    all_items = dedupe(all_items)

    # Cap to MAX_ITEMS
    return all_items[:MAX_ITEMS]

def write_items(items: List[Dict[str, Any]], path: str = ITEMS_PATH) -> None:
    payload = {
        "updated": datetime.now(tz=timezone.utc).isoformat(),
        "count": len(items),
        "items": items,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

def main():
    items = collect()
    write_items(items)
    print(f"[collect.py] Wrote {len(items)} items to {ITEMS_PATH}")

if __name__ == "__main__":
    main()
