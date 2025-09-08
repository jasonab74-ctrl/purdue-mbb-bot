#!/usr/bin/env python3
# Purdue Men's Basketball — hardened collector
# - Curated 10-source dropdown (strings only) for stability
# - Strict MBB filters (drops football, WBB, other sports, other schools)
# - Always writes 'updated', 'links', and 'sources' so UI never rolls back
# - Canonical links + de-dupe
# - No secrets required

import json, time, re, hashlib
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
from datetime import datetime, timezone
import feedparser
from feeds import FEEDS, STATIC_LINKS

MAX_ITEMS = 80

CURATED_SOURCES = [
    "PurdueSports.com",
    "Journal & Courier",
    "GoldandBlack.com",
    "Hammer and Rails",
    "The Athletic",
    "ESPN",
    "Yahoo Sports",
    "Sports Illustrated",
    "CBS Sports",
    "Big Ten Network",
]
ALLOWED_SOURCES = set(CURATED_SOURCES)

def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

def _host(u: str) -> str:
    try:
        n = urlparse(u).netloc.lower()
        for p in ("www.","m.","amp."): 
            if n.startswith(p): n = n[len(p):]
        return n
    except Exception:
        return ""

def canonical(u: str) -> str:
    try:
        p = urlparse(u)
        keep = {"id","story","v","p"}
        q = parse_qs(p.query)
        q = {k:v for k,v in q.items() if k in keep}
        p = p._replace(query=urlencode(q, doseq=True), fragment="", netloc=_host(u))
        return urlunparse(p)
    except Exception:
        return u

def hid(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:16]

ALIASES = {
    "purduesports.com":     "PurdueSports.com",
    "jconline.com":         "Journal & Courier",
    "on3.com":              "GoldandBlack.com",
    "goldandblack.com":     "GoldandBlack.com",
    "hammerandrails.com":   "Hammer and Rails",
    "theathletic.com":      "The Athletic",
    "espn.com":             "ESPN",
    "sports.yahoo.com":     "Yahoo Sports",
    "si.com":               "Sports Illustrated",
    "cbssports.com":        "CBS Sports",
    "btn.com":              "Big Ten Network",
    "btn.plus":             "Big Ten Network",
}

KEEP = [
    r"\bPurdue\b", r"\bBoilermakers?\b",
    r"\bmen'?s?\s*basketball\b", r"\bMBB\b",
    r"\bMatt Painter\b", r"\bBraden Smith\b", r"\bFletcher Loyer\b", r"\bMyles Colvin\b",
    r"\bTrey Kaufman-?Renn\b", r"\bMason Gillis\b"
]
DROP = [
    r"\bfootball\b", r"\bvolleyball\b", r"\bbaseball\b", r"\bsoftball\b", r"\bwrestling\b",
    r"\btrack\b", r"\bsoccer\b", r"\bhockey\b",
    r"\bwomen'?s\b", r"\bWBB\b", r"\bWNIT\b", r"\bWNBA\b",
    r"\bNotre Dame\b", r"\bIndiana\b", r"\bIU\b", r"\bButler\b",
]

def text_ok(title: str, summary: str) -> bool:
    t = f"{title} {summary}"
    if not any(re.search(p, t, re.I) for p in KEEP): return False
    if any(re.search(p, t, re.I) for p in DROP): return False
    return True

def parse_time(entry):
    for key in ("published_parsed","updated_parsed"):
        if entry.get(key):
            try:
                return time.strftime("%Y-%m-%dT%H:%M:%S%z", entry[key])
            except Exception:
                pass
    return now_iso()

def label_for(link: str, fallback: str) -> str:
    return ALIASES.get(_host(link), fallback.strip() or "Unknown")

def fetch_all():
    items, seen = [], set()
    for f in FEEDS:
        fname, furl = f["name"].strip(), f["url"].strip()
        try:
            parsed = feedparser.parse(furl)
        except Exception:
            continue
        for e in parsed.entries[:150]:
            link = canonical((e.get("link") or e.get("id") or "").strip())
            if not link: continue
            key = hid(link)
            if key in seen: continue

            src = label_for(link, fname)
            if src not in ALLOWED_SOURCES:  # keep dropdown tight and predictable
                continue

            title = (e.get("title") or "").strip()
            summary = (e.get("summary") or e.get("description") or "").strip()
            if not text_ok(title, summary): continue

            items.append({
                "id": key,
                "title": title or "(untitled)",
                "link": link,
                "source": src,
                "feed": fname,
                "published": parse_time(e),
                "summary": summary,
            })
            seen.add(key)

    items.sort(key=lambda x: x["published"], reverse=True)
    return items[:MAX_ITEMS]

def write_items(items):
    payload = {
        "updated": now_iso(),
        "items": items,
        "links": STATIC_LINKS,
        "sources": list(CURATED_SOURCES)
    }
    with open("items.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

def main():
    write_items(fetch_all())

if __name__ == "__main__":
    main()
