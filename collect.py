import time
from datetime import datetime, timedelta, timezone
import re
import requests
import feedparser

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) PurdueMBBBot/1.0 (+render)"
HTTP_TIMEOUT = 6  # seconds
CACHE_TTL = 15 * 60  # 15 minutes

SOURCES = [
# --- Additional Purdue-related YouTube RSS feeds (purely additive) ---
YOUTUBE_FEEDS = [
    "https://www.youtube.com/feeds/videos.xml?channel_id=UCKyz9ZrU_nqFauFWYhdPNIQ",  # Purdue Athletics (official)
    "https://www.youtube.com/feeds/videos.xml?channel_id=UC9by2xjmM_ldmvIwYrARCDg",  # Field of 68
    "https://www.youtube.com/feeds/videos.xml?channel_id=UCaqPH-Ckzu_pSoO3AKcatNw",  # Sleepers Media
]

# If you already have SOURCES defined elsewhere, this will extend it.
try:
    SOURCES += YOUTUBE_FEEDS
except NameError:
    SOURCES = list(YOUTUBE_FEEDS)
    ("Hammer & Rails", "https://www.hammerandrails.com/rss/index.xml"),
    ("Journal & Courier Purdue", "https://rss.app/feeds/2iN67Qv7t9C1p7dS.xml"),
    ("Sports Illustrated (Purdue)", "https://www.si.com/college/purdue/.rss"),
    ("Purdue Exponent", "https://www.purdueexponent.org/search/?f=atom&c=news%2Csports&t=article"),
    ("GoldandBlack", "https://www.on3.com/feeds/goldandblack/purdue/"),
    # Reddit: rate-limited sometimes; handle gracefully
    ("Reddit r/Boilermakers", "https://www.reddit.com/r/Boilermakers/search.rss?q=Purdue%20men%27s%20basketball&restrict_sr=on&sort=new&t=month"),
]

# in-memory cache
_CACHE = {"data": None, "ts": 0, "debug": None}

# ----------------- Helpers -----------------

def _now_iso():
    return datetime.now(timezone.utc).isoformat()

def _epoch():
    return int(time.time())

def _http_get(url):
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=HTTP_TIMEOUT)
        # reddit often 429s—treat as empty
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"[rss-skip] {url} -> {e}")
        return None

# Purdue MBB relevance filter (strict but pragmatic)
MBB_POS = re.compile(
    r"\b(Men'?s?\s+Basketball|MBB|boilermakers basketball|Mackey|Matt Painter|Braden Smith|Fletcher Loyer|Zach Edey|Purdue hoops)\b",
    re.IGNORECASE,
)
NON_MBB_NEG = re.compile(
    r"\b(football|soccer|volleyball|baseball|softball|track|swim|wrestling|rowing|golf|women'?s|wbb|hockey)\b",
    re.IGNORECASE,
)

def is_mbb_relevant(title, summary, source):
    text = f"{title or ''} {summary or ''}"
    if NON_MBB_NEG.search(text):
        return False
    # Require explicit basketball signal or known coach/venue
    return bool(MBB_POS.search(text))

def _norm_time(dt_struct):
    # feedparser returns time.struct_time or None
    try:
        dt = datetime(*dt_struct[:6], tzinfo=timezone.utc)
        return dt.isoformat(), int(dt.timestamp())
    except Exception:
        iso = _now_iso()
        return iso, _epoch()

def parse_rss(name, url, kept_counter):
    html = _http_get(url)
    if not html:
        return [], 0
    d = feedparser.parse(html)
    items = []
    fetched = 0
    for e in d.entries:
        fetched += 1
        title = getattr(e, "title", "")
        link = getattr(e, "link", "")
        summary = getattr(e, "summary", "")
        published_struct = getattr(e, "published_parsed", None) or getattr(e, "updated_parsed", None)
        published_iso, ts = _norm_time(published_struct) if published_struct else (_now_iso(), _epoch())

        if is_mbb_relevant(title, summary, name):
            items.append({
                "title": title,
                "link": link,
                "summary": summary,
                "source": name,
                "published": published_iso,
                "ts": ts,
            })
            kept_counter[0] += 1
    return items, fetched

# ----------------- Public API -----------------

def collect_all(force=False, include_raw=False):
    global _CACHE
    if not force and _CACHE["data"] and (_epoch() - _CACHE["ts"] < CACHE_TTL):
        return _CACHE["data"]

    all_items = []
    src_stats = []
    for (name, url) in SOURCES:
        kept = [0]
        items, fetched = parse_rss(name, url, kept)
        all_items.extend(items)
        src_stats.append({"name": name, "url": url, "fetched": fetched, "kept": kept[0]})

    # sort newest first & dedupe by link
    seen = set()
    all_items.sort(key=lambda x: x["ts"], reverse=True)
    deduped = []
    for it in all_items:
        if it["link"] in seen:
            continue
        seen.add(it["link"])
        deduped.append(it)

    data = {
        "count": len(deduped),
        "items": deduped,
        "sources": src_stats,
        "updated": _now_iso(),     # ISO for the UI
        "updated_ts": _epoch(),    # int if you want it
    }

    _CACHE = {"data": data, "ts": _epoch(), "debug": {"sources": src_stats, "updated": data["updated_ts"]}}
    return data

def get_cached_or_collect(include_raw=False):
    return collect_all(force=False, include_raw=include_raw)

def collect_debug():
    # always run a light collect to refresh stats, but don’t block too long on free tier
    data = collect_all(force=False)
    # Return a concise debug payload
    return {
        "count": data["count"],
        "items": [],  # keep small
        "sources": data["sources"],
        "updated": data["updated_ts"],
    }
