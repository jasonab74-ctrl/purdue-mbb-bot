"""
collect.py — fetch feeds and write normalized items.json (newest-first).

What this version adds:
- Keep strict football/WBB/other-sport excludes and Purdue-specific *includes*.
- YouTube: if RSS title/summary/tags don't show Purdue, do a tiny 4s HTML peek on
  the watch page (capped) to catch Purdue mentions that are only on the page.
- Ignore <category> tags for non-YouTube sources (Reddit/News) to avoid false positives.
"""

from pathlib import Path
import time, json, re
from html import unescape
from typing import List, Dict, Tuple
import requests, feedparser

from feeds import FEEDS_META, KEYWORDS_INCLUDE, KEYWORDS_EXCLUDE

OUT_FILE = Path("items.json")
MAX_PER_FEED = 60
TOTAL_MAX   = 500
TIMEOUT     = 15
UA          = "Mozilla/5.0 (X11; Linux x86_64) PurdueMBBBot/1.8 (+https://example.local)"

# --- Purdue-specific tokens we care about (must hit at least one) ---
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

# --- Limits for the YouTube HTML peek so we never block startup ---
YT_PEEK_TIMEOUT = 4          # seconds per video HTML fetch
YT_PEEK_MAX_PER_FEED = 8     # safety cap per run per YouTube channel

def _contains_any(text: str, tokens) -> bool:
    t = text.lower()
    return any(tok in t for tok in tokens)

def _passes_core_filter(text: str) -> bool:
    """Require a Purdue-specific token and no excluded tokens."""
    t = text.lower()
    if any(x in t for x in EXC):
        return False
    return any(x in t for x in PURDUE_CORE)

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
        return feedparser.parse(url)

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
            v = e.get(key);  parts.append(v or "")
        content = e.get("content")
        if isinstance(content, list):
            for c in content:
                parts.append((c or {}).get("value") or "")
        if "youtube" in source_name.lower():
            for tag in (e.get("tags") or []):
                term = tag.get("term") if isinstance(tag, dict) else getattr(tag, "term", "")
                parts.append(term or "")
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
    """Last-chance check: peek the YouTube HTML quickly for Purdue tokens."""
    try:
        r = requests.get(link, headers={"User-Agent": UA}, timeout=YT_PEEK_TIMEOUT)
        if r.status_code != 200:
            return False
        html = r.text.lower()
        # Cheap checks in title/meta/body
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

        for e in parsed.entries:
            title = (getattr(e, "title", "") or "").strip()
            if not title:
                continue

            link = (getattr(e, "link", "") or "").strip()
            if "youtube" in name.lower():
                link = yt_watch_link(e) or link
            if not link:
                continue

            desc = clean_html(getattr(e, "summary", "") or getattr(e, "description", ""))
            blob = harvest_text_fields(e, name)
            fulltext = f"{title} {blob}"

            passes = _passes_core_filter(fulltext)

            # If it's a YouTube item and we *didn't* pass via RSS fields,
            # try one capped HTML peek to catch Purdue mentions on the page.
            if not passes and "youtube" in name.lower() and yt_peeks < YT_PEEK_MAX_PER_FEED:
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
