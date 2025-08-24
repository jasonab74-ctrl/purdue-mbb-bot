# collect.py
import os
import re
import time
import json
import html
import math
import email.utils as eut
from datetime import datetime, timezone
from typing import List, Dict

import requests
import feedparser

# ---------- CONFIG ----------
# Required env var for YouTube:
# export YOUTUBE_API_KEY="YOUR_YOUTUBE_API_KEY"
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

# RSS feeds with frequent Purdue hoops coverage
FEEDS = [
    # Purdue official / local / team-specific
    "https://purduesports.com/rss.aspx?path=mbball",  # Purdue MBB (official site)
    "https://www.jconline.com/search/?q=Purdue%20basketball&output=rss",  # Lafayette Journal & Courier search
    # Major outlets with Purdue tags or team pages (many expose RSS)
    "https://www.on3.com/feeds/team/purdue-boilermakers/",
    "https://www.si.com/.rss/full/purdue-boilermakers",
    "https://www.sbnation.com/rss/team/purdue-boilermakers/index.xml",  # often Hammer & Rails content
    # Add more if you like (247, Rivals, BTN, IndyStar tag pages if they expose RSS)
]

# Subreddits to scan (we filter for Purdue in code)
REDDIT_SR = [
    "Boilermakers",
    "CollegeBasketball",
]

# YouTube filtering: we don’t need channel IDs.
# We search broadly for “Purdue basketball” and then keep only allowed channels.
YOUTUBE_CHANNEL_ALLOW = [
    "Field of 68",
    "Sleepers Media",
    "BoilerUpload",          # Rivals video brand
    "Purdue Athletics",
    "PurdueSports",
    "BTN",
    "Big Ten Network",
    "BoilerBall",            # historical Purdue hoops content
]

# Accept if *either* the title/description hits these words OR channel is in allowlist
TEAM_KEYWORDS = [
    "Purdue", "Boilermaker", "Boilermakers", "Boiler", "Boilers",
    "MBB", "men's basketball", "men’s basketball", "NCAA", "Big Ten",
    # common current names (kept generic—adjust anytime)
    "Matt Painter", "Braden Smith", "Fletcher Loyer", "Caleb Furst", "Trey Kaufman",
    "Mason Gillis", "Smith", "Loyer", "Kaufman", "Furst"
]
# ---------- END CONFIG ----------

HTTP_TIMEOUT = 20
UA = {"User-Agent": "purdue-mbb-feed/1.0 (+https://github.com/yourrepo)"}

def _parse_date_guess(s: str) -> str:
    """Return ISO 8601 string; fall back to now if unknown."""
    if not s:
        return datetime.now(timezone.utc).isoformat()
    # Try RFC 2822 (common in RSS)
    try:
        ts = eut.parsedate_to_datetime(s)
        if not ts.tzinfo:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts.isoformat()
    except Exception:
        pass
    # Try raw ISO
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if not dt.tzinfo:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()

def _clean_text(s: str) -> str:
    return html.unescape((s or "").strip())

def _looks_purdue(text: str) -> bool:
    t = text.lower()
    for k in TEAM_KEYWORDS:
        if k.lower() in t:
            return True
    return False

def fetch_rss() -> List[Dict]:
    items = []
    for url in FEEDS:
        try:
            feed = feedparser.parse(url)
            for e in feed.entries[:30]:
                title = _clean_text(getattr(e, "title", ""))
                link = getattr(e, "link", "")
                if not title or not link:
                    continue
                # Prefer basketball posts only
                summary = _clean_text(getattr(e, "summary", ""))[:400]
                if not (_looks_purdue(title) or _looks_purdue(summary)):
                    # If feed itself is highly Purdue-specific, you could keep everything;
                    # but we’ll be strict to avoid off-topic posts.
                    continue
                pub = (
                    getattr(e, "published", None)
                    or getattr(e, "updated", None)
                    or getattr(e, "published_parsed", None)
                )
                published_at = _parse_date_guess(str(pub))
                items.append({
                    "title": title,
                    "url": link,
                    "published_at": published_at,
                    "source": "News",
                })
        except Exception:
            continue
    return items

def fetch_reddit() -> List[Dict]:
    out = []
    for sr in REDDIT_SR:
        try:
            url = f"https://www.reddit.com/r/{sr}/new.json?limit=25"
            r = requests.get(url, headers=UA, timeout=HTTP_TIMEOUT)
            r.raise_for_status()
            for child in r.json().get("data", {}).get("children", []):
                d = child.get("data", {})
                title = _clean_text(d.get("title", ""))
                if not title:
                    continue
                # Require Purdue-ish
                if not _looks_purdue(title):
                    # also peek at selftext
                    if not _looks_purdue(_clean_text(d.get("selftext", ""))):
                        continue
                permalink = d.get("permalink", "")
                created_utc = d.get("created_utc", None)
                if created_utc is None:
                    published_at = datetime.now(timezone.utc).isoformat()
                else:
                    published_at = datetime.fromtimestamp(created_utc, tz=timezone.utc).isoformat()
                out.append({
                    "title": title,
                    "url": f"https://reddit.com{permalink}" if permalink else "https://reddit.com",
                    "published_at": published_at,
                    "source": f"Reddit r/{sr}",
                })
        except Exception:
            continue
    return out

def fetch_youtube() -> List[Dict]:
    if not YOUTUBE_API_KEY:
        return []
    results = []
    # Strategy: search Purdue basketball, newest first; filter to allowed channels or Purdue-ish text
    # Run a couple of slightly different queries to broaden coverage
    queries = ["Purdue basketball", "Purdue Boilermakers basketball", "Purdue MBB"]
    seen_ids = set()
    for q in queries:
        try:
            url = (
                "https://www.googleapis.com/youtube/v3/search"
                f"?key={YOUTUBE_API_KEY}"
                "&part=snippet"
                "&order=date"
                "&type=video"
                "&maxResults=25"
                f"&q={requests.utils.quote(q)}"
            )
            r = requests.get(url, timeout=HTTP_TIMEOUT)
            r.raise_for_status()
            for it in r.json().get("items", []):
                vid = it.get("id", {}).get("videoId")
                if not vid or vid in seen_ids:
                    continue
                snippet = it.get("snippet", {})
                title = _clean_text(snippet.get("title", ""))
                desc = _clean_text(snippet.get("description", ""))
                ch = _clean_text(snippet.get("channelTitle", ""))
                when = _parse_date_guess(snippet.get("publishedAt", ""))
                # Keep if channel is allowlisted OR content looks Purdue
                allowed_channel = any(ch.lower() == a.lower() for a in YOUTUBE_CHANNEL_ALLOW)
                if not (allowed_channel or _looks_purdue(title) or _looks_purdue(desc)):
                    continue
                results.append({
                    "title": title,
                    "url": f"https://www.youtube.com/watch?v={vid}",
                    "published_at": when,
                    "source": ch if ch else "YouTube",
                })
                seen_ids.add(vid)
        except Exception:
            continue
    return results

def _dedupe(items: List[Dict]) -> List[Dict]:
    seen = set()
    out = []
    for x in items:
        key = (x.get("title", "").strip().lower(), x.get("url", "").strip().lower())
        if key in seen: 
            continue
        seen.add(key)
        out.append(x)
    return out

def collect_all() -> List[Dict]:
    all_items = []
    all_items.extend(fetch_rss())
    all_items.extend(fetch_reddit())
    all_items.extend(fetch_youtube())
    all_items = _dedupe(all_items)
    # Sort newest first
    all_items.sort(key=lambda i: i.get("published_at", ""), reverse=True)
    # Trim to a sensible number
    return all_items[:200]

if __name__ == "__main__":
    data = collect_all()
    print(json.dumps(data, indent=2))
