#!/usr/bin/env python3
import json, time, re, os
from datetime import datetime, timezone
import feedparser

from feeds import FEEDS, STATIC_LINKS, CURATED_SOURCES, TRUSTED_DOMAINS

# ---------- helpers ----------
NOW = datetime.now(timezone.utc)

def iso_now():
    return NOW.isoformat()

def to_iso(dt_struct):
    try:
        return datetime.fromtimestamp(time.mktime(dt_struct), tz=timezone.utc).isoformat()
    except Exception:
        return iso_now()

def clean_text(s):
    return (s or "").replace("\u200b", "").strip()

def domain_of(href):
    try:
        return re.sub(r"^https?://(www\.)?", "", href).split("/")[0].lower()
    except Exception:
        return ""

# ---------- Purdue MBB filter ----------
NEGATIVE = re.compile(
    r"\b(football|nfl|volleyball|softball|baseball|women'?s|wbb|soccer|hockey)\b",
    re.I,
)
MBB_POSITIVE = re.compile(
    r"\b(basketball|mbb|men'?s\s+basketball|boilermakers)\b",
    re.I,
)
PURDUE = re.compile(r"\bpurdue\b", re.I)

def is_trusted(href):
    d = domain_of(href)
    return any(d.endswith(t) for t in TRUSTED_DOMAINS)

def allow_item(title, summary, href):
    """Strict Purdue MBB allow-list with sport excludes."""
    text = f"{title} {summary}"
    if NEGATIVE.search(text):
        return False
    if not PURDUE.search(text):
        # If the domain is trusted, allow even without explicit 'Purdue' (some headlines omit)
        if not is_trusted(href):
            return False
    # Must look like men's basketball
    if not MBB_POSITIVE.search(text):
        # For trusted domains, be lenient if it’s clearly a team page/recap path
        if not is_trusted(href):
            return False
    return True

# ---------- fetch ----------
def fetch_feed(url, limit=60):
    d = feedparser.parse(url)
    items = []
    for e in d.entries[:limit]:
        title = clean_text(getattr(e, "title", ""))
        link = getattr(e, "link", "")
        summary = clean_text(getattr(e, "summary", "") or getattr(e, "description", ""))
        src = clean_text(getattr(e, "source", {}).get("title", "") if hasattr(e, "source") else "")
        if not src:
            src = clean_text(getattr(d.feed, "title", "")) or domain_of(link)

        if not link or not title:
            continue
        if not allow_item(title, summary, link):
            continue

        published = None
        if hasattr(e, "published_parsed") and e.published_parsed:
            published = to_iso(e.published_parsed)
        elif hasattr(e, "updated_parsed") and e.updated_parsed:
            published = to_iso(e.updated_parsed)
        else:
            published = iso_now()

        items.append({
            "title": title,
            "link": link,
            "summary": summary,
            "source": src,
            "published": published,
        })
    return items

def dedupe(items):
    seen = set()
    out = []
    for it in items:
        k = (it["title"].lower(), it["link"])
        if k in seen:
            continue
        seen.add(k)
        out.append(it)
    return out

def sort_items(items):
    def key(it):
        return it.get("published", "")
    return sorted(items, key=key, reverse=True)

# ---------- main ----------
def main():
    all_items = []
    for url in FEEDS:
        try:
            all_items.extend(fetch_feed(url))
        except Exception:
            continue

    all_items = dedupe(all_items)
    all_items = sort_items(all_items)[:120]

    # Harden the dropdown by ALWAYS shipping curated sources,
    # even if a given run produced zero stories from one of them.
    data = {
        "updated": iso_now(),
        "sources": CURATED_SOURCES,
        "links": STATIC_LINKS,
        "items": all_items,
    }
    with open("items.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Wrote items.json with {len(all_items)} items at {data['updated']}")

if __name__ == "__main__":
    main()
