# collect.py
import os, html, traceback
import email.utils as eut
from datetime import datetime, timezone
from typing import List, Dict, Tuple
import requests, feedparser

# ---------------- CONFIG ----------------
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

# (url, is_team_specific, label)
FEEDS: List[Tuple[str, bool, str]] = [
    # --- Team / beat (should be most reliable) ---
    ("https://purduesports.com/rss.aspx?path=mbball", True,  "PurdueSports"),
    ("https://www.on3.com/feeds/team/purdue-boilermakers/", True, "On3 Purdue"),
    ("https://www.sbnation.com/rss/team/purdue-boilermakers/index.xml", True, "Hammer & Rails"),

    # --- Broad Google News (bring volume, then we filter) ---
    ("https://news.google.com/rss/search?q=Purdue+Boilermakers+men%27s+basketball+OR+%22Purdue+basketball%22+OR+%22Purdue+MBB%22&hl=en-US&gl=US&ceid=US:en", False, "GoogleNews broad"),
    ("https://news.google.com/rss/search?q=Purdue+basketball+OR+Boilermakers+basketball&hl=en-US&gl=US&ceid=US:en", False, "GoogleNews alt"),

    # --- Tag/search pages (keep, but may be sparse) ---
    ("https://www.si.com/.rss/full/purdue-boilermakers", False, "SI Purdue"),
    ("https://www.jconline.com/search/?q=Purdue%20basketball&output=rss", False, "J&C"),
    ("https://www.indystar.com/search/?q=Purdue%20basketball&output=rss", False, "IndyStar"),
]

REDDIT_SR = ["Boilermakers", "CollegeBasketball"]

YOUTUBE_CHANNEL_ALLOW = [
    "Field of 68", "Sleepers Media", "Purdue Athletics", "PurdueSports",
    "BTN", "Big Ten Network", "BoilerUpload", "BoilerBall",
]

TEAM_KEYWORDS = [
    "purdue", "boilermaker", "boilermakers", "purdue mbb", "boilerball",
    "matt painter", "braden smith", "fletcher loyer", "caleb furst",
    "trey kaufman", "mason gillis", "zach edey", "boilers"
]

HTTP_TIMEOUT = 20
UA = {"User-Agent": "purdue-mbb-feed/1.1 (+https://example.com)"}
# ---------------- END CONFIG ----------------

# --- lightweight telemetry so /api/debug can show what's happening
STATS = {
    "rss": {"ok": 0, "kept": 0, "skipped": 0},
    "reddit": {"ok": 0, "kept": 0, "skipped": 0},
    "youtube": {"ok": 0, "kept": 0, "skipped": 0},
    "feeds": {},   # label -> kept count
    "errors": []   # recent error strings
}

def _note_error(where: str, err: Exception):
    STATS["errors"].append(f"{where}: {type(err).__name__}: {err}")
    if len(STATS["errors"]) > 20:
        STATS["errors"] = STATS["errors"][-20:]

def _parse_date_guess(s: str) -> str:
    if not s: return datetime.now(timezone.utc).isoformat()
    try:
        dt = eut.parsedate_to_datetime(s)
        if not dt.tzinfo: dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    except Exception:
        pass
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if not dt.tzinfo: dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()

def _clean(s: str) -> str:
    return html.unescape((s or "").strip())

def _looks_purdue(text: str) -> bool:
    t = (text or "").lower()
    return any(k in t for k in TEAM_KEYWORDS)

def fetch_rss() -> List[Dict]:
    items: List[Dict] = []
    for url, team_specific, label in FEEDS:
        try:
            feed = feedparser.parse(url)
            STATS["rss"]["ok"] += 1
            kept_here = 0
            for e in feed.entries[:80]:
                title = _clean(getattr(e, "title", ""))
                link  = getattr(e, "link", "")
                if not title or not link:
                    STATS["rss"]["skipped"] += 1
                    continue
                summary = _clean(getattr(e, "summary", ""))

                # Team-specific: keep almost everything
                keep = True if team_specific else (_looks_purdue(title) or _looks_purdue(summary))
                if not keep:
                    STATS["rss"]["skipped"] += 1
                    continue

                pub = getattr(e, "published", None) or getattr(e, "updated", None) or getattr(e, "pubDate", None)
                items.append({
                    "title": title,
                    "url": link,
                    "published_at": _parse_date_guess(str(pub)),
                    "source": "News",
                    "description": summary[:240],
                })
                STATS["rss"]["kept"] += 1
                kept_here += 1

            if kept_here:
                STATS["feeds"][label] = STATS["feeds"].get(label, 0) + kept_here

        except Exception as err:
            _note_error(f"fetch_rss<{label}>", err)
            continue
    return items

def fetch_reddit() -> List[Dict]:
    out: List[Dict] = []
    for sr in REDDIT_SR:
        try:
            r = requests.get(f"https://www.reddit.com/r/{sr}/new.json?limit=40", headers=UA, timeout=HTTP_TIMEOUT)
            r.raise_for_status()
            STATS["reddit"]["ok"] += 1
            for ch in r.json().get("data", {}).get("children", []):
                d = ch.get("data", {})
                title = _clean(d.get("title", ""))
                body  = _clean(d.get("selftext", ""))
                if not title: 
                    STATS["reddit"]["skipped"] += 1
                    continue
                if not (_looks_purdue(title) or _looks_purdue(body)):
                    STATS["reddit"]["skipped"] += 1
                    continue
                permalink = d.get("permalink", "")
                created_utc = d.get("created_utc")
                when = datetime.fromtimestamp(created_utc, tz=timezone.utc).isoformat() if created_utc else datetime.now(timezone.utc).isoformat()
                out.append({
                    "title": title,
                    "url": f"https://reddit.com{permalink}" if permalink else "https://reddit.com",
                    "published_at": when,
                    "source": f"Reddit r/{sr}",
                    "description": body[:240],
                })
                STATS["reddit"]["kept"] += 1
        except Exception as err:
            _note_error(f"fetch_reddit<r/{sr}>", err)
            continue
    return out

def fetch_youtube() -> List[Dict]:
    if not YOUTUBE_API_KEY:
        _note_error("youtube", Exception("YOUTUBE_API_KEY not set"))
        return []
    results: List[Dict] = []
    seen = set()
    queries = ["Purdue basketball", "Purdue Boilermakers basketball", "Purdue MBB"]
    for q in queries:
        try:
            url = ("https://www.googleapis.com/youtube/v3/search"
                   f"?key={YOUTUBE_API_KEY}&part=snippet&order=date&type=video&maxResults=30&q={requests.utils.quote(q)}")
            r = requests.get(url, timeout=HTTP_TIMEOUT)
            r.raise_for_status()
            STATS["youtube"]["ok"] += 1
            for it in r.json().get("items", []):
                vid = it.get("id", {}).get("videoId")
                if not vid or vid in seen:
                    continue
                sn = it.get("snippet", {}) or {}
                title = _clean(sn.get("title", ""))
                desc  = _clean(sn.get("description", ""))
                ch    = _clean(sn.get("channelTitle", "")) or "YouTube"
                when  = _parse_date_guess(sn.get("publishedAt", ""))

                allowed_channel = any(ch.lower() == a.lower() for a in YOUTUBE_CHANNEL_ALLOW)
                if not (allowed_channel or _looks_purdue(title) or _looks_purdue(desc)):
                    STATS["youtube"]["skipped"] += 1
                    continue

                results.append({
                    "title": title,
                    "url": f"https://www.youtube.com/watch?v={vid}",
                    "published_at": when,
                    "source": ch,
                    "description": desc[:240],
                })
                seen.add(vid)
                STATS["youtube"]["kept"] += 1
        except Exception as err:
            _note_error("fetch_youtube", err)
            continue
    return results

def _dedupe(items: List[Dict]) -> List[Dict]:
    seen = set(); out = []
    for x in items:
        key = (x.get("title","").strip().lower(), x.get("url","").strip().lower())
        if key in seen: continue
        seen.add(key); out.append(x)
    return out

def collect_all() -> List[Dict]:
    STATS["feeds"].clear()
    items: List[Dict] = []
    items += fetch_rss()
    items += fetch_reddit()
    items += fetch_youtube()
    items = _dedupe(items)
    items.sort(key=lambda i: i.get("published_at",""), reverse=True)
    return items[:200]

def collect_debug() -> Dict:
    # shallow copy + current time
    now = datetime.now(timezone.utc).isoformat()
    return {
        "now": now,
        "stats": STATS,
        "feeds_config": [{"url": u, "team_specific": ts, "label": lbl} for (u, ts, lbl) in FEEDS],
        "youtube_key_present": bool(YOUTUBE_API_KEY),
        "team_keywords": TEAM_KEYWORDS,
    }

if __name__ == "__main__":
    import json
    print(json.dumps(collect_all(), indent=2))
