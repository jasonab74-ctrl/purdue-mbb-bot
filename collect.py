# collect.py  — unified feed collector for Purdue Men's Basketball News
# ---------------------------------------------------------------
# - Adds Yahoo Sports (via Google News site filter)
# - Includes Hammer & Rails, ESPN NCB, CBS CBB, Barstool, On3/GoldandBlack
# - Google/Bing news searches, Reddit, YouTube channels + searches
# - De-dupes, normalizes, and filters to Purdue MEN'S basketball
#
# After editing, deploy and run:
#   GET  /api/refresh-now?key=YOUR_REFRESH_KEY
# or POST with header X-Refresh-Key

import os
import re
import time
import json
import html
import hashlib
from datetime import datetime, timezone

import requests
import feedparser

DATA_FILE = "data.json"
USER_AGENT = "purdue-mbb-bot/1.0 (+https://purdue-mbb-api-2.onrender.com)"
TIMEOUT = 20

# ---------------------------------------------------------------
# 🔧 Sources (RSS/Atom). Keep names short; URLs must be RSS/ATOM.
# ---------------------------------------------------------------
SOURCES = [
    # Core Purdue
    {"name": "Hammer & Rails", "url": "https://www.hammerandrails.com/rss/index.xml"},

    # Broad news (two flavors of Google News for better coverage)
    {"name": "Google News", "url": "https://news.google.com/rss/search?q=%22Purdue%22%20%22men%27s%20basketball%22&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Google News", "url": "https://news.google.com/rss/search?q=%22Purdue%20Boilermakers%22%20basketball&hl=en-US&gl=US&ceid=US:en"},

    # Bing News (often surfaces different outlets)
    {"name": "Bing News", "url": "https://www.bing.com/news/search?q=Purdue+Boilermakers+men%27s+basketball&format=RSS"},

    # Major CBB wires
    {"name": "ESPN CBB", "url": "https://www.espn.com/espn/rss/ncb/news"},
    {"name": "CBS CBB",  "url": "https://www.cbssports.com/rss/headlines/college-basketball/"},

    # Yahoo Sports via Google News site filter (Yahoo no longer exposes stable RSS)
    {"name": "Yahoo Sports", "url": "https://news.google.com/rss/search?q=site:sports.yahoo.com%20Purdue%20basketball&hl=en-US&gl=US&ceid=US:en"},

    # GoldandBlack/On3 + Barstool via site filters
    {"name": "GoldandBlack", "url": "https://news.google.com/rss/search?q=site:on3.com%20Purdue%20basketball&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Barstool",      "url": "https://news.google.com/rss/search?q=site:barstoolsports.com%20Purdue%20basketball&hl=en-US&gl=US&ceid=US:en"},

    # Community
    {"name": "Reddit", "url": "https://www.reddit.com/r/Boilermakers/.rss"},

    # YouTube — channels
    {"name": "YouTube: Field of 68", "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UC8KEey9Gk_wA_w60Y8xX3Zw"},
    {"name": "YouTube: Sleepers Media", "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCtE2Qt3kFHW2cS7bIMD5zJQ"},

    # YouTube — searches (pull relevant Purdue videos from ANY channel)
    {"name": "YouTube Search", "url": "https://www.youtube.com/feeds/videos.xml?search_query=Purdue+basketball"},
    {"name": "YouTube Search", "url": "https://www.youtube.com/feeds/videos.xml?search_query=Purdue+Boilermakers+basketball"},
]

# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------

_re_whitespace = re.compile(r"\s+")
_re_html_tag = re.compile(r"<[^>]+>")
_re_youtube = re.compile(r"(youtube\.com|youtu\.be)", re.I)

NAMES = [
    "matt painter", "zach edey", "edey", "braden smith", "fletcher loyer",
    "trey kaufman", "lance jones", "caleb first", "mason gillis", "myles colvin",
    "camden", "riddell", "b1g", "big ten", "mackey"
]

def fetch_bytes(url: str) -> bytes:
    r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
    r.raise_for_status()
    return r.content

def norm_text(s: str) -> str:
    if not s:
        return ""
    s = html.unescape(s)
    s = _re_html_tag.sub("", s)
    s = _re_whitespace.sub(" ", s)
    return s.strip()

def to_epoch(entry) -> int:
    t = None
    for key in ("published_parsed", "updated_parsed"):
        if getattr(entry, key, None):
            t = getattr(entry, key)
            break
    if t:
        try:
            return int(time.mktime(t))
        except Exception:
            pass
    # Fallback to now to keep ordering sane
    return int(time.time())

def is_youtube(source_name: str, link: str) -> bool:
    if source_name.lower().startswith("youtube"):
        return True
    return bool(_re_youtube.search(link or ""))

def is_basketball_item(source_name: str, title: str, summary: str) -> bool:
    """
    Heuristic filter for MEN'S basketball + Purdue.
    """
    t = f"{title} {summary}".lower()

    # Fast-path drops
    if "football" in t and "basketball" not in t:
        return False
    if "women" in t or "wbb" in t or "women's" in t:
        # Keep women’s basketball out for now per project scope
        return False

    has_purdue = "purdue" in t or "boilermaker" in t or "boilers" in t
    has_hoops  = "basketball" in t or "mbb" in t or "ncaa" in t

    # Looser for YouTube to catch talk shows/pods
    if is_youtube(source_name, ""):
        return has_purdue or any(n in t for n in NAMES) or "big ten" in t or "b1g" in t

    # News/wires: require Purdue and either hoops or program/name hints
    if has_purdue and (has_hoops or any(n in t for n in NAMES) or "mackey" in t):
        return True

    # Occasionally Google/Bing include generic CBB lists/awards; allow with Purdue mention
    if has_purdue and ("rank" in t or "poll" in t or "award" in t or "preseason" in t):
        return True

    return False

def fingerprint(link: str, title: str) -> str:
    base = (link or "").strip() or (title or "").strip()
    return hashlib.sha1(base.encode("utf-8", "ignore")).hexdigest()

def normalize_item(feed_name: str, entry) -> dict:
    title = norm_text(getattr(entry, "title", "") or "")
    link  = getattr(entry, "link", "") or ""

    # summary content preference
    summary = ""
    if getattr(entry, "content", None):
        try:
            summary = entry.content[0].value
        except Exception:
            pass
    if not summary:
        summary = getattr(entry, "summary", "") or ""
    summary = norm_text(summary)

    ts = to_epoch(entry)
    src = feed_name or "RSS"

    return {
        "title": title or "(untitled)",
        "link": link,
        "summary_text": summary,
        "published_ts": ts,
        "source": src,
    }

def collect() -> list:
    items = []
    seen = set()

    for src in SOURCES:
        name = src["name"]
        url  = src["url"]
        try:
            raw = fetch_bytes(url)
            parsed = feedparser.parse(raw)
        except Exception:
            continue

        # Prefer the configured name; if YouTube channel exposes a good title, append
        feed_title = parsed.feed.title if getattr(parsed, "feed", None) and getattr(parsed.feed, "title", None) else ""
        label = name
        if name.startswith("YouTube:") and feed_title and "Uploads" not in feed_title:
            # e.g., "YouTube: Field of 68 – Rob Dauster" (nice but keep short)
            label = name

        for e in parsed.entries:
            itm = normalize_item(label, e)
            fp = fingerprint(itm["link"], itm["title"])
            if fp in seen:
                continue
            seen.add(fp)

            if is_basketball_item(label, itm["title"], itm["summary_text"]):
                items.append(itm)

    # Sort newest first
    items.sort(key=lambda x: x.get("published_ts", 0), reverse=True)
    return items

def save(items: list):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False)

# ---------------------------------------------------------------
# CLI support
# ---------------------------------------------------------------
if __name__ == "__main__":
    data = collect()
    save(data)
    print(f"Saved {len(data)} items to {DATA_FILE}")
