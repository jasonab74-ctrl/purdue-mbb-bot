#!/usr/bin/env python3
# Purdue Boilermakers MBB — collector (HARDENED: curated sources + guaranteed links/dates)

import json, time, re, hashlib
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
from datetime import datetime, timezone
import feedparser
from feeds import FEEDS, STATIC_LINKS

MAX_ITEMS = 60

# ---- Curated dropdown (8–10 reliable sources) ----
CURATED_SOURCES = [
    "Hammer and Rails",
    "ESPN",
    "Yahoo Sports",
    "Sports Illustrated",
    "IndyStar",
    "Journal & Courier",
    "Purdue Exponent",
    "AP News",
    "SB Nation",
    "The Athletic",
]

ALLOWED_SOURCES = set(CURATED_SOURCES)

# --------------- utils ----------------

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
    # locals / team
    "hammerandrails.com": "Hammer and Rails",
    "indystar.com":       "IndyStar",
    "jconline.com":       "Journal & Courier",
    "purdueexponent.org": "Purdue Exponent",
    # nationals (mapped so dropdown stays clean)
    "espn.com":           "ESPN",
    "sports.yahoo.com":   "Yahoo Sports",
    "si.com":             "Sports Illustrated",
    "apnews.com":         "AP News",
    "sbnation.com":       "SB Nation",
    "theathletic.com":    "The Athletic",
    # Google News articles will be normalized by target hostname,
    # so no separate alias is needed here.
}

# require Purdue + hoops; exclude non-MBB sports
KEEP = [r"\bPurdue\b", r"\bBoilermakers?\b", r"\bBoilers?\b", r"\bbasketball\b"]
DROP = [r"\bfootball\b", r"\bvolleyball\b", r"\bbaseball\b", r"\bwomen'?s\b", r"\bwbb\b"]

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
    return now_iso()  # fallback → dates always render

def source_label(link: str, feed_name: str) -> str:
    # Prefer normalized domain label; otherwise use feed name
    return ALIASES.get(_host(link), feed_name.strip())

# --------------- pipeline ----------------

def fetch_all():
    items, seen = [], set()
    for f in FEEDS:
        fname, furl = f["name"].strip(), f["url"].strip()
        try:
            parsed = feedparser.parse(furl)
        except Exception:
            continue
        for e in parsed.entries[:120]:
            link = canonical((e.get("link") or e.get("id") or "").strip())
            if not link: continue
            key = hid(link)
            if key in seen: continue

            src = source_label(link, fname)
            if src not in ALLOWED_SOURCES:
                continue  # dropdown remains curated/clean

            title = (e.get("title") or "").strip()
            summary = (e.get("summary") or e.get("description") or "").strip()
            if not text_ok(title, summary): continue

            items.append({
                "id": key,
                "title": title or "(untitled)",
                "link": link,
                "source": src,
                "feed": fname,
                "published": parse_time(e),   # always present (ISO)
                "summary": summary,
            })
            seen.add(key)

    items.sort(key=lambda x: x["published"], reverse=True)
    return items[:MAX_ITEMS]

def write_items(items):
    payload = {
        "updated": now_iso(),
        "items": items,
        "links": STATIC_LINKS,       # buttons always present
        "sources": CURATED_SOURCES,  # dropdown never disappears
    }
    with open("items.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

def main():
    write_items(fetch_all())

if __name__ == "__main__":
    main()
