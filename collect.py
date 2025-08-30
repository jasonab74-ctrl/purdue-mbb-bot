# collect.py — Purdue MBB collector (strict basketball focus)
from pathlib import Path
import time, json, re
from html import unescape
from typing import List, Dict, Tuple
import requests, feedparser
from feeds import FEEDS_META, KEYWORDS_EXCLUDE, KEYWORDS_INCLUDE

OUT_FILE = Path("items.json")
MAX_PER_FEED          = 60
TOTAL_MAX             = 500
TIMEOUT               = 15
UA                    = "Mozilla/5.0 (X11; Linux x86_64) PurdueMBBFeed/1.2 (+https://example.local)"
YT_PEEK_TIMEOUT       = 4
YT_PEEK_MAX_PER_FEED  = 6

INCLUDE = [s.lower() for s in KEYWORDS_INCLUDE]
EXCLUDE = [s.lower() for s in KEYWORDS_EXCLUDE]

def clean_html(s: str) -> str:
    return unescape(re.sub("<[^>]+>", " ", s or "").strip())

def parse_feed(url: str):
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT)
        r.raise_for_status()
        return feedparser.parse(r.content)
    except Exception:
        return feedparser.parse(url)

def norm_date(e) -> str:
    if getattr(e, "published_parsed", None):
        tm = e.published_parsed
        return f"{tm.tm_year:04d}-{tm.tm_mon:02d}-{tm.tm_mday:02d}"
    if getattr(e, "updated", None):
        return (e.updated or "").split("T")[0][:10]
    return ""

def fields_blob(e, source_name: str) -> str:
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

def title_passes(t: str) -> bool:
    tl = (t or "").lower()
    if any(x in tl for x in EXCLUDE): return False
    # Purist: demand Purdue + basketball signals in title
    require = ["purdue", "boilermaker", "boilerball"]
    hoops   = ["basketball", "mbb", "men's basketball", "matt painter"] + [
        "guard","forward","center","tipoff","assist","rebound","kenpom","net ranking"
    ]
    return any(r in tl for r in require) and (any(h in tl for h in hoops) or "purdue" in tl)

def blob_passes(b: str) -> bool:
    bl = (b or "").lower()
    if any(x in bl for x in EXCLUDE): return False
    inc_hits = sum(1 for k in INCLUDE if k in bl)
    return ("purdue" in bl or "boilermaker" in bl or "boilerball" in bl) and inc_hits >= 1

def youtube_watch_link(e) -> str:
    vid = None
    if isinstance(e, dict):
        vid = e.get("yt_videoid")
        if not vid:
            mg = e.get("media_group") or {}
            if isinstance(mg, dict):
                vid = mg.get("yt_videoid")
    link = (getattr(e, "link", "") or "").strip()
    return f"https://www.youtube.com/watch?v={vid}" if vid else link

def youtube_peek_psu(link: str) -> bool:
    try:
        r = requests.get(link, headers={"User-Agent": UA}, timeout=YT_PEEK_TIMEOUT)
        if r.status_code != 200: return False
        html = r.text.lower()
        return "purdue" in html or "boilermaker" in html or "boilerball" in html
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
                link = youtube_watch_link(e) or link
            if not link: continue

            desc = clean_html(getattr(e, "summary", "") or getattr(e, "description", ""))
            blob = fields_blob(e, name)
            full = f"{title} {blob}"

            # Reddit r/CollegeBasketball: require title to pass (less noise)
            passes = title_passes(title) if "reddit – r/collegebasketball" in lname else blob_passes(full)

            # YouTube: allow a few light peeks for Purdue mentions in HTML
            if not passes and "youtube" in lname and yt_peeks < YT_PEEK_MAX_PER_FEED:
                yt_peeks += 1
                if youtube_peek_psu(link):
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
            # Basic scoring: boost official + direct Purdue mentions
            score = 0
            tl = title.lower()
            if "purdue" in tl or "boilermaker" in tl or "boilerball" in tl: score += 5
            if "basketball" in tl or "mbb" in tl: score += 3
            if "purdue athletics" in name.lower() or "purduesports" in name.lower(): score += 2
            ranked.append((item, score))

            seen_link.add(link); seen_title.add(key_title)
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
