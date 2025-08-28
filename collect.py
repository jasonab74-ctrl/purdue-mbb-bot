#!/usr/bin/env python3
"""
Builds items.json (and last-mod.json) at the REPO ROOT.

- Sources include Google News, Bing News, Reddit, and YouTube search RSS
- Filters to Purdue men's basketball (drops football)
- De-duplicates
- Keeps the most recent 200
"""

import datetime as dt
import json
import os
import re
from typing import Dict, List, Tuple
import feedparser

# ----------------------- Config ---------------------------------------------

# News search feeds (RSS)
NEWS_FEEDS: List[Tuple[str, str]] = [
    # Google News (exclude football)
    ("Google News", "https://news.google.com/rss/search?q=(Purdue%20Boilermakers%20men%27s%20basketball%20OR%20Purdue%20basketball)%20-OR%20-football&hl=en-US&gl=US&ceid=US:en"),
    # Bing News
    ("Bing News", "https://www.bing.com/news/search?q=Purdue+Boilermakers+basketball&format=rss"),
    # Hammer & Rails (site-wide; we filter below)
    ("Hammer & Rails", "https://www.hammerandrails.com/rss/index.xml"),
    # Reddit Boilermakers
    ("Reddit r/Boilermakers", "https://www.reddit.com/r/Boilermakers/.rss"),
]

# YouTube search RSS (works without an API key)
YOUTUBE_SEARCH_FEEDS: List[Tuple[str, str]] = [
    ("YouTube — Purdue Basketball", "https://www.youtube.com/feeds/videos.xml?search_query=Purdue+Basketball"),
    ("YouTube — Boilermakers Basketball", "https://www.youtube.com/feeds/videos.xml?search_query=Boilermakers+Basketball"),
]

# How many items to keep
MAX_ITEMS = 200

# Output files (at repo root)
ITEMS_PATH = os.path.join(os.getcwd(), "items.json")
LASTMOD_PATH = os.path.join(os.getcwd(), "last-mod.json")

# ---------------------------------------------------------------------------

_word = r"[A-Za-z0-9']"
RE_PURDUE = re.compile(rf"\bpurdue\b", re.I)
RE_BOILER = re.compile(rf"\bboilermaker{_word}*\b", re.I)
RE_MBB = re.compile(rf"\b(basketball|hoops|mbb)\b", re.I)
RE_FOOTBALL = re.compile(rf"\bfootball\b", re.I)

def is_mbb_hit(title: str, summary: str) -> bool:
    text = f"{title} {summary}".lower()
    if RE_FOOTBALL.search(text):
        return False
    # Strong Purdue + basketball signal
    if (RE_PURDUE.search(text) or RE_BOILER.search(text)) and RE_MBB.search(text):
        return True
    # Heuristic: titles that clearly look like Purdue hoops even if "basketball" missing
    if RE_PURDUE.search(text) and ("painter" in text or "boilermakers" in text):
        return True
    return False

def pull_feed(name: str, url: str) -> List[Dict]:
    d = feedparser.parse(url)
    out: List[Dict] = []
    for e in d.entries:
        title = (getattr(e, "title", "") or "").strip()
        link = (getattr(e, "link", "") or "").strip()
        summary = (getattr(e, "summary", "") or getattr(e, "description", "") or "").strip()
        published = (getattr(e, "published", "") or getattr(e, "updated", "") or getattr(e, "pubDate", "") or "").strip()

        # YouTube: sometimes nicer to construct the canonical watch URL
        if "youtube.com" in url or "feeds/videos.xml" in url:
            vid = getattr(e, "yt_videoid", None) or getattr(e, "videoid", None)
            if vid and ("watch?v=" not in (link or "")):
                link = f"https://www.youtube.com/watch?v={vid}"

        if not title or not link:
            continue
        if not is_mbb_hit(title, summary):
            continue

        out.append({
            "title": title,
            "link": link,
            "summary": summary,
            "source": name,
            "published": published,
        })
    return out

def dedupe(items: List[Dict]) -> List[Dict]:
    seen_links = set()
    seen_titles = set()
    out: List[Dict] = []
    for it in items:
        lk = it["link"].strip().lower()
        tk = it["title"].strip().lower()
        if lk in seen_links or tk in seen_titles:
            continue
        seen_links.add(lk)
        seen_titles.add(tk)
        out.append(it)
    return out

def sort_items(items: List[Dict]) -> List[Dict]:
    def key(it):
        return it.get("published", "")
    return sorted(items, key=key, reverse=True)

def main():
    items: List[Dict] = []
    # News
    for name, url in NEWS_FEEDS:
        items.extend(pull_feed(name, url))
    # YouTube
    for name, url in YOUTUBE_SEARCH_FEEDS:
        items.extend(pull_feed(name, url))

    items = dedupe(items)
    items = sort_items(items)[:MAX_ITEMS]

    # Write outputs
    with open(ITEMS_PATH, "w", encoding="utf-8") as f:
        json.dump({"items": items}, f, ensure_ascii=False)

    with open(LASTMOD_PATH, "w", encoding="utf-8") as f:
        json.dump({"modified": dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")}, f)

    print(f"Wrote {len(items)} items to {ITEMS_PATH}")

if __name__ == "__main__":
    main()
