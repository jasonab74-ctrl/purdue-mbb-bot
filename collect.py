#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Purdue collector — gentle filter + stable pipeline

- Accepts FEEDS as list of dicts {"name","url"} or tuples (name, url)
- Fetch entries with a browser-like UA
- Gentle filter:
    • Block obvious football-only items (unless they clearly mention basketball)
    • Block obvious archive/rankings posts (e.g., 1990–2009 “rankings/poll”)
      ONLY when they do not mention Purdue
    • Keep anything with basketball cues OR Purdue cues
- Normalize, sort newest→oldest, dedupe, cap at MAX_ITEMS (50)
- Write items.json with updated timestamp
"""

import os
import json
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Dict, Any, List, Tuple

import feedparser

MAX_ITEMS = 50
APP_DIR = os.path.dirname(__file__)
ITEMS_PATH = os.path.join(APP_DIR, "items.json")

# Pretend to be a real browser (helps Google/Bing/Reddit)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

# ---- Feeds ----
try:
    from feeds import FEEDS
except Exception as e:
    raise SystemExit(f"[collect.py] Could not import feeds.py: {e}")

def _coerce_feeds(feeds_any: Any) -> List[Tuple[str, str]]:
    """Normalize FEEDS to a list of (name, url)."""
    out: List[Tuple[str, str]] = []
    for item in feeds_any:
        if isinstance(item, dict):
            name = (item.get("name") or item.get("source") or "").strip()
            url  = (item.get("url") or "").strip()
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

# ---- Filter (gentle) ----
BASKETBALL_CUES = [
    "basketball","mbb","men's basketball","mens basketball","men’s basketball",
    "painter","matt painter",
    "edey","zach edey",
    "braden smith","fletcher loyer",
    "trey kaufman-renn","kaufman-renn","tkr",
    "caleb furst","mason gillis","camden heide","myles colvin","oscar cluff",
    "jack benter","omer mayer","gicarri harris","raleigh burgess","daniel jacobsen",
    "liam murphy","sam king","aaron fine","jace rayl","jack lusk","c.j. cox","cj cox"
]
PURDUE_CUES = ["purdue","boilermaker","boilermakers","boilers"]
FOOTBALL_CUES = ["football"," fb "]  # keep minimal, checked against padded text
ARCHIVE_WORDS = ["ranking","rankings","poll","preseason"]

def _txt(*parts: str) -> str:
    return " ".join(p or "" for p in parts).lower()

def allow_item(title: str, summary: str) -> bool:
    """
    Gentle allow-list:
      1) If football-only (no basketball cue) → drop.
      2) If looks like old/other-league rankings (1990–2009 + 'ranking/poll')
         without Purdue mention → drop.
      3) Keep if basketball cues OR Purdue cues present.
      4) Otherwise drop neutral noise.
    """
    t = _txt(title, summary)

    has_ball = any(k in t for k in BASKETBALL_CUES)
    has_pu   = any(k in t for k in PURDUE_CUES)
    has_foot = any(k in f" {t} " for k in FOOTBALL_CUES)

    # (1) Pure football → drop
    if has_foot and not has_ball:
        return False

    # (2) Very gentle archive/rankings block (e.g., 2006/2007 rankings) if no Purdue
    has_archive_word = any(w in t for w in ARCHIVE_WORDS)
    # cover 1990–2009 explicitly (common in archive reposts)
    has_old_year = any(f" {y} " in f" {t} " for y in range(1990, 2010))
    if has_archive_word and has_old_year and not has_pu:
        return False

    # (3) Keep if Purdue or basketball is present
    if has_ball or has_pu:
        return True

    # (4) Otherwise drop neutral clutter
    return False

# ---- Helpers ----
def parse_when(entry: Dict[str, Any]) -> datetime:
    """Parse a date from the feed entry, defaulting to 'now' in UTC."""
    for key in ("published_parsed", "updated_parsed"):
        dt = entry.get(key)
        if dt:
            try:
                return datetime.fromtimestamp(time.mktime(dt), tz=timezone.utc)
            except Exception:
                pass
    for key in ("published", "updated"):
        val = entry.get(key)
        if val:
            try:
                return parsedate_to_datetime(val).astimezone(timezone.utc)
            except Exception:
                pass
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
    seen_links, seen_titles, out = set(), set(), []
    for it in items:
        L = (it.get("link") or "").strip().lower()
        T = (it.get("title") or "").strip().lower()
        if L and L in seen_links:  continue
        if T and T in seen_titles: continue
        seen_links.add(L); seen_titles.add(T); out.append(it)
    return out

def fetch_feed(name: str, url: str) -> List[Dict[str, Any]]:
    parsed = feedparser.parse(url, request_headers={"User-Agent": USER_AGENT})
    entries = parsed.get("entries") or []
    items: List[Dict[str, Any]] = []
    for e in entries:
        item = normalize_item(name, e)
        if allow_item(item["title"], item["summary"]):
            items.append(item)
    return items

def collect() -> List[Dict[str, Any]]:
    """Fetch all feeds, filter, sort, dedupe, cap."""
    all_items: List[Dict[str, Any]] = []
    for name, url in FEEDS_NORM:
        try:
            batch = fetch_feed(name, url)
            print(f"[collect] {name}: kept {len(batch)}")
            all_items.extend(batch)
        except Exception as ex:
            print(f"[collect] Feed failed: {name} ({url}) -> {ex}")
            continue
    all_items.sort(key=lambda x: x.get("published_ts", 0), reverse=True)
    all_items = dedupe(all_items)
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
