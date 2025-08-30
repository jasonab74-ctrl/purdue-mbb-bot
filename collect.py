# collect.py — fetch, filter, dedupe, and write items.json (basketball-only tuning)
import json, os, re, time, hashlib, html, datetime, urllib.parse
from typing import List, Dict, Any
import feedparser
import requests

# Import feed config
from feeds import FEEDS, KEYWORDS_INCLUDE, KEYWORDS_EXCLUDE, MAX_ITEMS_PER_FEED, SOURCE_ALIASES, FEED_TITLE_REQUIRE

OUT_PATH = os.environ.get("ITEMS_PATH", "items.json")
FRESH_DAYS = int(os.environ.get("FRESH_DAYS", "365"))  # keep a season’s worth by default
NOW = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)

USER_AGENT = "PurdueMBB/1.0 (+https://railway.app)"
TIMEOUT = 15

# -------- helpers --------
def norm_text(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(s or "")).strip()

def to_utc(dt_struct) -> datetime.datetime:
    """Convert feedparser date to aware UTC datetime."""
    try:
        if not dt_struct: 
            return None
        ts = time.mktime(dt_struct)
        return datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)
    except Exception:
        return None

def parse_date(entry: dict) -> datetime.datetime:
    for k in ("published_parsed","updated_parsed","created_parsed"):
        if k in entry and entry[k]:
            dt = to_utc(entry[k])
            if dt: return dt
    return None

def age_ok(dt: datetime.datetime) -> bool:
    if not dt: 
        return True  # some feeds omit dates; allow but will sort late
    return (NOW - dt) <= datetime.timedelta(days=FRESH_DAYS)

def sha(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()

def alias_source(name: str) -> str:
    return SOURCE_ALIASES.get(name, name)

# -------- filtering --------
INC = [t.lower() for t in KEYWORDS_INCLUDE]
EXC = [t.lower() for t in KEYWORDS_EXCLUDE]

PLAYER_OR_TERMS = [
    "purdue","boiler","boilers","boilermaker","boilermakers","painter",
    # player last names likely to appear by themselves
    "edey","smith","loyer","kaufman","kaufman-renn","gillis","furst",
    "colvin","heide","berg","benter","jacobsen","mayer","cook",
]

def has_any(hay: str, needles: List[str]) -> bool:
    h = hay.lower()
    return any(n in h for n in needles)

def feed_requires(feed_name: str, title: str) -> bool:
    for key, req_list in FEED_TITLE_REQUIRE.items():
        if key.lower() in feed_name.lower():
            return has_any(title, [r.lower() for r in req_list])
    return True

def looks_like_basketball(title: str, summary: str, link: str) -> bool:
    text = f"{title} {summary} {link}".lower()
    if has_any(text, EXC):
        return False
    # Require either explicit basketball terms OR Purdue+player name context
    if has_any(text, INC):
        return True
    # r/CollegeBasketball etc needs Purdue mention
    if ("reddit.com" in link.lower()) and not has_any(text, ["purdue","boiler","boilermaker","boilermakers"]):
        return False
    # be permissive if Purdue is present and a likely player/coach is mentioned
    if "purdue" in text and has_any(text, PLAYER_OR_TERMS):
        return True
    return False

def item_from_entry(feed_name: str, entry: dict) -> Dict[str, Any]:
    title = norm_text(entry.get("title", ""))
    link  = entry.get("link") or entry.get("id") or ""
    if not link:
        return None
    if not feed_requires(feed_name, title):
        return None

    summary = norm_text(entry.get("summary", ""))
    if not looks_like_basketball(title, summary, link):
        return None

    dt = parse_date(entry)
    if not age_ok(dt):
        return None

    date_iso = dt.isoformat() if dt else None
    source = alias_source(feed_name)
    uid = sha(f"{title}|{link}")

    # badge text = source
    badge = source

    return {
        "id": uid,
        "title": title,
        "link": link,
        "date": date_iso,
        "source": source,
        "badge": badge,
        "snippet": summary[:400],
    }

# -------- fetchers --------
def fetch_rss(url: str) -> feedparser.FeedParserDict:
    return feedparser.parse(url, request_headers={"User-Agent": USER_AGENT})

def fetch_all() -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for feed in FEEDS:
        name, url = feed["name"], feed["url"]
        try:
            parsed = fetch_rss(url)
            # Soft skip on HTTP failures but continue overall
            entries = parsed.entries or []
            count = 0
            for e in entries:
                it = item_from_entry(name, e)
                if it:
                    items.append(it)
                    count += 1
                    if count >= MAX_ITEMS_PER_FEED:
                        break
        except Exception:
            # Never crash collection on one bad feed
            continue
    return items

# -------- write out --------
def dedupe_sort(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for it in items:
        key = it["id"]
        if key in seen:
            continue
        seen.add(key)
        out.append(it)

    # sort newest first; undated sinks
    def keyfn(x):
        return x["date"] or "1900-01-01T00:00:00+00:00"
    out.sort(key=keyfn, reverse=True)
    return out

def main():
    items = fetch_all()
    items = dedupe_sort(items)
    data = {
        "generated_at": NOW.isoformat(),
        "items_count": len(items),
        "items": items,
    }
    tmp = OUT_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, OUT_PATH)
    print(json.dumps({
        "ok": True,
        "final_count": len(items),
        "ts": NOW.isoformat(),
    }))

if __name__ == "__main__":
    main()
