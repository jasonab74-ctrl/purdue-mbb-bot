#!/usr/bin/env python3
"""
collect.py — fetches RSS, applies Purdue MBB filters, writes items.json

Safe tighten-ups:
- Negative sport words: drop if found and "basketball" not present
- Positive signals require "purdue" and ("basketball" or known MBB entity)
- Mild year guard for stale "Team Rankings" listicles (e.g., 2006/2007)
- 50 item cap
"""

from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Tuple
from urllib.parse import urlparse

import feedparser

# ---- Config -----------------------------------------------------------------

MAX_ITEMS = 50  # cap

# Load feeds/links from feeds.py (default Purdue set)
try:
    from feeds import FEEDS as BASE_FEEDS  # type: ignore
except Exception as e:
    print(f"ERROR importing feeds.py: {e}", file=sys.stderr)
    BASE_FEEDS = []

# Known Purdue MBB entities (coach, arena, current roster bundle)
POSITIVE_ENTITIES = [
    # coach/arena
    "matt painter", "mackey arena",
    # players bundle (keep lowercase)
    "braden smith", "fletcher loyer", "trey kaufman-renn", "jack benter", "omer mayer",
    "gicarri harris", "raleigh burgess", "daniel jacobsen", "oscar cluff", "liam murphy",
    "sam king", "aaron fine", "jace rayl", "jack lusk", "c.j. cox", "cj cox"
]

# Negative sport words we want to block *unless* "basketball" also appears
NEGATIVE_SPORT_WORDS = [
    "football", "volleyball", "softball", "baseball", "soccer", "wbb", "women's", "women’s",
    "womens", "women", "swim", "golf", "track", "tennis", "hockey", "wrestling"
]

# Some sources we treat as "trusted", but still reject obvious non-basketball items.
# Using partials so we can match against the "source" label we attach.
TRUSTED_SOURCE_PARTIALS = [
    "On3", "247Sports", "Rivals", "GoldandBlack", "Hammer & Rails",
    "PurdueSports.com", "Journal & Courier", "Purdue Exponent"
]

# Mild year guard for stale ranking listicles
YEAR_GUARD_RE = re.compile(r"\b(200[0-9]|201[0-4])\b")  # blocks <= 2014 in titles unless basketball is explicit


# ---- Helpers ----------------------------------------------------------------

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_get_time(entry: Any) -> Tuple[float, str]:
    """
    Returns (timestamp, iso_string). Falls back to now if not present.
    """
    # feedparser sets 'published_parsed' or 'updated_parsed'
    dt_struct = entry.get("published_parsed") or entry.get("updated_parsed")
    if dt_struct:
        ts = time.mktime(dt_struct)
        iso = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
        return ts, iso
    # Otherwise try raw strings
    raw = entry.get("published") or entry.get("updated") or ""
    try:
        # last ditch: rely on feedparser's parsed fields if available
        pass
    except Exception:
        pass
    # Fallback: now
    iso = now_iso()
    return time.time(), iso


def domain_from_link(link: str) -> str:
    try:
        return urlparse(link).netloc.lower()
    except Exception:
        return ""


def text_blob(entry: Any) -> str:
    parts = [
        str(entry.get("title", "")),
        str(entry.get("summary", "")),
        str(entry.get("description", "")),
        str(entry.get("source", "")),
    ]
    return " ".join(parts).lower()


def is_trusted_source(source_name: str) -> bool:
    s = source_name.lower()
    return any(p.lower() in s for p in TRUSTED_SOURCE_PARTIALS)


# ---- Filtering ---------------------------------------------------------------

def allow_item(entry: Any, source_name: str) -> bool:
    """
    Tight but safe filter for Purdue Men's Basketball.
    Rules (lowercased comparisons):
      1) If NEGATIVE sport word present AND "basketball" absent => reject.
      2) Require "purdue" present somewhere.
      3) Also require "basketball" OR any POSITIVE_ENTITIES present.
         (Trusted sources still must pass this simple sport/subject check.)
      4) If title looks like old ranking listicles (<= 2014) and "basketball" not present => reject.
    """
    title = str(entry.get("title", "")).strip()
    summary = str(entry.get("summary", "")).strip()
    blob = f"{title}\n{summary}".lower()

    # Rule 1: obvious other-sport blocks unless basketball present
    if any(w in blob for w in NEGATIVE_SPORT_WORDS) and ("basketball" not in blob and "mbb" not in blob):
        return False

    # Require "purdue" somewhere
    if "purdue" not in blob and "boilermaker" not in blob:
        return False

    # Sport/topic positive
    has_bball = ("basketball" in blob) or ("mbb" in blob)
    has_entity = any(name in blob for name in POSITIVE_ENTITIES)

    if not (has_bball or has_entity):
        # Even for trusted sources, still ensure it's hoop-ish
        return False

    # Year guard for ancient listicles (common on team feeds)
    title_lc = title.lower()
    if YEAR_GUARD_RE.search(title_lc) and "basketball" not in title_lc:
        return False

    return True


# ---- Fetch & Build -----------------------------------------------------------

def fetch_feed(url: str) -> feedparser.FeedParserDict:
    # feedparser handles HTTP; simple call is fine
    try:
        return feedparser.parse(url)
    except Exception as e:
        print(f"feed error: {url} -> {e}", file=sys.stderr)
        return feedparser.FeedParserDict(entries=[])


def build_items(feeds: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    seen_links = set()

    for feed in feeds:
        name = feed.get("name", "Source")
        url = feed.get("url", "")
        if not url:
            continue

        parsed = fetch_feed(url)
        for entry in parsed.entries or []:
            link = entry.get("link") or entry.get("id") or ""
            if not link or link in seen_links:
                continue

            if not allow_item(entry, name):
                continue

            ts, iso = safe_get_time(entry)
            title = str(entry.get("title", "")).strip()
            summary = str(entry.get("summary", "")).strip()
            src_label = name
            item = {
                "source": src_label,
                "title": title,
                "link": link,
                "summary": summary,
                "published": iso,
                "ts": ts,
                "domain": domain_from_link(link),
            }
            items.append(item)
            seen_links.add(link)

    # newest first
    items.sort(key=lambda x: x.get("ts", 0), reverse=True)
    # cap
    return items[:MAX_ITEMS]


# ---- Write -------------------------------------------------------------------

def write_items_json(items: List[Dict[str, Any]], path: str = "items.json") -> None:
    payload = {
        "updated": now_iso(),
        "count": len(items),
        "items": [
            {
                "source": it["source"],
                "title": it["title"],
                "link": it["link"],
                "summary": it["summary"],
                "published": it["published"],
            }
            for it in items
        ],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


# ---- Main --------------------------------------------------------------------

def main() -> None:
    # Optional flags for multi-team setups:
    #   --team <slug> : import teams/<slug>/feeds.py
    #   --out  <path> : output path (default items.json)
    feeds = BASE_FEEDS
    out_path = "items.json"

    args = sys.argv[1:]
    if "--team" in args:
        try:
            idx = args.index("--team")
            slug = args[idx + 1]
            mod_name = f"teams.{slug}.feeds"
            team_mod = __import__(mod_name, fromlist=["*"])
            feeds = getattr(team_mod, "FEEDS", feeds)
            # STATIC_LINKS optionally used by the server/template, but not needed here
        except Exception as e:
            print(f"WARNING: could not load team feeds: {e}", file=sys.stderr)

    if "--out" in args:
        try:
            out_path = args[args.index("--out") + 1]
        except Exception:
            pass

    items = build_items(feeds)
    write_items_json(items, out_path)
    print(f"Wrote {len(items)} items -> {out_path}")


if __name__ == "__main__":
    main()