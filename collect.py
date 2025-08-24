# collect.py
# Purdue MEN'S BASKETBALL–only collector with fast timeouts + Reddit support

from __future__ import annotations
import os
import re
import sys
import time
import html
import json
import math
import urllib.parse as urlparse
from datetime import datetime, timezone
from typing import List, Dict, Any

import requests
import feedparser


# ------------ HTTP settings ------------
HTTP_TIMEOUT = (6, 12)  # (connect, read) seconds
HEADERS = {
    "User-Agent": "purdue-mbb-bot/1.0 (+https://purdue-mbb-api.onrender.com)",
    "Accept": "application/rss+xml, application/xml;q=0.9, text/xml;q=0.8, */*;q=0.5",
}

# ------------ Feeds ------------
# Focus on MBB via Google News queries + Hammer & Rails + Reddit searches.
FEEDS: List[str] = [
    # Google News queries (RSS)
    "https://news.google.com/rss/search?q=%22Purdue%20men%27s%20basketball%22&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=Purdue%20Boilermakers%20men%27s%20basketball&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=Purdue%20basketball%20Matt%20Painter&hl=en-US&gl=US&ceid=US:en",
    # SB Nation – Purdue (has multi-sport; we filter to MBB)
    "https://www.hammerandrails.com/rss/index.xml",
    # Reddit searches (RSS)
    "https://www.reddit.com/r/Boilermakers/search.rss?q=Purdue%20men%27s%20basketball&restrict_sr=on&sort=new&t=month",
    "https://www.reddit.com/r/Boilermakers/search.rss?q=mbb%20OR%20basketball&restrict_sr=on&sort=new&t=month",
    "https://www.reddit.com/r/CollegeBasketball/search.rss?q=Purdue&restrict_sr=on&sort=new&t=month",
]

# ------------ Filtering ------------
NEG_WORDS = {
    # other sports
    "football", "nfl", "ross-ade", "soccer", "volleyball", "baseball", "softball",
    "wrestling", "golf", "swim", "swimming", "tennis", "track", "cross country",
    # women’s sports
    "women", "wbb", "women’s", "women's",
    # misc not-news noise
    "parking", "tailgate", "simulcast", "kickoff", "odds for football", "campus police",
}

# Strong signals this IS men’s basketball
POS_PATTERNS = [
    r"\bpurdue\b.*\bmen['’]s?\s+basketball\b",
    r"\bmen['’]s?\s+basketball\b.*\bpurdue\b",
    r"\bpurdue\b.*\bbasketball\b",
    r"\bboilermakers\b.*\bbasketball\b",
    r"\bmatt\s+painter\b",
    r"\bmackey\s+arena\b",
    r"\bmbb\b",
]
POS_REGEXES = [re.compile(p, re.I) for p in POS_PATTERNS]


def _now_ts() -> float:
    return time.time()


def _iso(dt: float) -> str:
    return datetime.fromtimestamp(dt, tz=timezone.utc).isoformat()


def _clean_summary(s: str | None) -> str:
    if not s:
        return ""
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def _canon_url(u: str) -> str:
    try:
        p = urlparse.urlparse(u)
        q = urlparse.parse_qsl(p.query, keep_blank_values=False)
        q = [(k, v) for (k, v) in q if not k.lower().startswith("utm_")]
        new_q = urlparse.urlencode(q, doseq=True)
        return urlparse.urlunparse((p.scheme, p.netloc, p.path, p.params, new_q, ""))
    except Exception:
        return u


def _hostname(u: str) -> str:
    try:
        return urlparse.urlparse(u).netloc.lower()
    except Exception:
        return ""


def parse_rss(url: str):
    """Fetch RSS with explicit timeouts and UA, then parse with feedparser.
    On any error, return an empty, feedparser-like object to keep the pipeline moving."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=HTTP_TIMEOUT)
        resp.raise_for_status()
        return feedparser.parse(resp.content)
    except Exception as e:
        print(f"[rss-skip] {url} -> {e}", file=sys.stderr)
        # Return object with .entries = []
        return type("Obj", (), {"entries": [], "bozo": 1, "bozo_exception": str(e)})


def _entry_pub_ts(entry) -> float:
    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        tm = getattr(entry, key, None) or entry.get(key) if isinstance(entry, dict) else None
        if tm:
            try:
                return time.mktime(tm)
            except Exception:
                pass
    # Fallback to now
    return _now_ts()


def _looks_like_mbb(text: str, host: str) -> bool:
    if any(w in text for w in NEG_WORDS):
        return False
    # Require "purdue" in text to keep general CBB out
    if "purdue" not in text:
        return False
    for rx in POS_REGEXES:
        if rx.search(text):
            return True
    # If from Hammer & Rails or Reddit and it says "purdue" + "basketball", accept
    if host.endswith("hammerandrails.com") or host.endswith("reddit.com"):
        if "basketball" in text or "mbb" in text:
            return True
    return False


def _normalize(entry, src_url: str) -> Dict[str, Any]:
    title = html.unescape(entry.get("title", "")).strip()
    link = _canon_url(entry.get("link") or entry.get("id") or "")
    host = _hostname(link) or _hostname(src_url)
    summary = entry.get("summary") or entry.get("description") or ""
    summary = _clean_summary(summary)
    ts = _entry_pub_ts(entry)

    # source label
    source = "Reddit" if "reddit.com" in host else (host or "source")

    item = {
        "title": title,
        "url": link,
        "link": link,           # alias for UI compatibility
        "site": source,         # alias
        "source": source,
        "source_url": src_url,
        "published": _iso(ts),
        "published_ts": ts,
        "age_hours": round((_now_ts() - ts) / 3600, 2),
        "summary": summary,
        "is_reddit": "reddit.com" in host,
    }
    return item


def collect_all() -> List[Dict[str, Any]]:
    seen: set[str] = set()
    out: List[Dict[str, Any]] = []

    for url in FEEDS:
        feed = parse_rss(url)
        for e in getattr(feed, "entries", []) or []:
            item = _normalize(e, url)
            text = f"{item['title']} {item['summary']}".lower()
            if not _looks_like_mbb(text, _hostname(item["url"])):
                continue

            dedupe_key = (item["title"].strip().lower(), _canon_url(item["url"]))
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            out.append(item)

    # Sort newest first and keep top N
    out.sort(key=lambda x: x["published_ts"], reverse=True)
    limit = int(os.getenv("RESULT_LIMIT", "120"))
    return out[:limit]


def collect_debug() -> Dict[str, Any]:
    """Zero-network debug info (safe to call in /api/debug)."""
    return {
        "cwd": os.getcwd(),
        "env": {"PYTHONPATH": os.getenv("PYTHONPATH")},
        "files_in_app": sorted(os.listdir(".")),
        "glob_py_at_root": sorted([f for f in os.listdir(".") if f.endswith(".py")]),
        "sys_path": sys.path,
        "note": "debug does not fetch network",
    }
