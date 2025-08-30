#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Purdue MBB — resilient collector
- Broad GN coverage + retries/backoff
- Strict football filtering; CBB reddit requires 'Purdue' in title
- Cleans HTML; dedup by link; per-domain throttling
- Newest-first
- Guardrails so we NEVER overwrite with a weak/empty pass
"""

import json, os, re, time, traceback
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

import feedparser  # type: ignore
import requests    # type: ignore
from html import unescape

# ---- Config from feeds.py ----------------------------------------------------
try:
    from feeds import (
        FEEDS, STATIC_LINKS,
        KEYWORDS_INCLUDE, KEYWORDS_EXCLUDE,
        MAX_ITEMS_PER_FEED, ALLOW_DUPLICATE_DOMAINS, SOURCE_ALIASES,
        DOMAIN_PER_FEED_LIMIT,
    )
except Exception:
    FEEDS = []
    STATIC_LINKS = []
    KEYWORDS_INCLUDE = ["purdue","boilers","boilermakers","men's basketball","ncaa","matt painter","mackey"]
    KEYWORDS_EXCLUDE = ["football","cfb","quarterback","nfl"]
    MAX_ITEMS_PER_FEED = 120
    ALLOW_DUPLICATE_DOMAINS = False
    DOMAIN_PER_FEED_LIMIT = 4
    SOURCE_ALIASES = {}

ROOT = os.path.dirname(os.path.abspath(__file__))
ITEMS_PATH = os.path.join(ROOT, "items.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (PurdueMBBFeed/1.3) Python/requests",
    "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8",
}
TIMEOUT = 25
RETRIES = 3
BACKOFF_BASE = 1.6

INCLUDE_RE = re.compile("|".join([re.escape(k) for k in KEYWORDS_INCLUDE]), re.IGNORECASE)
EXCLUDE_RE = re.compile("|".join([re.escape(k) for k in KEYWORDS_EXCLUDE]), re.IGNORECASE)
YOUTUBE_HOSTS = ("youtube.com","youtu.be")

def now_iso() -> str: return datetime.now(timezone.utc).isoformat()

def to_iso(dt_struct) -> str:
    try:
        if not dt_struct: return now_iso()
        ts = time.mktime(dt_struct)
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    except Exception:
        return now_iso()

def normalize_link(url: str) -> str:
    if not url: return ""
    try:
        from urllib.parse import urlparse, parse_qsl, urlunparse, urlencode
        u = urlparse(url)
        q = dict(parse_qsl(u.query, keep_blank_values=True))
        if any(h in u.netloc for h in YOUTUBE_HOSTS):
            q = {k:v for k,v in q.items() if k in ("t","time_continue")}
        else:
            q = {}
        return urlunparse((u.scheme,u.netloc,u.path,u.params, urlencode(q), "")) or url
    except Exception:
        return url

def domain_of(url: str) -> str:
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc.lower()
    except Exception:
        return ""

def clean_html(s: str) -> str:
    if not s: return ""
    s = re.sub(r"<[^>]+>", " ", s)
    s = unescape(re.sub(r"\s+", " ", s)).strip()
    return s

def text_of(entry: Dict[str, Any]) -> str:
    parts=[]
    for k in ("title","summary","description"):
        v = entry.get(k)
        if isinstance(v,str): parts.append(v)
    return " ".join(parts)

def passes_filters(entry: Dict[str, Any], source_name: str) -> bool:
    text = text_of(entry)
    if not INCLUDE_RE.search(text): return False
    if EXCLUDE_RE.search(text): return False
    if "CollegeBasketball" in source_name and not re.search(r"\bpurdue\b", entry.get("title",""), re.IGNORECASE):
        return False
    return True

def entry_to_item(entry: Dict[str, Any], source_name: str) -> Dict[str, Any]:
    title = entry.get("title") or "Untitled"
    link = normalize_link(entry.get("link") or entry.get("id") or "")
    iso = to_iso(entry.get("published_parsed") or entry.get("updated_parsed"))
    source = SOURCE_ALIASES.get(source_name, source_name)
    summary = clean_html(entry.get("summary") or entry.get("description") or "")
    host = domain_of(link)
    if any(h in host for h in YOUTUBE_HOSTS) and "YouTube" not in source:
        source = f"YouTube — {source}"
    return {"title": title, "link": link, "date": iso, "source": source, "summary": summary[:600]}

def fetch_bytes_with_retries(url: str) -> bytes:
    last = None
    for i in range(RETRIES):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp.content
        except Exception as e:
            last = e
           
