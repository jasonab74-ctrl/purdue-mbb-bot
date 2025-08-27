#!/usr/bin/env python3
"""
Collect Purdue MBB news into items.json (and last_modified.json).

- Robust YouTube parsing (Field of 68 + Sleepers Media)
- Basketball-only focus: keeps Purdue hoops, filters football
- Writes a flat list consumed by /api/items
"""

import json, re, time, datetime
from pathlib import Path
import feedparser

# ------------------ SOURCES ------------------
SOURCES = [
    {"name": "Hammer & Rails", "url": "https://www.hammerandrails.com/rss/index.xml"},
    {"name": "Google News", "url": "https://news.google.com/rss/search?q=%22Purdue%22%20%22men%27s%20basketball%22&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Google News", "url": "https://news.google.com/rss/search?q=%22Purdue%20Boilermakers%22%20basketball&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Bing News", "url": "https://www.bing.com/news/search?q=Purdue+Boilermakers+men%27s+basketball&format=RSS"},
    {"name": "ESPN CBB", "url": "https://www.espn.com/espn/rss/ncb/news"},
    {"name": "CBS CBB", "url": "https://www.cbssports.com/rss/headlines/college-basketball/"},
    # YouTube channels (videos)
    {"name": "YouTube: Field of 68", "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UC8KEey9Gk_wA_w60Y8xX3Zw"},
    {"name": "YouTube: Sleepers Media", "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCtE2Qt3kFHW2cS7bIMD5zJQ"},
]

# -------------- FILTERS (keep hoops, drop FB) --------------
GOOD = re.compile(
    r"""
    \b(
        purdue|boiler(?:maker|makers)?|boilers|
        painter|mackey|paint[-\s]?crew|
        edey|zach\s*edey|lance\s*jones|fletcher\s*loyer|braden\s*smith|
        big\s*ten\s*titles?|\bmatt\s*painter\b
    )\b
    """,
    re.I | re.X,
)

BAD = re.compile(
    r"\b(football|nfl|qb|quarterback|tight\s*end|running\s*back|kickoff|touchdown|spring\s*game)\b",
    re.I,
)

# Extra helper to relax “Purdue” requirement for **channel** videos:
YOUTUBE_ALWAYS_VIDEO = {"YouTube: Field of 68", "YouTube: Sleepers Media"}

# -------------- Helpers --------------
def _clean(s: str) -> str:
    if not s:
        return ""
    return re.sub(r"\s+", " ", str(s)).strip()

def _entry_datetime(e) -> str:
    # ISO string we can sort on later; fallbacks are fine
    for k in ("published", "updated", "created", "issued"):
        v = e.get(k)
        if v:
            return v
    # feedparser also exposes *_parsed; we can convert to ISO if present
    for k in ("published_parsed", "updated_parsed"):
        t = e.get(k)
        if t:
            try:
                return time.strftime("%Y-%m-%dT%H:%M:%S", t)
            except Exception:
                pass
    return ""

def _youtube_link(e, default=None):
    # Try standard 'link'
    link = e.get("link")
    if link:
        return link
    # Try links array
    links = e.get("links") or []
    for L in links:
        if L.get("href") and (L.get("rel") in (None, "alternate")):
            return L["href"]
    # Build from video id if present
    vid = (
        e.get("yt_videoid")
        or e.get("yt_video_id")
        or (e.get("id", "").split(":")[-1] if "youtube" in (default or "").lower() else None)
    )
    if vid:
        return f"https://www.youtube.com/watch?v={vid}"
    return default

def _summary_from_entry(e):
    # YouTube often uses media:description
    return _clean(
        e.get("summary")
        or e.get("media_description")
        or (e.get("summary_detail") or {}).get("value")
        or ""
    )

def _looks_like_bball(text: str, source_name: str) -> bool:
    if BAD.search(text):
        return False
    if GOOD.search(text):
        return True
    # If it's from our YouTube Hoops channels, allow items that mention basketball topics
    if source_name in YOUTUBE_ALWAYS_VIDEO:
        # Still avoid obvious FB
        if BAD.search(text):
            return False
        # Let broader hoops chatter through even if "Purdue" isn’t in title
        hoops_hint = re.search(r"\b(basketball|hoops|big\s*ten|ncaa|cbb)\b", text, re.I)
        return bool(hoops_hint)
    return False

# -------------- Collector --------------
def collect():
    items = []
    for src in SOURCES:
        name, url = src["name"], src["url"]
        try:
            feed = feedparser.parse(url)
        except Exception:
            continue

        for e in feed.entries:
            title = _clean(e.get("title") or "")
            summary = _summary_from_entry(e)
            link = _clean(_youtube_link(e, default=e.get("link") or ""))
            published = _entry_datetime(e)

            if not title or not link:
                continue

            blob = f"{title} {summary}"
            if not _looks_like_bball(blob, name):
                continue

            is_video = "youtube.com" in link or "youtu.be" in link or "youtube" in url.lower()
            items.append(
                {
                    "source": name,
                    "title": title,
                    "summary": summary,
                    "link": link,
                    "iso": published,
                    "is_video": bool(is_video),
                }
            )

    # Dedupe by (title, link)
    seen = set()
    deduped = []
    for it in items:
        key = (it["title"].lower(), it["link"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(it)

    # Sort newest first (fall back to title when iso missing)
    def _sort_key(x):
        return (x.get("iso") or "", x.get("title") or "")
    deduped.sort(key=_sort_key, reverse=True)

    Path("items.json").write_text(json.dumps(deduped, ensure_ascii=False), encoding="utf-8")
    Path("last_modified.json").write_text(
        json.dumps({"modified": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")}),
        encoding="utf-8",
    )

if __name__ == "__main__":
    collect()
