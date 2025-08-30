# collect.py — Purdue Men’s Basketball collector (strict)

from pathlib import Path
import time, json, re
from html import unescape
from typing import List, Dict, Tuple
import requests, feedparser
from feeds import FEEDS_META, KEYWORDS_EXCLUDE

OUT_FILE = Path("items.json")
MAX_PER_FEED          = 60
TOTAL_MAX             = 500
TIMEOUT               = 15
UA                    = "Mozilla/5.0 (X11; Linux x86_64) PurdueMBBFeed/1.1 (+https://example.local)"
YT_PEEK_TIMEOUT       = 4
YT_PEEK_MAX_PER_FEED  = 6

# Purdue basketball language (positive signals)
PURDUE_CORE = [
    "purdue","boilermakers","boilers","mackey","painter","big ten","march madness","ncaa tournament",
    "basketball","mbb","men’s basketball","men's basketball",
    # roster names (2025–26)
    "c.j. cox","antione west jr.","fletcher loyer","braden smith","aaron fine","jack lusk",
    "jack benter","omer mayer","gicarri harris","jace rayl","trey kaufman-renn","liam murphy",
    "sam king","raleigh burgess","daniel jacobsen","oscar cluff",
]
PURDUE_CORE = [t.lower() for t in PURDUE_CORE]

EXC = [k.lower() for k in KEYWORDS_EXCLUDE] + [
    # ban non-basketball sports explicitly
    "football","wbb","women","volleyball","wrestling","baseball","softball",
    "soccer","hockey","golf","track","cross country","tennis","swimming","lacrosse",
    # betting spam
    "odds","parlay","props","fanduel","draftkings","promo code",
]

def _contains_any(text: str, tokens) -> bool:
    t = text.lower()
    return any(tok in t for tok in tokens)

def passes_core_blob(text: str) -> bool:
    t = text.lower()
    if any(x in t for x in EXC):    # hard negatives
        return False
    return ("purdue" in t or "boilermakers" in t or "mackey" in t) and (
        "basketball" in t or "mbb" in t or any(k in t for k in PURDUE_CORE)
    )

def passes_core_title(title: str) -> bool:
    t = (title or "").lower()
    if any(x in t for x in EXC): return False
    return ("purdue" in t or "boilermakers" in t) and (
        "basketball" in t or "mbb" in t or any(k in t for k in PURDUE_CORE)
    )

def norm_date(e) -> str:
    if getattr(e, "published_parsed", None):
        tm = e.published_parsed
        return f"{tm.tm_year:04d}-{tm.tm_mon:02d}-{tm.tm_mday:02d}"
    if getattr(e, "updated", None):
        return (e.updated or "").split("T")[0][:10]
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
    if "purdue" in t or "boilermakers" in t: s += 5
    if "basketball" in t or "mbb" in t: s += 3
    s += sum(2 for k in PURDUE_CORE if k in t)
    s += sum(1 for k in PURDUE_CORE if k in d)
    if "purdue" in source.lower(): s += 2
    if "reddit" in source.lower(): s -= 1
    return s

def youtube_peek_has_purdue(link: str) -> bool:
    try:
        r = requests.get(link, headers={"User-Agent": UA}, timeout=YT_PEEK_TIMEOUT)
        if r.status_code != 200: return False
        html = r.text.lower()
        return passes_core_blob(html)
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
        lname = name.lower()

        for e in parsed.entries:
            title = (getattr(e, "title", "") or "").strip()
            if not title: continue

            link = (getattr(e, "link", "") or "").strip()
            if "youtube" in lname:
                link = yt_watch_link(e) or link
            if not link: continue

            desc = clean_html(getattr(e, "summary", "") or getattr(e, "description", ""))
            blob = harvest_text_fields(e, name)
            fulltext = f"{title} {blob}"

            passes = passes_core_blob(fulltext)
            if "reddit – r/cbb" in lname:
                passes = passes_core_title(title)

            if not passes and "youtube" in lname and yt_peeks < YT_PEEK_MAX_PER_FEED:
                yt_peeks += 1
                if youtube_peek_has_purdue(link):
                    passes = True

            if not passes: continue

            key_title = re.sub(r"\s+", " ", title.lower())
            if link in seen_link or key_title in seen_title: continue

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
            if pulled >= MAX_PER_FEED: break

        print(f"[collector] {name}: {pulled} items (YT peeks: {yt_peeks})")
        time.sleep(0.2)

    def date_key(it: Dict) -> str:
        return it.get("date") or "0000-00-00"
    ranked.sort(key=lambda p: (date_key(p[0]), p[1]), reverse=True)
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
