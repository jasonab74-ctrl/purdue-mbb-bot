# collect.py
# -------------------------------------------------------------------
# Fetches sources from feeds.py, filters to *Purdue Men's Basketball*,
# dedupes, sorts newest-first, and writes /app/items.json
#
# Endpoints (wired in server.py):
#   GET /collect-now          -> runs this once (honors lock)
#   GET /collect-now?force=1  -> bypass lock
#
# Env:
#   FRESH_DAYS=120   (how far back to look)
#   MAX_ITEMS=250    (cap items.json length)
#   DEBUG=1          (include debug payload)
# -------------------------------------------------------------------

import os, re, time, json, hashlib, html, urllib.parse as ul
from datetime import datetime, timedelta, timezone
import requests
import feedparser

from feeds import (
    TEAM_NAME,
    DAYS_BACK_DEFAULT,
    MAX_ITEMS_DEFAULT,
    NEWS_QUERIES,
    YOUTUBE_SOURCES,
    REDDIT_SOURCES,
    PURDUE_HEAVY_DOMAINS,
)

APP_DIR      = os.environ.get("APP_DIR", "/app")
ITEMS_PATH   = os.path.join(APP_DIR, "items.json")
LOCK_PATH    = os.path.join(APP_DIR, ".collect.lock")
USER_AGENT   = "PurdueMBB/1.0 (+https://railway.app)"

FRESH_DAYS   = int(os.environ.get("FRESH_DAYS", DAYS_BACK_DEFAULT))
MAX_ITEMS    = int(os.environ.get("MAX_ITEMS", MAX_ITEMS_DEFAULT))
DEBUG        = bool(int(os.environ.get("DEBUG", "0")))

HTTP_TIMEOUT = 15

# ------------------------ keyword filters ---------------------------

INCLUDE_TERMS = {
    # team/program
    "purdue", "boiler", "boilermaker", "boilermakers",
    "mackey arena", "mackey",
    "purdue basketball", "men's basketball", "mbb", "ncaa tournament",

    # coach
    "matt painter",

    # prominent/current players (extend freely)
    "braden smith", "fletcher loyer", "trey kaufman-renn", "trey kaufman",
    "mason gillis", "caleb furst", "myles colvin", "camden heide",
    "will berg", "jack benter", "daniel jacobsen", "levi cook",
    "omer mayer",  # add new names as needed
}

# hard excludes (any one kills the item)
EXCLUDE_TERMS = {
    # other sports
    "football", "quarterback", "qb", "touchdown", "wide receiver", "ryan walters",
    "volleyball", "soccer", "baseball", "softball", "wrestling",
    "swimming", "golf", "tennis", "track", "cross country",
    # rivals bait
    "indiana football", "big ten media days (football)",

    # misfires from general feeds
    "discord", "ticket info only", "parking change debate", "robot dog",
}

def norm_text(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(s or "")).strip().lower()

def domain_of(url: str) -> str:
    try:
        return ul.urlparse(url).netloc.lower().replace("www.", "")
    except Exception:
        return ""

def passes_filters(title, summary, link, source_domain, force_light=False):
    """Return True if this item looks like Purdue MBB."""
    t = " ".join([title or "", summary or "", link or ""])
    nt = norm_text(t)

    # global hard excludes
    for bad in EXCLUDE_TERMS:
        if bad in nt:
            return False

    # Purdue-heavy domains get a lighter include test (still MBB-ish words)
    light = force_light or (source_domain in PURDUE_HEAVY_DOMAINS)

    if light:
        # Require at least one basketball-ish token with Purdue context
        if ("basketball" in nt or "men's basketball" in nt or "mbb" in nt or "matt painter" in nt):
            if ("purdue" in nt or "boiler" in nt or "boilermaker" in nt):
                return True
        return False

    # For general sources, require at least one include term
    if any(term in nt for term in INCLUDE_TERMS):
        # and strongly prefer basketball context
        if ("basketball" in nt or "men's basketball" in nt or "mbb" in nt or "matt painter" in nt or "mackey" in nt):
            return True

    return False

# ------------------------ feed URL builders -------------------------

def google_news_rss(q: str, when_days: int) -> str:
    # Pull a lot (ceid=US:en seems to help), sort by date, recent window
    # Note: Google News RSS ignores “when” directly; we’ll filter by date ourselves.
    return f"https://news.google.com/rss/search?q={ul.quote(q)}&hl=en-US&gl=US&ceid=US:en"

def bing_news_rss(q: str) -> str:
    # Bing news RSS supports count param
    return f"https://www.bing.com/news/search?q={ul.quote(q)}&format=rss&setmkt=en-US"

def reddit_rss(sub: str) -> str:
    return f"https://www.reddit.com/r/{sub}/new.rss"

def youtube_channel_rss(channel_id: str) -> str:
    # Standard channel feed
    return f"https://www.youtube.com/feeds/videos.xml?channel_id={ul.quote(channel_id)}"

def youtube_playlist_rss(playlist_id: str) -> str:
    return f"https://www.youtube.com/feeds/videos.xml?playlist_id={ul.quote(playlist_id)}"

# --------------------------- HTTP fetch -----------------------------

def fetch(url: str) -> feedparser.FeedParserDict:
    headers = {"User-Agent": USER_AGENT}
    r = requests.get(url, headers=headers, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    return feedparser.parse(r.content)

# ------------------------- item assembly ----------------------------

def item_id(link: str, title: str) -> str:
    key = (link or "") + "||" + (title or "")
    return hashlib.sha1(key.encode("utf-8", "ignore")).hexdigest()

def sanitize_link(u: str) -> str:
    if not u:
        return u
    p = ul.urlparse(u)
    q = ul.parse_qs(p.query)
    # strip trackers
    for k in list(q.keys()):
        if k.startswith("utm_") or k in {"gclid", "fbclid", "soc_src", "soc_trk"}:
            q.pop(k, None)
    new_q = ul.urlencode({k:v[0] for k,v in q.items()})
    return ul.urlunparse((p.scheme, p.netloc, p.path, p.params, new_q, ""))

def dt_from_entry(e) -> datetime:
    # Try published or updated
    for key in ("published_parsed", "updated_parsed"):
        val = getattr(e, key, None) or e.get(key)
        if val:
            try:
                return datetime.fromtimestamp(time.mktime(val), tz=timezone.utc)
            except Exception:
                pass
    # Fallback: now
    return datetime.now(tz=timezone.utc)

# ------------------------- main collection --------------------------

def collect():
    now = datetime.now(tz=timezone.utc)
    cutoff = now - timedelta(days=FRESH_DAYS)

    items = []
    per_feed_counts = {}
    per_feed_meta = {}
    per_feed_seen = {}

    # 1) News engines (Google & Bing) queries
    for qdef in NEWS_QUERIES:
        label = qdef["label"]
        engine = qdef["engine"]
        q      = qdef["q"]

        if engine == "google":
            url = google_news_rss(q, FRESH_DAYS)
        else:
            url = bing_news_rss(q)

        try:
            feed = fetch(url)
            entries = feed.entries or []
            kept = 0
            seen = 0
            for e in entries:
                seen += 1
                title   = html.unescape(getattr(e, "title", "") or e.get("title", ""))
                link    = sanitize_link(getattr(e, "link", "") or e.get("link", ""))
                summary = html.unescape(getattr(e, "summary", "") or e.get("summary", ""))
                dt      = dt_from_entry(e)
                if dt < cutoff:
                    continue
                dom = domain_of(link)

                if not passes_filters(title, summary, link, dom, force_light=(dom in PURDUE_HEAVY_DOMAINS)):
                    continue

                items.append({
                    "id": item_id(link, title),
                    "title": title[:500],
                    "link": link,
                    "source": label,
                    "domain": dom,
                    "date": dt.isoformat(),
                    "snippet": summary[:1000],
                })
                kept += 1
            per_feed_counts[label] = kept
            per_feed_seen[label] = seen
            per_feed_meta[label] = {"http": 200, "bytes": len(feed.get("feed", {})) + len(entries)}
        except Exception as ex:
            per_feed_counts[label] = 0
            per_feed_seen[label] = 0
            per_feed_meta[label] = {"error": str(ex), "http": 0, "bytes": 0}

    # 2) Reddit subs (strict title filter: must mention Purdue + basketball-ish)
    for rd in REDDIT_SOURCES:
        label = f"Reddit — r/{rd['sub']}"
        url = reddit_rss(rd["sub"])
        try:
            feed = fetch(url)
            entries = feed.entries or []
            kept = 0
            seen = 0
            for e in entries:
                seen += 1
                title = html.unescape(getattr(e, "title", "") or "")
                link  = sanitize_link(getattr(e, "link", "") or "")
                summary = ""
                dt = dt_from_entry(e)
                if dt < cutoff:
                    continue
                dom = domain_of(link) or "reddit.com"
                # Reddit: require Purdue in title & a hoops word
                nt = norm_text(title)
                if not (("purdue" in nt or "boiler" in nt) and ("basketball" in nt or "mbb" in nt or "matt painter" in nt)):
                    continue
                if not passes_filters(title, summary, link, dom, force_light=True):
                    continue
                items.append({
                    "id": item_id(link, title),
                    "title": title[:500],
                    "link": link,
                    "source": label,
                    "domain": dom,
                    "date": dt.isoformat(),
                    "snippet": summary,
                })
                kept += 1
            per_feed_counts[label] = kept
            per_feed_seen[label] = seen
            per_feed_meta[label] = {"http": 200, "bytes": len(feed.get("feed", {})) + len(entries)}
        except Exception as ex:
            per_feed_counts[label] = 0
            per_feed_seen[label] = 0
            per_feed_meta[label] = {"error": str(ex), "http": 0, "bytes": 0}

    # 3) YouTube (official playlist/channel + trusted channels)
    for yt in YOUTUBE_SOURCES:
        label = yt["label"]
        if yt["type"] == "yt_channel":
            url = youtube_channel_rss(yt["id"])
        else:
            url = youtube_playlist_rss(yt["id"])
        try:
            feed = fetch(url)
            entries = feed.entries or []
            kept = 0
            seen = 0
            for e in entries:
                seen += 1
                title = html.unescape(getattr(e, "title", "") or "")
                link  = sanitize_link(getattr(e, "link", "") or "")
                summary = html.unescape(getattr(e, "summary", "") or "")
                dt = dt_from_entry(e)
                if dt < cutoff:
                    continue
                dom = "youtube.com"
                # Require a Purdue/MBB signal unless it's the official Purdue playlist/channel label
                light = ("Purdue MBB" in label) or ("PurdueSports" in label)
                if not passes_filters(title, summary, link, dom, force_light=light):
                    continue
                items.append({
                    "id": item_id(link, title),
                    "title": title[:500],
                    "link": link,
                    "source": label,
                    "domain": dom,
                    "date": dt.isoformat(),
                    "snippet": summary[:600],
                })
                kept += 1
            per_feed_counts[label] = kept
            per_feed_seen[label] = seen
            per_feed_meta[label] = {"http": 200, "bytes": len(feed.get("feed", {})) + len(entries)}
        except Exception as ex:
            per_feed_counts[label] = 0
            per_feed_seen[label] = 0
            per_feed_meta[label] = {"error": str(ex), "http": 0, "bytes": 0}

    # ------------------ dedupe and sort -----------------------------
    # Prefer newest; dedupe by (title+link) id, keep first (newest)
    seen_ids = set()
    deduped = []
    for it in sorted(items, key=lambda x: x["date"], reverse=True):
        if it["id"] in seen_ids:
            continue
        seen_ids.add(it["id"])
        deduped.append(it)

    deduped = deduped[:MAX_ITEMS]

    payload = {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "items_count": len(deduped),
        "items": deduped,
        "fresh_days": FRESH_DAYS,
    }

    if DEBUG:
        payload["per_feed_counts"] = per_feed_counts
        payload["per_feed_seen"] = per_feed_seen
        payload["per_feed_meta"] = per_feed_meta

    tmp_path = ITEMS_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    os.replace(tmp_path, ITEMS_PATH)

    return {
        "ok": True,
        "final_count": len(deduped),
        "per_feed_counts": per_feed_counts,
        "fresh_days": FRESH_DAYS,
    }

# --------------------------- CLI run --------------------------------

def lock_exists():
    try:
        st = os.stat(LOCK_PATH)
        # stale after 10 minutes
        age = time.time() - st.st_mtime
        return age < 600
    except FileNotFoundError:
        return False

def touch_lock():
    with open(LOCK_PATH, "w") as f:
        f.write(str(time.time()))

def clear_lock():
    try:
        os.remove(LOCK_PATH)
    except FileNotFoundError:
        pass

if __name__ == "__main__":
    force = os.environ.get("FORCE", "0") == "1"
    if lock_exists() and not force:
        print(json.dumps({"ok": True, "skipped": True, "reason": "lock_exists"}))
        raise SystemExit(0)
    try:
        touch_lock()
        res = collect()
        print(json.dumps(res))
    except Exception as ex:
        print(json.dumps({"ok": False, "error": str(ex)}))
    finally:
        clear_lock()
