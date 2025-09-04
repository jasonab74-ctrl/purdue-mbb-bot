#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Purdue MBB collector — baseline known-good
- Works with FEEDS as list of dicts {"name","url"} or tuples (name,url)
- Permissive: keep anything that mentions Purdue/Boilermakers OR basketball signals
- If filtered result is EMPTY, it runs a fallback to avoid zero items:
    1) Try a looser include again (same logic).
    2) If still empty, include the newest entries from all feeds UNFILTERED (up to 50).
- Sorts newest-first, dedupes, caps to MAX_ITEMS (50)
- Writes items.json at repo root
- Prints per-feed counts to stdout for debugging
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
APP_DIR = os.path.dirname(__file__)
ITEMS_PATH = os.path.join(APP_DIR, "items.json")
USER_AGENT = "Mozilla/5.0 (Purdue-MBB Collector Baseline)"

# ------------ import feeds ------------
try:
    from feeds import FEEDS, STATIC_LINKS  # noqa: F401
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

def allow_item(title: str, summary: str) -> bool:
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

# ------------ fetch ------------

def fetch_feed(name: str, url: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Returns (filtered_items, raw_items)
    """
    parsed = feedparser.parse(url, request_headers={"User-Agent": USER_AGENT})
    entries = parsed.get("entries") or []
    raw: List[Dict[str, Any]] = []
    keep: List[Dict[str, Any]] = []
    for e in entries:
        item = normalize_item(name, e)
        raw.append(item)
        if allow_item(item["title"], item["summary"]):
            keep.append(item)
    return keep, raw

# ------------ collect ------------

def collect() -> List[Dict[str, Any]]:
    filtered_all: List[Dict[str, Any]] = []
    raw_all: List[Dict[str, Any]] = []

    for name, url in FEEDS_NORM:
        try:
            keep, raw = fetch_feed(name, url)
            print(f"[collect] {name}: {len(keep)} kept / {len(raw)} raw")
            filtered_all.extend(keep)
            raw_all.extend(raw)
        except Exception as ex:
            print(f"[collect] Feed failed: {name} ({url}) -> {ex}")
            continue

    # If nothing kept, FALL BACK to raw (newest first)
    if not filtered_all:
        print("[collect] No filtered items — FALLBACK to raw (unfiltered).")
        raw_all.sort(key=lambda x: x.get("published_ts", 0), reverse=True)
        raw_all = dedupe(raw_all)
        return raw_all[:MAX_ITEMS]

    # Normal path: sort kept newest → oldest and cap
    filtered_all.sort(key=lambda x: x.get("published_ts", 0), reverse=True)
    filtered_all = dedupe(filtered_all)
    return filtered_all[:MAX_ITEMS]

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
