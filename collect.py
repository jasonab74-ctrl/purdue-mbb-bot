# collect.py
#
# Fetch Purdue Men's Basketball (MBB) items from a handful of sources,
# filter for MBB-only, and return a cached-ready payload.

from __future__ import annotations
import time
import html
import re
from typing import List, Dict, Any, Tuple
import requests
import feedparser
from urllib.parse import urlparse

# ---------- HTTP config ----------
UA = "purdue-mbb-bot/1.0 (+https://purdue-mbb-api.onrender.com)"
REQ_TIMEOUT = (5, 10)  # connect, read seconds
REQ_HEADERS = {"User-Agent": UA, "Accept": "application/rss+xml,application/atom+xml;q=0.9,*/*;q=0.8"}

# ---------- Sources ----------
SOURCES: List[Tuple[str, str]] = [
    ("Hammer & Rails", "https://www.hammerandrails.com/rss/index.xml"),
    ("Journal & Courier Purdue", "https://rss.app/feeds/2iN670v7t9C1p7dS.xml"),
    ("Sports Illustrated (Purdue)", "https://www.si.com/college/purdue/.rss"),
    ("Purdue Exponent", "https://www.purdueexponent.org/search/?f=atom&c=news%2Csports&t=article"),
    ("GoldandBlack", "https://www.on3.com/feeds/goldandblack/purdue/"),
    # Reddit (can rate-limit; we add strong UA and accept skips on 429)
    ("Reddit r/Boilermakers", "https://www.reddit.com/r/Boilermakers/search.rss?q=Purdue%20men%27s%20basketball&restrict_sr=on&sort=new&t=month"),
]

# ---------- Filtering ----------
NEGATIVE = [
    "football", "women's", "womens", "women’s", "soccer", "volleyball", "baseball", "softball",
    "hockey", "wrestling", "golf", "tennis", "track", "cross country", "swim", "swimming"
]

# Current / recent MBB names + coach + arena keywords.
NAMES = [
    "matt painter", "mackey arena", "braden smith", "fletcher loyer", "myles colvin",
    "caleb furst", "trey kaufman", "camden heide", "lance jones", "mason gillis", "zach edey",
    "zach edey", "z. edey", "purdue commit", "boilermakers guard", "boilermakers forward"
]

POSITIVE = ["basketball", "men's basketball", "mens basketball", "mbb", "boiler ball", "boilermaker ball"] + NAMES

MAX_AGE_DAYS = 120  # only keep reasonably recent items


def _now_ms() -> int:
    return int(time.time() * 1000)


def _req_bytes(url: str) -> bytes | None:
    try:
        r = requests.get(url, headers=REQ_HEADERS, timeout=REQ_TIMEOUT, allow_redirects=True)
        if r.status_code == 429:
            # Too many requests (Reddit often does this). Just skip gracefully.
            return None
        r.raise_for_status()
        return r.content
    except Exception:
        return None


def parse_rss(url: str) -> feedparser.FeedParserDict | None:
    raw = _req_bytes(url)
    if not raw:
        return None
    try:
        return feedparser.parse(raw)
    except Exception:
        return None


def _text(*parts: Any) -> str:
    s = " ".join([str(p) for p in parts if p])
    s = html.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _is_recent(entry: feedparser.FeedParserDict) -> bool:
    # Accept entries without dates, but prefer recent ones.
    try:
        tm = entry.get("published_parsed") or entry.get("updated_parsed")
        if not tm:
            return True
        ts = int(time.mktime(tm))  # seconds
        age_days = (time.time() - ts) / 86400.0
        return age_days <= MAX_AGE_DAYS
    except Exception:
        return True


def _host_key(link: str) -> str:
    try:
        u = urlparse(link)
        return f"{u.netloc}{u.path}".lower()
    except Exception:
        return link.lower()


def is_mbb_relevant(title: str, summary: str, link: str) -> bool:
    t = _text(title, summary, link).lower()

    # Hard negative filter
    for n in NEGATIVE:
        if f" {n} " in f" {t} ":
            return False

    # Require basketball context or known MBB names
    has_basketball = "basketball" in t or "men's basketball" in t or "mens basketball" in t or "mbb" in t
    has_purdue = "purdue" in t or "boilermaker" in t or "boilermakers" in t

    if has_basketball and has_purdue:
        return True

    for p in POSITIVE:
        if p in t and has_purdue:
            return True

    # Some sources are Purdue-only; allow generic “basketball” without repeating “Purdue”
    if has_basketball:
        return True

    return False


def collect_all() -> Dict[str, Any]:
    items: List[Dict[str, Any]] = []
    seen: set[str] = set()
    debug_sources: List[Dict[str, Any]] = []

    for name, url in SOURCES:
        fetched = 0
        kept = 0

        d = parse_rss(url)
        if d and d.entries:
            fetched = len(d.entries)
            for e in d.entries:
                title = e.get("title", "")
                summary = e.get("summary", "") or e.get("subtitle", "") or ""
                link = e.get("link", "")
                if not link:
                    continue
                if not _is_recent(e):
                    continue
                if not is_mbb_relevant(title, summary, link):
                    continue

                key = _host_key(link)
                if key in seen:
                    continue
                seen.add(key)

                # Date handling
                pub = None
                try:
                    tm = e.get("published_parsed") or e.get("updated_parsed")
                    if tm:
                        pub_ms = int(time.mktime(tm) * 1000)
                        pub = pub_ms
                except Exception:
                    pub = None

                source_title = d.feed.get("title", name) if d and getattr(d, "feed", None) else name
                items.append({
                    "title": _text(title),
                    "link": link,
                    "source": source_title,
                    "summary": _text(summary),
                    "published": pub,          # ms since epoch or None
                })
                kept += 1

        debug_sources.append({
            "name": name,
            "url": url,
            "fetched": fetched,
            "kept": kept,
        })

    # Sort newest first (fallback to now for missing dates)
    now_ms = _now_ms()
    items.sort(key=lambda x: x.get("published") or now_ms, reverse=True)

    payload = {
        "count": len(items),
        "items": items,
        "sources": debug_sources,
        "updated": now_ms,  # **milliseconds** for the UI
    }
    return payload


def collect_debug_empty() -> Dict[str, Any]:
    """A minimal empty payload used before the first refresh completes."""
    return {"count": 0, "items": [], "sources": [{"name": n, "url": u, "fetched": 0, "kept": 0} for n, u in SOURCES], "updated": 0}
