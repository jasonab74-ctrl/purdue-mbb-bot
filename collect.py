"""
collect.py — fetches articles from FEEDS and writes normalized items.json.

- Uses KEYWORDS_INCLUDE / KEYWORDS_EXCLUDE from feeds.py to keep the feed relevant.
- Deduplicates by link and title.
- Keeps a balanced number from each feed.
- Safe on errors (continues when a feed fails).
"""

from pathlib import Path
import time, json, re
import feedparser
from urllib.parse import urlparse

from feeds import FEEDS_META, KEYWORDS_INCLUDE, KEYWORDS_EXCLUDE

OUT_FILE = Path("items.json")
MAX_PER_FEED = 15
TOTAL_MAX = 200

INC = [k.lower() for k in KEYWORDS_INCLUDE]
EXC = [k.lower() for k in KEYWORDS_EXCLUDE]

def text_ok(txt: str) -> bool:
    t = (txt or "").lower()
    if EXC and any(x in t for x in EXC):
        return False
    # if includes present, at least one must match
    return (not INC) or any(x in t for x in INC)

def norm_date(e) -> str:
    if getattr(e, "published_parsed", None):
        tm = e.published_parsed
        return f"{tm.tm_year:04d}-{tm.tm_mon:02d}-{tm.tm_mday:02d}"
    if getattr(e, "updated", None):
        return e.updated.split("T")[0][:10]
    return ""

def domain(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return ""

def collect():
    items = []
    seen_links, seen_titles = set(), set()

    for f in FEEDS_META:
        name, url = f["name"], f["url"]
        try:
            parsed = feedparser.parse(url)
            count = 0
            for e in parsed.entries:
                title = getattr(e, "title", "") or ""
                link = getattr(e, "link", "") or ""
                desc = getattr(e, "summary", "") or getattr(e, "description", "")
                blob = f"{title} {desc}"

                if not link or not title:
                    continue
                if not text_ok(blob):
                    continue

                key_title = re.sub(r"\s+", " ", title.strip().lower())
                if link in seen_links or key_title in seen_titles:
                    continue

                items.append({
                    "title": title.strip(),
                    "link": link.strip(),
                    "source": name,
                    "date": norm_date(e),
                    "description": re.sub("<[^>]+>", "", desc).strip()[:280]
                })
                seen_links.add(link)
                seen_titles.add(key_title)
                count += 1
                if count >= MAX_PER_FEED:
                    break
            time.sleep(0.2)  # be polite
        except Exception:
            # keep going on individual feed failure
            continue

    # sort newest first (undated at bottom)
    items.sort(key=lambda it: it.get("date") or "0000-00-00", reverse=True)
    items = items[:TOTAL_MAX]

    payload = {"items": items}
    OUT_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {len(items)} items to {OUT_FILE}")

if __name__ == "__main__":
    collect()
