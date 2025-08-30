#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Purdue MBB — fail-safe collector with host-aware headers + debug titles
- Real Chrome UA
- Adds proper Referer for Google News / Bing News so they don't return empty bodies
- Pass 1: topic/roster/player matching (football excluded)
- If < 30 items, Pass 2: LENIENT (accept any non-football from your feeds)
- Freshness window 365d by default (set FRESH_DAYS env to change)
- Writes items.json atomically with a rich last_run block (seen/kept/meta/debug_titles)
"""

import json, os, re, time, traceback
from datetime import datetime, timezone, timedelta
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
    KEYWORDS_INCLUDE = ["purdue","boilers","boilermakers","basketball","ncaa","painter","mackey","roster"]
    KEYWORDS_EXCLUDE = ["football","qb","nfl"]
    MAX_ITEMS_PER_FEED = 200
    ALLOW_DUPLICATE_DOMAINS = True
    DOMAIN_PER_FEED_LIMIT = 999
    SOURCE_ALIASES = {}

# -----------------------------------------------------------------------------
# Player keywords (this-year roster + notable recent)
PLAYER_KEYWORDS_DEFAULT = [
    "braden smith", "fletcher loyer", "trey kaufman", "trey kaufman-renn",
    "mason gillis", "caleb furst", "myles colvin", "camden heide", "will berg",
    "matt painter", "zach edey"
]
EXTRA = os.environ.get("PLAYER_EXTRA", "").strip()
if EXTRA:
    PLAYER_KEYWORDS = PLAYER_KEYWORDS_DEFAULT + [s.strip().lower() for s in EXTRA.split(",") if s.strip()]
else:
    PLAYER_KEYWORDS = PLAYER_KEYWORDS_DEFAULT

ROOT = os.path.dirname(os.path.abspath(__file__))
ITEMS_PATH = os.path.join(ROOT, "items.json")

# Browser-like headers
BASE_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/125.0 Safari/537.36"),
    "Accept": "application/rss+xml, application/atom+xml, application/xml;q=0.9, text/xml;q=0.8, */*;q=0.7",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Connection": "close",
}
TIMEOUT = 25
RETRIES = 3
BACKOFF_BASE = 1.7

# Freshness window (days). You can tune with env FRESH_DAYS.
FRESH_DAYS = int(os.environ.get("FRESH_DAYS", "365"))

# Build regexes
INCLUDE_TERMS = (KEYWORDS_INCLUDE or []) + PLAYER_KEYWORDS
CORE_INCLUDE_RE = re.compile(
    r"\b(purdue|boilers?|boilermakers?|boilerball|basketball|ncaa|painter|mackey|roster)\b"
    r"|2025[\-—–]26|class of 2025|class of 2026",
    re.IGNORECASE,
)
INCLUDE_RE = re.compile("|".join([re.escape(k) for k in INCLUDE_TERMS]), re.IGNORECASE)
EXCLUDE_RE = re.compile("|".join([re.escape(k) for k in (KEYWORDS_EXCLUDE or [])]), re.IGNORECASE)
YOUTUBE_HOSTS = ("youtube.com","youtu.be")

TARGETED_FEED_HINTS = (
    "purdue","boiler","mackey","matt painter","youtube","r/boilermakers",
    "bing news","google news","hammer & rails"
)

def now_iso() -> str: return datetime.now(timezone.utc).isoformat()

def domain_of(url: str) -> str:
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc.lower()
    except Exception:
        return ""

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

def to_iso(dt_struct) -> str:
    try:
        if not dt_struct: return now_iso()
        ts = time.mktime(dt_struct)
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    except Exception:
        return now_iso()

def too_old(iso: str) -> bool:
    try:
        dt = datetime.fromisoformat(iso.replace("Z","+00:00"))
        return (datetime.now(timezone.utc) - dt) > timedelta(days=FRESH_DAYS)
    except Exception:
        return False

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

def feed_is_targeted(feed_name: str) -> bool:
    n = (feed_name or "").lower()
    return any(h in n for h in TARGETED_FEED_HINTS)

def passes_filters(entry: Dict[str, Any], source_name: str, *, lenient: bool) -> bool:
    txt = text_of(entry)
    # Always block football/other excluded sports
    if EXCLUDE_RE.search(txt):
        return False
    if lenient:
        # Fail-safe: accept anything non-football
        return True
    if feed_is_targeted(source_name): return True
    if CORE_INCLUDE_RE.search(txt):  return True
    if INCLUDE_RE.search(txt):       return True
    return False

def entry_to_item(entry: Dict[str, Any], source_name: str) -> Dict[str, Any]:
    title = entry.get("title") or "Untitled"
    link  = normalize_link(entry.get("link") or entry.get("id") or "")
    iso   = to_iso(entry.get("published_parsed") or entry.get("updated_parsed"))
    source= SOURCE_ALIASES.get(source_name, source_name)
    summary = clean_html(entry.get("summary") or entry.get("description") or "")
    host = domain_of(link)
    if any(h in host for h in YOUTUBE_HOSTS) and "YouTube" not in source:
        source = f"YouTube — {source}"
    return {"title": title, "link": link, "date": iso, "source": source, "summary": summary[:600]}

# ---------- host-aware fetch with diagnostics ----------
def _headers_for(url: str) -> Dict[str,str]:
    h = dict(BASE_HEADERS)
    host = domain_of(url)
    if "news.google.com" in host:
        h["Referer"] = "https://news.google.com/"
    elif "bing.com" in host:
        h["Referer"] = "https://www.bing.com/news"
    elif "reddit.com" in host:
        # reddit can be picky; plain Chrome UA is usually fine, but this helps
        h["Accept"] = "*/*"
    return h

def fetch_bytes_with_retries(url: str):
    last_exc = None
    for i in range(RETRIES):
        try:
            resp = requests.get(url, headers=_headers_for(url), timeout=TIMEOUT, allow_redirects=True)
            return resp.content or b"", resp.status_code
        except Exception as e:
            last_exc = e
        time.sleep(BACKOFF_BASE ** i)
    if last_exc: raise last_exc
    return b"", 0

def fetch_feed_with_meta(url: str):
    meta = {"http": None, "bytes": 0, "error": None}
    try:
        data, code = fetch_bytes_with_retries(url)
        meta["http"]  = int(code) if code else None
        meta["bytes"] = len(data)
        if data:
            parsed = feedparser.parse(data)
        else:
            parsed = feedparser.parse(url)
        entries = parsed.entries or []
        return entries, meta
    except Exception as e:
        meta["error"] = str(e)
        try:
            parsed = feedparser.parse(url)
            entries = parsed.entries or []
            return entries, meta
        except Exception as e2:
            meta["error"] = f"{meta['error']} | fp:{e2}"
            return [], meta

# ---------- persistence ----------
def write_items_with_meta(items: List[Dict[str, Any]], last_run: Dict[str, Any]):
    payload = {
        "items": items,
        "generated_at": now_iso(),
        "last_run": last_run,
        "items_mtime": now_iso(),
    }
    tmp = ITEMS_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp, ITEMS_PATH)

def load_previous() -> Dict[str, Any]:
    if not os.path.exists(ITEMS_PATH):
        return {"items": [], "generated_at": now_iso(), "last_run": {}}
    try:
        with open(ITEMS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"items": [], "generated_at": now_iso(), "last_run": {}}

# ---------- collection ----------
def collect_pass(*, lenient: bool):
    items: List[Dict[str, Any]] = []
    errors: List[str] = []
    per_feed_kept: Dict[str,int] = {}
    per_feed_seen: Dict[str,int] = {}
    per_feed_meta: Dict[str,
