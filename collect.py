#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Purdue MBB collector
- Fetches feeds from feeds.py: FEEDS (list of (name, url)) and optional TRUSTED_FEEDS (set of names)
- Strictly filters for Purdue Men's Basketball
- Explicitly excludes football (and other non-MBB sports) unless the text clearly indicates basketball
- Sorts newest-first and caps at MAX_ITEMS (default 50)
- Writes items.json in repo root
"""

import os
import json
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Dict, Any, List, Tuple

import feedparser

# ---- config ----
MAX_ITEMS = 50
ITEMS_PATH = os.path.join(os.path.dirname(__file__), "items.json")
USER_AGENT = "Mozilla/5.0 (Purdue-MBB Collector; +https://example.local)"

# ---- feeds ----
try:
    # Expected: FEEDS = [("Source Name", "https://...rss"), ...]
    # Optional: TRUSTED_FEEDS = {"Gold and Black", "Field of 68", ...}
    from feeds import FEEDS, STATIC_LINKS  # noqa: F401 (STATIC_LINKS not used here)
    try:
        from feeds import TRUSTED_FEEDS  # type: ignore
    except Exception:
        TRUSTED_FEEDS = set()
except Exception as e:
    raise SystemExit(f"[collect.py] Could not import feeds.py: {e}")

# ---- filtering helpers ----

INCLUDE_ALL = [
    "purdue", "boilermaker", "boilermakers", "boilers",
    "mbb", "men's basketball", "mens basketball", "men’s basketball",
    "basketball",
    # coach + player signals
    "matt painter", "painter",
    "zach edey", "edey",
    "braden smith", "smith",  # 'smith' is common; it will still require 'purdue' nearby in practice
    "fletcher loyer", "loyer",
    "trey kaufman-renn", "kaufman-renn", "tkr",
    "caleb furst", "furst",
    "mason gillis", "gillis",
    "lance jones", "camden heide", "myles colvin",
]

# terms that strongly indicate the content is *not* MBB
# (we still allow if headline clearly contains basketball)
EXCLUDE_STRONG = [
    "football", "fb",
    "wbb", "women's", "women’s", "women basketball", "women’s basketball",
    "volleyball", "softball", "soccer", "baseball", "wrestling", "track",
    "cross country", "golf", "tennis", "swimming", "diving", "hockey",
    "lacrosse", "gymnastics",
]

# generic department term that often shows up in all-sports posts
EXCLUDE_WEAK = [
    "athletics", "athletic department",
]

BASKETBALL_SIGNALS = [
    "mbb", "basketball", "men's basketball", "mens basketball", "men’s basketball",
    "matt painter", "painter", "edey", "zach edey",
    "braden smith", "loyer", "kaufman-renn", "furst", "gillis",
]

def _lower_join(*parts: str) -> str:
    return " ".join(p or "" for p in parts).lower().strip()

def allow_item(title: str, summary: str, source_name: str) -> bool:
    """
    Decision:
    - Always lowercase inputs.
    - If source is trusted:
        * allow if it's clearly basketball OR Purdue MBB names.
        * still BLOCK if it explicitly says "football" (or other strong excludes) and doesn't also say basketball.
    - For non-trusted:
        * require 'purdue' AND any basketball signal (e.g., 'basketball' or player/coach)
        * reject if strong excludes appear without basketball context
        * weak excludes like 'athletics' are rejected unless basketball is present
    """
    text = _lower_join(title, summary)
    source_lower = (source_name or "").lower()

    has_purdue = "purdue" in text or "boilermaker" in text or "boilermakers" in text or "boilers" in text
    has_basketball = any(tok in text for tok in BASKETBALL_SIGNALS)
    has_strong_exclude = any(tok in text for tok in EXCLUDE_STRONG)
    has_weak_exclude = any(tok in text for tok in EXCLUDE_WEAK)

    is_trusted = source_name in TRUSTED_FEEDS or source_lower in {s.lower() for s in TRUSTED_FEEDS}

    # If it's clearly basketball, we can allow (trusted or not), provided it's Purdue-linked for non-trusted.
    if has_basketball:
        if is_trusted:
            # Even for trusted, block explicit football/etc if basketball is *not* present (but we *are* present here),
            # so trusted + basketball => allow.
            return True
        else:
            return has_purdue  # must still be Purdue-related for non-trusted

    # Not clearly basketball… apply exclusions strongly.
    if has_strong_exclude:
        # Any strong non-MBB sport mention => reject.
        return False

    if has_weak_exclude and not has_basketball:
        # Generic "athletics" or department posts without any basketball hint => reject.
        return False

    # Trusted feeds can sometimes post neutral items (e.g., schedule notes). Be conservative:
    if is_trusted:
        # Only allow if at least Purdue mention AND NOT a strong exclude
        return has_purdue and not has_strong_exclude

    # Default for non-trusted: require both Purdue + some MBB signal (which we don't have), so reject.
    return False

# ---- parsing helpers ----

def parse_when(entry: Dict[str, Any]) -> datetime:
    # Try published, then updated, else now
    for key in ("published_parsed", "updated_parsed"):
        dt = entry.get(key)
        if dt:
            try:
                # feedparser gives time.struct_time
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

# ---- fetch ----

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
    for name, url in FEEDS:
        try:
            batch = fetch_feed(name, url)
            all_items.extend(batch)
        except Exception as ex:
            # Don't crash the whole collector for one bad feed
            print(f"[collect] Feed failed: {name} ({url}) -> {ex}")
            continue

    # sort newest → oldest and dedupe
    all_items.sort(key=lambda x: x.get("published_ts", 0), reverse=True)
    all_items = dedupe(all_items)

    # cap to MAX_ITEMS
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
