#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Purdue MBB Live Feed — collector
- Pulls RSS feeds from feeds.py (articles + YouTube mentions via Google News)
- Applies include/exclude filters to avoid football & non-MBB noise
- Dedupes, sorts newest->oldest, writes items.json at repo root
- Side-effect free for server.py; no interface changes
"""

import json
import os
import re
import time
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

import feedparser  # type: ignore
import requests    # type: ignore

# ---- Project config (from feeds.py) -----------------------------------------
try:
    from feeds import FEEDS, STATIC_LINKS, KEYWORDS_INCLUDE, KEYWORDS_EXCLUDE, MAX_ITEMS_PER_FEED, ALLOW_DUPLICATE_DOMAINS, SOURCE_ALIASES
except Exception:
    # Minimal fallbacks so the script never crashes if feeds.py changes
    FEEDS = []
    STATIC_LINKS = []
    KEYWORDS_INCLUDE = ["purdue", "boilermakers", "men's basketball", "mens basketball", "ncaa", "matt painter", "mackey arena"]
    KEYWORDS_EXCLUDE = ["football", "cfb", "quarterback", "nfl", "volleyball", "soccer", "baseball", "softball"]
    MAX_ITEMS_PER_FEED = 50
    ALLOW_DUPLICATE_DOMAINS = False
    SOURCE_ALIASES = {}

# -----------------------------------------------------------------------------

ROOT = os.path.dirname(os.path.abspath(__file__))
ITEMS_PATH = os.path.join(ROOT, "items.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (PurdueMBBFeed/1.0; +https://example.invalid) Python/requests",
    "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8",
}

TIMEOUT = 15

INCLUDE_RE = re.compile("|".join([re.escape(k) for k in KEYWORDS_INCLUDE]), re.IGNORECASE)
EXCLUDE_RE = re.compile("|".join([re.escape(k) for k in KEYWORDS_EXCLUDE]), re.IGNORECASE)

YOUTUBE_HOSTS = ("youtube.com", "youtu.be")

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def to_iso(dt_struct) -> str:
    """Convert feedparser time struct -> ISO8601; fallback to now."""
    try:
        if not dt_struct:
            return now_iso()
        ts = time.mktime(dt_struct)
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    except Exception:
        return now_iso()

def normalize_link(url: str) -> str:
    if not url:
        return ""
    # Trim tracking params to improve dedupe (keep YouTube t= param)
    try:
        from urllib.parse import urlparse, parse_qsl, urlunparse, urlencode
        u = urlparse(url)
        q = dict(parse_qsl(u.query, keep_blank_values=True))
        if any(h in u.netloc for h in YOUTUBE_HOSTS):
            # Keep time parameter for YT deep-links, drop others
            q = {k: v for k, v in q.items() if k in ("t", "time_continue")}
        else:
            q = {}
        return urlunparse((u.scheme, u.netloc, u.path, u.params, urlencode(q), "")) or url
    except Exception:
        return url

def domain_of(url: str) -> str:
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc.lower()
    except Exception:
        return ""

def text_of(entry: Dict[str, Any]) -> str:
    parts = []
    for k in ("title", "summary", "description"):
        v = entry.get(k)
        if isinstance(v, str):
            parts.append(v)
    return " ".join(parts)

def passes_filters(entry: Dict[str, Any], source_name: str) -> bool:
    """Require at least one include term; reject if any exclude term matched.
       For Reddit CBB, require explicit 'purdue' mention in title to be strict."""
    text = text_of(entry)
    if not INCLUDE_RE.search(text):
        return False
    if EXCLUDE_RE.search(text):
        return False
    # Stricter rule for r/CollegeBasketball noise
    if "CollegeBasketball" in source_name and not re.search(r"\bpurdue\b", entry.get("title", ""), re.IGNORECASE):
        return False
    return True

def entry_to_item(entry: Dict[str, Any], source_name: str) -> Dict[str, Any]:
    title = entry.get("title") or "Untitled"
    link = normalize_link(entry.get("link") or entry.get("id") or "")
    # Prefer published, then updated, else now
    iso = to_iso(entry.get("published_parsed") or entry.get("updated_parsed"))

    # Prefer feed's declared source name; alias if provided
    source = SOURCE_ALIASES.get(source_name, source_name)

    # Short summary
    summary = entry.get("summary") or entry.get("description") or ""
    summary = re.sub(r"\s+", " ", summary).strip()

    # If the link is a Google News redirect, keep as-is (browser will redirect)
    # Tag YouTube for nicer badges if desired (UI can still show 'source')
    host = domain_of(link)
    if any(h in host for h in YOUTUBE_HOSTS) and "YouTube" not in source:
        source = f"YouTube — {source}"

    return {
        "title": title,
        "link": link,
        "date": iso,
        "source": source,
        "summary": summary[:600],  # keep payload small
    }

def fetch_feed(url: str) -> feedparser.FeedParserDict:
    # requests first (better TLS/redirects), fallback to feedparser’s built-in
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        return feedparser.parse(resp.content)
    except Exception:
        return feedparser.parse(url)

def collect() -> Tuple[List[Dict[str, Any]], List[str]]:
    items: List[Dict[str, Any]] = []
    errors: List[str] = []
    seen_links = set()
    seen_domains = set()

    for f in FEEDS:
        name = f.get("name", "Feed")
        url = f.get("url")
        if not url:
            continue
        try:
            parsed = fetch_feed(url)
            entries = parsed.entries or []
            count = 0
            for e in entries:
                if not passes_filters(e, name):
                    continue
                itm = entry_to_item(e, name)
                if not itm["link"]:
                    continue
                # Dedup by link
                if itm["link"] in seen_links:
                    continue
                # Optional domain dedupe to avoid floods from same site
                if not ALLOW_DUPLICATE_DOMAINS:
                    d = domain_of(itm["link"])
                    key = (name, d)
                    if d and key in seen_domains:
                        continue
                    if d:
                        seen_domains.add(key)

                seen_links.add(itm["link"])
                items.append(itm)
                count += 1
                if count >= max(5, int(MAX_ITEMS_PER_FEED)):
                    break
        except Exception as ex:
            errors.append(f"{name}: {ex}")
            traceback.print_exc()

    # Sort newest first (ISO timestamps sort lexicographically as well, but be safe)
    items.sort(key=lambda x: x.get("date") or "", reverse=True)

    # Soft cap overall size
    items = items[:400]

    return items, errors

def write_items(items: List[Dict[str, Any]]):
    payload = {"items": items, "generated_at": now_iso()}
    tmp = ITEMS_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp, ITEMS_PATH)

def main():
    items, errors = collect()
    write_items(items)
    # Optionally print to logs (Railway shows STDOUT)
    print(json.dumps({
        "ok": True,
        "count": len(items),
        "errors": errors,
        "ts": now_iso()
    }))

if __name__ == "__main__":
    main()
