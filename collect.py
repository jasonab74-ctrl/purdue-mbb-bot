#!/usr/bin/env python3
import json, time, re
from datetime import datetime, timezone
import feedparser

from feeds import FEEDS, STATIC_LINKS, CURATED_SOURCES, TRUSTED_DOMAINS

NOW = datetime.now(timezone.utc)
def iso_now(): return NOW.isoformat()

def to_iso(tp):
    try:
        return datetime.fromtimestamp(time.mktime(tp), tz=timezone.utc).isoformat()
    except Exception:
        return iso_now()

def clean(s): return (s or "").replace("\u200b","").strip()
def domain(href):
    try:
        return re.sub(r"^https?://(www\.)?", "", href).split("/")[0].lower()
    except Exception:
        return ""

# ------------- HARD FILTERS (Purdue MBB only) -------------
NEGATIVE_HARD = re.compile(
    r"\b(football|nfl|volleyball|softball|baseball|soccer|hockey|women'?s|wbb)\b",
    re.I,
)
PURDUE = re.compile(r"\bpurdue\b", re.I)
MBB = re.compile(r"\b(men'?s\s+basketball|basketball|mbb)\b", re.I)

def trusted(h): 
    d = domain(h)
    return any(d.endswith(t) for t in TRUSTED_DOMAINS)

def allow_item(title, summary, href):
    text = f"{title} {summary}"

    # 1) HARD BLOCK negatives ALWAYS (even on trusted domains)
    if NEGATIVE_HARD.search(text):
        return False

    # 2) Must include Purdue somewhere
    if not PURDUE.search(text) and not trusted(href):
        return False

    # 3) Strong bias to men's basketball
    if not MBB.search(text) and not trusted(href):
        return False

    return True
# -----------------------------------------------------------

def grab(url, limit=60):
    d = feedparser.parse(url)
    out = []
    for e in d.entries[:limit]:
        title = clean(getattr(e, "title", ""))
        link  = getattr(e, "link", "")
        if not title or not link: 
            continue

        summary = clean(getattr(e, "summary", "") or getattr(e, "description", ""))
        src = clean(getattr(d.feed, "title", "")) or domain(link)

        if not allow_item(title, summary, link):
            continue

        if getattr(e, "published_parsed", None):
            pub = to_iso(e.published_parsed)
        elif getattr(e, "updated_parsed", None):
            pub = to_iso(e.updated_parsed)
        else:
            pub = iso_now()

        out.append({
            "title": title,
            "link": link,
            "source": src,
            "published": pub
        })
    return out

def dedupe(items):
    seen = set(); out = []
    for it in items:
        k = (it["title"].lower(), it["link"])
        if k in seen: continue
        seen.add(k); out.append(it)
    return out

def sort_desc(items):
    return sorted(items, key=lambda x: x.get("published",""), reverse=True)

def main():
    all_items = []
    for u in FEEDS:
        try:
            all_items.extend(grab(u))
        except Exception:
            continue

    all_items = sort_desc(dedupe(all_items))[:120]

    data = {
        "updated": iso_now(),
        "sources": CURATED_SOURCES,
        "links": STATIC_LINKS,
        "items": all_items
    }
    with open("items.json","w",encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"items.json -> {len(all_items)} stories")

if __name__ == "__main__":
    main()