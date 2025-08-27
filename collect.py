#!/usr/bin/env python3
import feedparser, time, json, re
from datetime import datetime, timezone
from pathlib import Path

# ----- knobs you can tune -----
MAX_ITEMS = 120
DATA_PATH = Path("data.json")

SOURCES = [
    # Primary/beat sites
    {"name": "Hammer & Rails", "url": "https://www.hammerandrails.com/rss/index.xml"},
    {"name": "GoldandBlack",   "url": "https://www.on3.com/teams/purdue-boilermakers/feeds/all/atom/"},
    {"name": "ESPN CBB",       "url": "https://www.espn.com/espn/rss/ncb/news"},
    {"name": "CBS CBB",        "url": "https://www.cbssports.com/rss/headlines/college-basketball/"},
    {"name": "Yahoo CBB",      "url": "https://sports.yahoo.com/college-basketball/rss/"},

    # Aggregators (we suppress their summaries to avoid messy blobs)
    {"name": "Google News",    "url": "https://news.google.com/rss/search?q=%22Purdue%20Boilermakers%22%20men%27s%20basketball&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Bing News",      "url": "https://www.bing.com/news/search?q=Purdue+Boilermakers+men%27s+basketball&format=RSS"},

    # YouTube (channels + searches to catch mentions outside those channels)
    {"name": "YouTube: Field of 68",      "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UC8KEey9Gk_wA_w60Y8xX3Zw"},
    {"name": "YouTube: Sleepers Media",   "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCtE2Qt3kFHW2cS7bIMD5zJQ"},
    {"name": "YouTube: Search Purdue MBB","url": "https://www.youtube.com/feeds/videos.xml?search_query=Purdue+men%27s+basketball"},
    {"name": "YouTube: Search Boilermakers","url": "https://www.youtube.com/feeds/videos.xml?search_query=Purdue+Boilermakers+basketball"},

    # Community
    {"name": "Reddit /r/Boilermakers", "url": "https://www.reddit.com/r/Boilermakers/.rss"},
]

# obvious football words/phrases to exclude
EXCLUDE_TERMS = [
    "football","gridiron","quarterback","qb","running back","wide receiver",
    "tight end","offensive line","defensive line","touchdown","field goal",
    "kickoff","punt","nfl","b1g football","college football","pigskin"
]

# what makes a YouTube result “basketball-ish”
YT_KEEP = [
    "purdue","boilermaker","boilermakers","matt painter","painter","zach edey","edey",
    "braden smith","fletcher loyer","trey kaufman","mason gillis","caleb furst","mackey",
    "big ten","ncaa","march","sweet 16","elite eight","final four","boiler ball",
    "men's basketball","mens basketball","basketball"
]

TAG_RE = re.compile(r"<[^>]*>")

def strip_html(s: str) -> str:
    if not s: return ""
    s = TAG_RE.sub("", str(s))
    s = (s.replace("&nbsp;"," ").replace("&amp;","&")
           .replace("&quot;", '"').replace("&#39;","'"))
    return re.sub(r"\s+"," ", s).strip()

def best_summary(entry) -> str:
    for k in ("summary", "description"):
        val = getattr(entry, k, None)
        if isinstance(val, str) and val.strip():
            return strip_html(val)[:500]
    if hasattr(entry, "content") and isinstance(entry.content, list) and entry.content:
        return strip_html(entry.content[0].get("value", ""))[:500]
    return ""

def to_ts(e) -> float:
    for k in ("published_parsed","updated_parsed","created_parsed"):
        if getattr(e, k, None):
            try: return time.mktime(getattr(e, k))
            except Exception: pass
    return time.time()

def is_football(text: str) -> bool:
    t = text.lower()
    return any(x in t for x in EXCLUDE_TERMS)

def youtube_ok(title: str, summary: str) -> bool:
    t = f"{title} {summary}".lower()
    return any(x in t for x in YT_KEEP)

def collect():
    items, seen = [], set()

    for src in SOURCES:
        feed = feedparser.parse(src["url"])
        for e in getattr(feed, "entries", []):
            title = strip_html(getattr(e, "title", ""))[:240]
            link  = getattr(e, "link", "").strip()
            if not title or not link:
                continue

            # keep aggregator titles clean; hide their noisy summaries
            if src["name"] in ("Google News","Bing News"):
                summary = ""
            else:
                summary = best_summary(e)

            # football filter
            if is_football(f"{src['name']} {title} {summary}"):
                continue

            # YouTube gating
            if src["name"].lower().startswith("youtube"):
                if not youtube_ok(title, summary):
                    continue

            ts = to_ts(e)
            key = (title.lower(), link.lower())
            if key in seen:
                continue
            seen.add(key)

            items.append({
                "source": src["name"],
                "title": title,
                "link":  link,
                "summary": summary,
                "ts": ts
            })

    items.sort(key=lambda x: x["ts"], reverse=True)
    items = items[:MAX_ITEMS]

    payload = {
        "modified": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "count": len(items),
        "items": items
    }
    DATA_PATH.write_text(json.dumps(payload, ensure_ascii=False))

if __name__ == "__main__":
    collect()
