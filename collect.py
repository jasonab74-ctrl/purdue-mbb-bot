#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Collects articles from FEEDS (feeds.py), filters for Purdue Men's Basketball,
normalizes, sorts newest-first, and writes items.json.

SAFE CHANGE: caps output to the 50 most recent items (configurable via MAX_ITEMS).
"""

import os
import json
import time
from datetime import datetime, timezone
from typing import List, Dict, Any
import feedparser
import requests

from feeds import FEEDS  # list of dicts: {"name": ..., "url": ...}

# ---- Settings ----
OUTPUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "items.json")
TIMEOUT = float(os.environ.get("HTTP_TIMEOUT", "12"))
MAX_ITEMS = int(os.environ.get("MAX_ITEMS", "50"))  # <-- cap (default 50)

# Some feeds are trusted and bypass aggressive keyword checks
TRUSTED_SOURCES = {
    "Hammer & Rails (SB Nation)",
    "PurdueSports.com — “Men’s Basketball”",
    "Reddit — r/Boilermakers",
    "Reddit — r/CollegeBasketball (Purdue search)",
}

# Basic word lists for filtering
KEY_INCLUDE = [
    "purdue",
    "boilermaker",
    "boilermakers",
    "matt painter",
    "mackey",
]
KEY_BBALL = [
    "basketball",
    "mbb",
    "men’s basketball",
    "men's basketball",
]
KEY_EXCLUDE = [
    "football", "volleyball", "softball", "baseball",
    "women’s", "women's", "wbb", "soccer", "w. basketball",
]

# Player/coach names to strengthen recall
PEOPLE = [
    "braden smith", "fletcher loyer", "trey kaufman-renn", "jack benter", "omer mayer",
    "gicarri harris", "raleigh burgess", "daniel jacobsen", "oscar cluff", "liam murphy",
    "sam king", "aaron fine", "jace rayl", "jack lusk", "c.j. cox", "cj cox",
    "matt painter"
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def fetch(url: str) -> bytes:
    """HTTP GET with a short timeout; return raw bytes."""
    r = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": "purdue-mbb-bot/1.0"})
    r.raise_for_status()
    return r.content


def parse_datetime(entry: Dict[str, Any]) -> float:
    """
    Return a unix timestamp (float) for sorting.
    Prefer published_parsed, then updated_parsed, else now.
    """
    ts = None
    for key in ("published_parsed", "updated_parsed"):
        val = entry.get(key)
        if val:
            try:
                ts = time.mktime(val)
                break
            except Exception:
                pass
    if ts is None:
        ts = time.time()
    return float(ts)


def norm_text(x: Any) -> str:
    return (x or "").strip()


def allow_item(title: str, summary: str, source: str) -> bool:
    """
    Filtering: keep strong Purdue MBB relevance; trusted sources bypass.
    """
    t = f"{title} {summary}".lower()

    if source in TRUSTED_SOURCES:
        return True

    if any(ex in t for ex in KEY_EXCLUDE):
        return False

    inc_hit = any(k in t for k in KEY_INCLUDE) or any(p in t for p in PEOPLE)
    bball_hit = any(k in t for k in KEY_BBALL)

    return inc_hit and bball_hit


def normalize(entry: Dict[str, Any], source: str) -> Dict[str, Any]:
    title = norm_text(entry.get("title"))
    link = norm_text(entry.get("link"))
    summary = norm_text(entry.get("summary") or entry.get("description") or "")
    # Some feeds put the site name in link text; keep display clean
    date_ts = parse_datetime(entry)
    dt = datetime.fromtimestamp(date_ts, tz=timezone.utc)
    iso = dt.isoformat(timespec="seconds")
    nice = dt.strftime("%a, %d %b %Y %H:%M:%S GMT")

    return {
        "title": title,
        "link": link,
        "summary": summary,
        "date": nice,
        "ts": date_ts,
        "source": source,
    }


def collect() -> int:
    items: List[Dict[str, Any]] = []

    for feed in FEEDS:
        name = feed.get("name", "Unknown")
        url = feed.get("url")
        if not url:
            continue
        try:
            raw = fetch(url)
            parsed = feedparser.parse(raw)
            for e in parsed.entries:
                # Normalize first (we need title/summary for filtering)
                n = normalize(e, name)
                if allow_item(n["title"], n["summary"], name):
                    items.append(n)
        except Exception as e:
            # Non-fatal; continue other feeds
            print(f"[collect] feed error: {name}: {e}", flush=True)
            continue

    # Sort newest-first and CAP to MAX_ITEMS (default 50)
    items.sort(key=lambda x: x.get("ts", 0.0), reverse=True)
    if MAX_ITEMS > 0:
        items = items[:MAX_ITEMS]

    data = {
        "items": items,
        "meta": {
            "generated_at": utc_now_iso(),
            "count": len(items),
            "max": MAX_ITEMS,
        },
    }

    # Write atomically
    tmp = OUTPUT_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, OUTPUT_PATH)

    print(f"[collect] wrote {len(items)} items (cap={MAX_ITEMS}) → {OUTPUT_PATH}", flush=True)
    return len(items)


if __name__ == "__main__":
    collect()
