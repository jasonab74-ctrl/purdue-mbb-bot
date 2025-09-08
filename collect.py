#!/usr/bin/env python3
# Hardened Purdue MBB collector — ensures items actually appear

import json, time, re, hashlib
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
from datetime import datetime, timezone
import feedparser
from feeds import FEEDS, STATIC_LINKS

MAX_ITEMS = 100

CURATED_SOURCES = [
    "PurdueSports.com","Journal & Courier","GoldandBlack.com","Hammer and Rails",
    "The Athletic","ESPN","Yahoo Sports","Sports Illustrated","CBS Sports","Big Ten Network"
]
ALLOWED_SOURCES = set(CURATED_SOURCES)

def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

def _host(u):
    try:
        n=urlparse(u).netloc.lower()
        for p in("www.","m.","amp."):
            if n.startswith(p): n=n[len(p):]
        return n
    except: return ""

def canonical(u):
    try:
        p=urlparse(u); q=parse_qs(p.query)
        keep={"id","story","v","p"}
        q={k:v for k,v in q.items() if k in keep}
        p=p._replace(query=urlencode(q,doseq=True),fragment="",netloc=_host(u))
        return urlunparse(p)
    except: return u

def hid(s): return hashlib.sha1(s.encode("utf-8")).hexdigest()[:16]

ALIASES = {
    "purduesports.com":"PurdueSports.com",
    "jconline.com":"Journal & Courier",
    "goldandblack.com":"GoldandBlack.com",
    "on3.com":"GoldandBlack.com",
    "hammerandrails.com":"Hammer and Rails",
    "theathletic.com":"The Athletic",
    "espn.com":"ESPN",
    "sports.yahoo.com":"Yahoo Sports",
    "si.com":"Sports Illustrated",
    "cbssports.com":"CBS Sports",
    "btn.com":"Big Ten Network",
    "btn.plus":"Big Ten Network",
}

# Looser KEEP to ensure items show; still drop non-MBB
KEEP = [
    r"\bPurdue\b", r"\bBoilermakers?\b",
    r"\bmen'?s?\s*basketball\b", r"\bMBB\b",
    r"\bMatt Painter\b", r"\bBraden Smith\b", r"\bFletcher Loyer\b",
    r"\bTrey Kaufman-?Renn\b", r"\bMyles Colvin\b", r"\bZach Edey\b"
]
DROP = [
    r"\bfootball\b", r"\bvolleyball\b", r"\bbaseball\b", r"\bsoftball\b",
    r"\bwrestling\b", r"\btrack\b", r"\bsoccer\b", r"\bhockey\b",
    r"\bwomen'?s\b", r"\bWBB\b", r"\bWNBA\b", r"\bWNIT\b",
    r"\bNotre Dame\b", r"\bIndiana\b", r"\bIU\b", r"\bButler\b",
]

def text_ok(title, summary):
    t=f"{title} {summary}"
    if not any(re.search(p,t,re.I) for p in KEEP): return False
    if any(re.search(p,t,re.I) for p in DROP): return False
    return True

def parse_time(e):
    for k in("published_parsed","updated_parsed"):
        if e.get(k):
            try: return time.strftime("%Y-%m-%dT%H:%M:%S%z", e[k])
            except: pass
    return now_iso()

def label_for(link, fallback):
    return ALIASES.get(_host(link), fallback.strip() or "Unknown")

def fetch_all():
    items, seen = [], set()
    for f in FEEDS:
        fname=f["name"].strip(); furl=f["url"].strip()
        try:
            parsed=feedparser.parse(furl)
        except: 
            continue
        for e in parsed.entries[:150]:
            link = canonical((e.get("link") or e.get("id") or "").strip())
            if not link: continue
            key=hid(link)
            if key in seen: continue

            src = label_for(link, fname)
            if src not in ALLOWED_SOURCES: 
                continue

            title=(e.get("title") or "").strip()
            summary=(e.get("summary") or e.get("description") or "").strip()
            # Permit broader during preseason/quiet periods: keep Purdue mentions even if "men's" not present
            if not text_ok(title, summary): 
                continue

            items.append({
                "id": key,
                "title": title or "(untitled)",
                "link": link,
                "source": src,
                "feed": fname,
                "published": parse_time(e),
                "summary": summary
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
    with open("items.json","w",encoding="utf-8") as f:
        json.dump(payload,f,ensure_ascii=False,indent=2)

if __name__ == "__main__":
    write_items(fetch_all())
