#!/usr/bin/env python3
"""
Purdue MBB collector — hardened
- Pulls from a fixed list of basketball-focused feeds (see feeds.py)
- Normalizes source names so the dropdown stays stable
- Filters OUT football and unrelated posts
- Writes items.json with: {updated, items:[{title,link,source,published}]}
"""
from datetime import datetime, timezone
import json, time, hashlib
import feedparser

from feeds import FEEDS

# Canonical source names (keeps dropdown stable)
CANON = {
    "Hammer and Rails": "Hammer and Rails",
    "Journal & Courier": "Journal & Courier",
    "GoldandBlack.com": "GoldandBlack.com",
    "The Athletic": "The Athletic",
    "ESPN": "ESPN",
    "Yahoo Sports": "Yahoo Sports",
    "Sports Illustrated": "Sports Illustrated",
    "CBS Sports": "CBS Sports",
    "Big Ten Network": "Big Ten Network",
    "AP Top 25": "AP Top 25",
    "Google News": "Google News",
}

# Terms that strongly indicate FOOTBALL or non-MBB
EXCLUDE_ANY = [
    "football", "pigskin", "qb", "quarterback", "running back", "linebacker",
    "tight end", "ross-ade", "gridiron", "ncaa football", "cfb", "b1g football",
    "drew brees", "kickoff", "touchdown",
]

# Soft MBB terms (we’ll require at least one when “purdue” is present)
INCLUDE_ANY = [
    "basketball", "mbb", "boilermakers", "matt painter", "zach edey",
    "mackey", "big ten", "b1g", "ncaa", "hoops", "guard", "forward", "center",
]

def text_in(s, words):
    s = (s or "").lower()
    return any(w in s for w in words)

def allow_item(title, summary, source_name):
    t = (title or "") + " " + (summary or "")
    l = t.lower()

    # Hard reject football/non-MBB
    if text_in(l, EXCLUDE_ANY):
        return False

    # Must relate to Purdue
    if "purdue" not in l and "boilermaker" not in l and "mackey" not in l:
        return False

    # If it doesn’t explicitly say “basketball”, allow if it matches other MBB context
    if ("basketball" not in l) and (not text_in(l, INCLUDE_ANY)):
        return False

    return True

def canonical_source(name):
    if not name:
        return "Unknown"
    # Exact map first
    if name in CANON:
        return CANON[name]
    # Heuristics
    lower = name.lower()
    if "hammer and rails" in lower: return "Hammer and Rails"
    if "journal" in lower and "courier" in lower: return "Journal & Courier"
    if "goldandblack" in lower: return "GoldandBlack.com"
    if "athletic" in lower: return "The Athletic"
    if "sports illustrated" in lower or "si.com" in lower: return "Sports Illustrated"
    if "yahoo" in lower: return "Yahoo Sports"
    if "espn" in lower: return "ESPN"
    if "cbs sports" in lower: return "CBS Sports"
    if "big ten network" in lower or "btn" in lower: return "Big Ten Network"
    if "news.google" in lower: return "Google News"
    return name.strip()

def parse_time(entry):
    # try multiple places
    if getattr(entry, "published_parsed", None):
        return int(time.mktime(entry.published_parsed))
    if getattr(entry, "updated_parsed", None):
        return int(time.mktime(entry.updated_parsed))
    return int(time.time())

def main():
    items = []
    seen_links = set()

    for name, url in FEEDS:
        d = feedparser.parse(url)
        for e in d.entries:
            title = getattr(e, "title", "") or ""
            summary = getattr(e, "summary", "") or getattr(e, "description", "") or ""
            link = getattr(e, "link", "") or ""
            if not link:
                continue
            # de-dupe by link hash
            h = hashlib.sha1(link.encode("utf-8")).hexdigest()
            if h in seen_links:
                continue

            source = canonical_source(name or getattr(d.feed, "title", "") or "")
            if not allow_item(title, summary, source):
                continue

            seen_links.add(h)
            items.append({
                "title": title.strip(),
                "link": link,
                "source": source,
                "published": parse_time(e),
            })

    # Sort newest first
    items.sort(key=lambda x: x["published"], reverse=True)

    payload = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "items": items[:250],  # cap for payload size
    }

    with open("items.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()