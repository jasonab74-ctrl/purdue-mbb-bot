"""
collect.py — fetch feeds and write normalized items.json (newest-first).

Fixes in this version:
- Require a *Purdue-specific* keyword match (no more generic "men's basketball" passes),
  so league/generic pieces like "Horizon League slate" are filtered out.
- Keep strong football/WBB/other-sport excludes (from feeds.py).
- YouTube: keep canonical watch links and include RSS <category> tags in matching
  so Field of 68 / Sleepers videos about Purdue show up reliably.
"""

from pathlib import Path
import time, json, re
from html import unescape
from typing import List, Dict, Tuple
import requests, feedparser

from feeds import FEEDS_META, KEYWORDS_INCLUDE, KEYWORDS_EXCLUDE

OUT_FILE = Path("items.json")
MAX_PER_FEED = 60
TOTAL_MAX = 500
TIMEOUT = 15
UA = "Mozilla/5.0 (X11; Linux x86_64) PurdueMBBBot/1.6 (+https://example.local)"

# Build lists for matching
INC = [k.lower() for k in KEYWORDS_INCLUDE]
EXC = [k.lower() for k in KEYWORDS_EXCLUDE]

# Purdue-specific core tokens (must match at least one of these)
PURDUE_CORE = [
    # program / identity
    "purdue", "boilermaker", "boilermakers", "boilerball", "purdue boilermakers",
    # staff
    "matt painter",
    # 2025–26 roster (names & common variants)
    "c.j. cox", "cj cox",
    "antione west jr", "antione west",
    "fletcher loyer",
    "braden smith",
    "trey kaufman-renn", "tre kaufman-renn",
    "liam murphy",
    "aaron fine",
    "sam king",
    "jack lusk",
    "daniel jacobsen",
    "jack benter",
    "omer mayer",
    "gicarri harris",
    "jace rayl",
    "raleigh burgess",
    "oscar cluff",
]
PURDUE_CORE = [t.lower() for t in PURDUE_CORE]

def _contains_any(text: str, tokens) -> bool:
    t = text.lower()
    return any(tok in t for tok in tokens)

def text_ok(txt: str) -> bool:
    """
    Passes only if:
      - no exclude tokens hit, AND
      - at least one *Purdue-specific* token hits (PURDUE_CORE).
    (We ignore generic "men's basketball" etc. to avoid league/generic posts.)
    """
    if _contains_any(txt, EXC):
        return False
    return _contains_any(txt, PURDUE_CORE)

def norm_date(e) -> str:
    """Return YYYY-MM-DD or ''."""
    if getattr(e, "published_parsed", None):
        tm = e.published_parsed
        return f"{tm.tm_year:04d}-{tm.tm_mon:02d}-{tm.tm_mday:02d}"
    if getattr(e, "updated", None):
        return e.updated.split("T")[0][:10]
    return ""

def clean_html(s: str) -> str:
    return unescape(re.sub("<[^>]+>", " ", s or "").strip())

def parse_feed(url: str):
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT)
        r.raise_for_status()
        return feedparser.parse(r.content)
    except Exception:
        return feedparser.parse(url)  # best-effort fallback

def yt_watch_link(entry) -> str:
    """
    Build a reliable YouTube link.
    Prefer yt_videoid when available; else use entry.link.
    """
    vid = None
    if isinstance(entry, dict):
        vid = entry.get("yt_videoid")
        if not vid:
            mg = entry.get("media_group") or {}
            if isinstance(mg, dict):
                vid = mg.get("yt_videoid")
    link = (getattr(entry, "link", "") or "").strip()
    return f"https://www.youtube.com/watch?v={vid}" if vid else link

def harvest_text_fields(e) -> str:
    """
    Combine likely text fields (title/summary/description/media fields + TAGS)
    so keyword filtering sees YouTube channel tags like 'Purdue', 'Boilermakers', player names.
    """
    parts = [
        getattr(e, "title", ""),
        getattr(e, "summary", "") or getattr(e, "description", "")
    ]
    if isinstance(e, dict):
        for key in ("media_description", "media_title"):
            v = e.get(key)
            if v:
                parts.append(v)
        # Include RSS <category> tags (feedparser -> e.tags[].term)
        tags = e.get("tags") or []
        for tag in tags:
            term = ""
            if isinstance(tag, dict):
                term = tag.get("term") or ""
            else:
                term = getattr(tag, "term", "") or ""
            if term:
                parts.append(term)
    return " ".join([clean_html(p) for p in parts if p])

def score_item(title: str, desc: str, source: str) -> int:
    """Simple relevance score — title matches weigh more."""
    t = (title or "").lower()
    d = (desc or "").lower()
    s = 0
    if "purdue" in t: s += 5
    s += sum(2 for k in PURDUE_CORE if k in t)   # title hits
    s += sum(1 for k in PURDUE_CORE if k in d)   # summary/media/tag hits
    if "purdue athletics" in source.lower(): s += 2
    if "youtube" in source.lower(): s += 1
    return s

def collect() -> List[Dict]:
    ranked: List[Tuple[Dict, int]] = []
    seen_link, seen_title = set(), set()

    for f in FEEDS_META:
        name, url = f["name"], f["url"]
        parsed = parse_feed(url)
        pulled = 0

        for e in parsed.entries:
            title = (getattr(e, "title", "") or "").strip()
            if not title:
                continue

            # Robust link (esp. for YouTube)
            link = (getattr(e, "link", "") or "").strip()
            if "youtube" in name.lower():
                link = yt_watch_link(e) or link
            if not link:
                continue

            # Build blob for filtering (now includes tags)
            desc = clean_html(getattr(e, "summary", "") or getattr(e, "description", ""))
            blob = harvest_text_fields(e)
            fulltext = f"{title} {blob}"

            if not text_ok(fulltext):
                continue

            key_title = re.sub(r"\s+", " ", title.lower())
            if link in seen_link or key_title in seen_title:
                continue

            item = {
                "title": title,
                "link": link,
                "source": name,
                "date": norm_date(e),
                "description": (desc[:280] + ("…" if len(desc) > 280 else "")) if desc else ""
            }
            score = score_item(title, desc, name)

            ranked.append((item, score))
            seen_link.add(link)
            seen_title.add(key_title)
            pulled += 1
            if pulled >= MAX_PER_FEED:
                break

        print(f"[collector] {name}: {pulled} items")
        time.sleep(0.2)  # be polite

    # Newest-first, then by score; undated at bottom
    def date_key(it: Dict) -> str:
        return it.get("date") or "0000-00-00"

    ranked.sort(key=lambda pair: (date_key(pair[0]), pair[1]), reverse=True)
    return [it for it, _ in ranked][:TOTAL_MAX]

def main():
    try:
        items = collect()
    except Exception as e:
        print(f"[collector] ERROR: {e}")
        items = []
    OUT_FILE.write_text(json.dumps({"items": items}, indent=2), encoding="utf-8")
    print(f"[collector] Wrote {len(items)} items to {OUT_FILE}")

if __name__ == "__main__":
    main()
