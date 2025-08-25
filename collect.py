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
        return f"{u.netloc}{u.pa
