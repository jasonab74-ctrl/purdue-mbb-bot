#!/usr/bin/env python3
import os, json, time, datetime, hashlib
from typing import List, Dict, Any
import feedparser

DATA_FILE = "items.json"
LAST_FILE = "last_modified.json"

# ——————————————————————————————————————————————————
# Sources (RSS/ATOM). YouTube feeds are valid ATOM.
# Curated for men’s hoops; Google/Bing queries exclude “football”.
SOURCES: List[Dict[str, str]] = [
    {"name": "Hammer & Rails", "url": "https://www.hammerandrails.com/rss/index.xml"},

    {"name": "Google News",
     "url": "https://news.google.com/rss/search?q=%22Purdue%22%20%22men%27s%20basketball%22%20-football&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Google News",
     "url": "https://news.google.com/rss/search?q=%22Purdue%20Boilermakers%22%20%22men%27s%20basketball%22%20-football&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Bing News",
     "url": "https://www.bing.com/news/search?q=Purdue+Boilermakers+men%27s+basketball+-football&format=RSS"},

    {"name": "ESPN CBB", "url": "https://www.espn.com/espn/rss/ncb/news"},
    {"name": "CBS CBB",  "url": "https://www.cbssports.com/rss/headlines/college-basketball/"},

    # — YouTube channels (videos). Only episodes mentioning “Purdue” will pass the filter.
    {"name": "YouTube: Field of 68",
     "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UC8KEey9Gk_wA_w60Y8xX3Zw"},
    {"name": "YouTube: Sleepers Media",
     "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCtE2Qt3kFHW2cS7bIMD5zJQ"},
]
# ——————————————————————————————————————————————————

# Obvious football tokens we don’t want. (lowercase)
NEGATIVE_KEYWORDS = {
    "football", "cfb", "gridiron", "kickoff", "touchdown",
    "quarterback", "qb", "running back", "receiver", "tight end",
    "defensive line", "offensive line", "secondary",
    "walters", "ross-ade", "spring game", "nfl"
}

# Basketball-positive hints (lowercase). If any are present, we keep the item.
POSITIVE_HINTS = {
    "basketball", "mbb", "ncaa", "men's college basketball", "men’s college basketball",
    "matt painter", "mackey", "purdue hoops", "boiler hoops",
    "zach edey", "braden smith", "fletcher loyer", "lance jones", "tre kaufman", "caleb", "swanigan"
}

def _ts(entry: Any) -> float:
    """Extract a timestamp (epoch) from a feed entry; fall back to now."""
    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        if getattr(entry, key, None):
            try:
                return time.mktime(getattr(entry, key))
            except Exception:
                pass
        if isinstance(entry, dict) and key in entry and entry[key]:
            try:
                return time.mktime(entry[key])
            except Exception:
                pass
    return time.time()

def _hash(link: str) -> str:
    return hashlib.sha256(link.encode("utf-8", "ignore")).hexdigest()[:16]

def _standardize(entry: Any, source_name: str) -> Dict[str, Any]:
    """Normalize a feed entry into our item shape."""
    title = (
        getattr(entry, "title", None)
        or (entry.get("title") if isinstance(entry, dict) else None)
        or ""
    )
    link = (
        getattr(entry, "link", None)
        or (entry.get("link") if isinstance(entry, dict) else None)
        or ""
    )
    summary = (
        getattr(entry, "summary", None)
        or getattr(entry, "description", None)
        or (entry.get("summary") if isinstance(entry, dict) else None)
        or (entry.get("description") if isinstance(entry, dict) else None)
        or ""
    )

    # YouTube links sometimes come as watch URLs in links or via id
    is_video = ("youtube.com" in link) or ("youtu.be" in link)
    if not is_video:
        # YouTube atom entries carry 'yt_videoid' or links in entry.links
        vid = None
        if isinstance(entry, dict):
            vid = entry.get("yt_videoid") or entry.get("yt:videoid")
        else:
            vid = getattr(entry, "yt_videoid", None) or getattr(entry, "yt:videoid", None)
        if vid:
            link = f"https://www.youtube.com/watch?v={vid}"
            is_video = True

    ts = _ts(entry)
    iso = datetime.datetime.utcfromtimestamp(ts).isoformat(timespec="seconds") + "Z"

    return {
        "id": _hash(link or (title + source_name + iso)),
        "title": title.strip(),
        "link": link.strip(),
        "summary": summary.strip(),
        "source": source_name,
        "is_video": bool(is_video),
        "ts": ts,
        "iso": iso,
    }

def _looks_like_basketball(item: Dict[str, Any]) -> bool:
    """Purdue men’s hoops heuristic."""
    text = " ".join([item.get("title",""), item.get("summary",""), item.get("link","")]).lower()

    # must be Purdue-related
    if "purdue" not in text and "boilermaker" not in text:
        return False

    # If football words appear and we don’t see strong hoops hints, drop it.
    if any(w in text for w in NEGATIVE_KEYWORDS) and not any(h in text for h in POSITIVE_HINTS):
        return False

    # Favor hoopsy URLs quickly
    link = item.get("link", "").lower()
    if ("basketball" in link) or ("college-basket" in link) or ("mens-college-basketball" in link):
        return True

    # Otherwise keep if any hoop hints exist
    return any(h in text for h in POSITIVE_HINTS) or "basketball" in text or "mbb" in text

def collect_all() -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    seen_links = set()

    for src in SOURCES:
        try:
            feed = feedparser.parse(src["url"])
            for entry in getattr(feed, "entries", []) or []:
                item = _standardize(entry, src["name"])
                # Drop non-hoops
                if not _looks_like_basketball(item):
                    continue
                # De-dupe by link (or id)
                key = item["link"] or item["id"]
                if key in seen_links:
                    continue
                seen_links.add(key)
                items.append(item)
        except Exception as e:
            # Keep going on bad feeds
            print(f"[collect] Error on {src['name']}: {e}")

    # Sort newest first, cap to ~300
    items.sort(key=lambda x: x["ts"], reverse=True)
    return items[:300]

def save_items(items: List[Dict[str, Any]]) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False)
    with open(LAST_FILE, "w", encoding="utf-8") as f:
        json.dump({"modified": datetime.datetime.utcnow().isoformat(timespec="seconds")}, f)

if __name__ == "__main__":
    data = collect_all()
    save_items(data)
    print(f"[collect] wrote {len(data)} items")
