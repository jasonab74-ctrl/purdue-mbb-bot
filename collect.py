#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Purdue MBB collector (robust + forgiving)
- Works with FEEDS as dicts {"name","url"} or tuples (name,url)
- FILTER CHANGE: For non-trusted feeds, allow if the text clearly mentions Purdue/Boilermakers
  AND does NOT contain strong excludes (like "football"). This prevents zero-results when
  feeds omit the word "basketball" in titles/summaries.
- Still blocks football & other sports unless basketball is obvious.
- Sorts newest-first, dedupes, caps to MAX_ITEMS (50)
- Writes items.json at repo root
- Prints per-feed counts for quick debugging
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
USER_AGENT = "Mozilla/5.0 (Purdue-MBB Collector)"

# ------------ import feeds ------------
try:
    from feeds import FEEDS, STATIC_LINKS  # noqa: F401
    try:
        from feeds import TRUSTED_FEEDS  # optional
    except Exception:
        TRUSTED_FEEDS = set()
except Exception as e:
    raise SystemExit(f"[collect.py] Could not import feeds.py: {e}")

_TRUSTED_LOWER = {s.lower() for s in (TRUSTED_FEEDS or set())}

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

# ------------ filtering ------------

BASKETBALL_SIGNALS = [
    "mbb", "basketball", "men's basketball", "mens basketball", "men’s basketball",
    "matt painter", "painter",
    "edey", "zach edey",
    "braden smith", "fletcher loyer", "loyer",
    "trey kaufman-renn", "kaufman-renn", "tkr",
    "caleb furst", "furst",
    "mason gillis", "gillis",
    "camden heide", "myles colvin", "oscar cluff", "jack benter",
    "omer mayer", "gicarri harris", "raleigh burgess", "daniel jacobsen",
    "liam murphy", "sam king", "aaron fine", "jace rayl", "jack lusk", "c.j. cox", "cj cox"
]

EXCLUDE_STRONG = [
    "football", "fb",
    "wbb", "women's", "women’s", "women basketball", "women’s basketball",
    "volleyball", "softball", "soccer", "baseball", "wrestling", "track",
    "cross country", "golf", "tennis", "swimming", "diving", "hockey",
    "lacrosse", "gymnastics",
]

EXCLUDE_WEAK = ["athletics", "athletic department"]

def _lower_join(*parts: str) -> str:
    return " ".join(p or "" for p in parts).lower().strip()

def allow_item(title: str, summary: str, source_name: str) -> bool:
    """
    Final rules:
      - If strong excludes (football/other sports) appear AND there's no basketball signal → BLOCK.
      - Trusted feeds:
          * Allow if basketball is present, OR (Purdue present AND no strong excludes).
      - Non-trusted feeds (RELAXED to avoid zero-results):
          * Allow if Purdue/Boilermakers present AND no strong excludes.
          * This keeps MBB and neutral Purdue items, while still blocking football by keyword.
      - Weak excludes ("athletics") without basketball won't auto-block if Purdue is present,
        since we're already blocking strong non-MBB sports explicitly.
    """
    text = _lower_join(title, summary)
    source_lower = (source_name or "").lower()

    has_purdue = any(tok in text for tok in ["purdue", "boilermaker", "boilermakers", "boilers"])
    has_basketball = any(tok in text for tok in BASKETBALL_SIGNALS)
    has_strong_exclude = any(tok in text for tok in EXCLUDE_STRONG)
    # has_weak_exclude = any(tok in text for tok in EXCLUDE_WEAK)  # informative only

    is_trusted = (source_name in TRUSTED_FEEDS) or (source_lower in _TRUSTED_LOWER)

    # Hard block strong non-MBB sports unless it's clearly a basketball story (rare mixed cases)
    if has_strong_exclude and not has_basketball:
        return False

    if is_trusted:
        # Trusted may allow basketball, or Purdue without strong excludes
        if has_basketball:
            return True
        return has_purdue and not has_strong_exclude

    # Non-trusted (RELAXED): Purdue mention required; strong excludes blocked
    if has_purdue and not has_strong_exclude:
        return True

    return False

# ------------ parsing helpers ------------

def parse_when(entry: Dict[str, Any]) -> datetime:
    # Try structured times first
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
    # Last resort: now (ensures items still sort and show)
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
