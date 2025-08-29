"""
collect.py — fetch feeds and write normalized items.json (newest-first).

This version:
- Keeps strict football/WBB/other-sport excludes.
- Requires a Purdue-specific match (program/coach/roster tokens).
- For Reddit r/CollegeBasketball, require a Purdue match specifically in the TITLE
  (prevents generic league threads from passing).
- For YouTube channels (Field of 68, Sleepers), include RSS tags and do a short,
  capped HTML peek when RSS fields don't carry Purdue but the watch page does.
"""

from pathlib import Path
import time, json, re
from html import unescape
from typing import List, Dict, Tuple
from urllib.parse import urlparse

import requests, feedparser
from feeds import FEEDS_META, KEYWORDS_EXCLUDE

OUT_FILE = Path("items.json")
MAX_PER_FEED          = 60
TOTAL_MAX             = 500
TIMEOUT               = 15
UA                    = "Mozilla/5.0 (X11; Linux x86_64) PurdueMBBBot/1.9 (+https://example.local)"
YT_PEEK_TIMEOUT       = 4     # seconds per YouTube HTML peek
YT_PEEK_MAX_PER_FEED  = 8     # cap per channel per run

# Purdue-specific tokens (must match at least one)
PURDUE_CORE = [
    "purdue", "purdue boilermakers", "boilermaker", "boilermakers", "boilerball",
    "matt painter",
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
EXC = [k.lower() for k in KEYWORDS_EXCLUDE]

def _contains_any(text: str, tokens) -> bool:
    t = text.lower()
    return any(tok in t for tok in tokens)

def passes_core_filter(text: str) -> bool:
    """Require a Purdue-specific token and no excluded tokens."""
    t = text.lower()
    if any(x in t for x in EXC):
        return False
    return any(x in t for x in PURDUE_CORE)

def passes_core_title(title: str) -> bool:
    """Stricter: require Purdue token in the TITLE."""
    return passes_core_filter(title or "")

def norm_date(e) -> str:
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
        return feedparser.parse(url)  # fallback

def yt_watch_link(entry) -> str:
    """Prefer yt_videoid when present; fall back to entry.link."""
    vid = None
    if isinstance(entry, dict):
        vid = entry.get("yt_videoid")
        if not vid:
            mg = entry.get("media_group") or {}
            if isinstance(mg, dict):
                vid = mg.get("yt_videoid")
    link = (getattr(entry, "link", "") or "").strip()
    return f"https://www.youtube.com/watch?v={vid}" if vid else link

def harvest_text_fields(e, source_name: str) -> str:
    """
    Build filter text:
      - Always title + summary/description (+ media_* + content if present)
      - Include RSS tags ONLY for YouTube sources (channel tags can carry 'Purdue').
        For Reddit/News feeds, tags often equal the search term and create noise.
    """
    parts = [
        getattr(e, "title", ""),
        getattr(e, "summary", "") or getattr(e, "description", "")
    ]
    if isinstance(e, dict):
        for key in ("media_description", "media_title"):
            v = e.get(key)
            if v: parts.append(v)
        content = e.get("content")
        if isinstance(content, list):
            for c in content:
                val = (c or {}).get("value")
                if val: parts.append(val)
        if "youtube" in source_name.lower():
            for tag in (e.get("tags") or []):
                term = tag.get("term") if isinstance(tag, dict) else getattr(tag, "term", "")
                if term: parts.append(term)
    return " ".join([clean_html(p) for p in parts if p])

def score_item(title: str, desc: str, source: str) -> int:
    t = (title or "").lower(); d = (desc or "").lower(); s = 0
    if "purdue" in t: s += 5
    s += sum(2 for k in PURDUE_CORE if k in t)
    s += sum(1 for k in PURDUE_CORE if k in d)
    if "purdue athletics" in source.lower(): s += 2
    if "youtube" in source.lower(): s += 1
    return s

def youtube_peek_has_purdue(link: str) -> bool:
    """Short, capped HTML peek to catch Purdue tokens on the watch page."""
    try:
        r = requests.get(link, headers={"User-Agent": UA}, timeout=YT_PEEK_TIMEOUT)
        if r.status_code != 200:
            return False
        html = r.text.lower()
        return any(tok in html for tok in PURDUE_CORE) and not any(x in html for x in EXC)
    except Exception:
        return False

def collect() -> List[Dict]:
    ranked: List[Tuple[Dict, int]] = []
    seen_link, seen_title = set(), set()

    for f in FEEDS_META:
        name, url = f["name"], f["url"]
        parsed = parse_feed(url)
        pulled = 0
        yt_peeks = 0
        lower_name = name.lower()

        for e in parsed.entries:
            title = (getattr(e, "title", "") or "").strip()
            if not title:
                continue

            link = (getattr(e, "link", "") or "").strip()
            if "youtube" in lower_name:
                link = yt_watch_link(e) or link
            if not link:
                continue

            desc = clean_html(getattr(e, "summary", "") or getattr(e, "description", ""))
            blob = harvest_text_fields(e, name)
            fulltext = f"{title} {blob}"

            # Default rule: must pass Purdue-specific filter (title/summary/content)
            passes = passes_core_filter(fulltext)

            # EXTRA strict for Reddit r/CollegeBasketball:
            # require Purdue mention in the TITLE specifically
            if "reddit – r/collegebasketball" in lower_name:
                passes = passes_core_title(title)

            # For YouTube: if not passing via RSS, try one short HTML peek
            if not passes and "youtube" in lower_name and yt_peeks < YT_PEEK_MAX_PER_FEED:
                yt_peeks += 1
                if youtube_peek_has_purdue(link):
                    passes = True

            if not passes:
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

        print(f"[collector] {name}: {pulled} items (YT peeks: {yt_peeks})")
        time.sleep(0.2)

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
    Path(OUT_FILE).write_text(json.dumps({"items": items}, indent=2), encoding="utf-8")
    print(f"[collector] Wrote {len(items)} items to {OUT_FILE}")

if __name__ == "__main__":
    main()
