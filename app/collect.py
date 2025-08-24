# collect.py
import os
import html
import email.utils as eut
from datetime import datetime, timezone
from typing import List, Dict, Tuple

import requests
import feedparser

# ------------ CONFIG ------------
# YouTube
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

# Each feed is (url, is_team_specific)
# If is_team_specific=True we will keep almost everything (minimal filtering).
FEEDS: List[Tuple[str, bool]] = [
    # --- Team-specific (keep almost everything) ---
    ("https://purduesports.com/rss.aspx?path=mbball", True),                    # Official Purdue MBB
    ("https://www.on3.com/feeds/team/purdue-boilermakers/", True),             # On3 Purdue
    ("https://www.sbnation.com/rss/team/purdue-boilermakers/index.xml", True), # Hammer & Rails

    # --- Purdue tag/search pages (still filtered by keywords) ---
    ("https://www.si.com/.rss/full/purdue-boilermakers", False),               # SI Purdue tag
    ("https://www.jconline.com/search/?q=Purdue%20basketball&output=rss", False),  # Lafayette J&C
    ("https://www.indystar.com/search/?q=Purdue%20basketball&output=rss", False),  # IndyStar

    # --- Google News (broad but filtered by keywords below) ---
    ("https://news.google.com/rss/search?q=Purdue+Boilermakers+men%27s+basketball&hl=en-US&gl=US&ceid=US:en", False),
    ("https://news.google.com/rss/search?q=%22Purdue+basketball%22+OR+%22Purdue+MBB%22&hl=en-US&gl=US&ceid=US:en", False),
    ("https://news.google.com/rss/search?q=Purdue+Boilermakers+basketball+site:espn.com&hl=en-US&gl=US&ceid=US:en", False),
    ("https://news.google.com/rss/search?q=Purdue+Boilermakers+basketball+site:yahoo.com&hl=en-US&gl=US&ceid=US:en", False),
    ("https://news.google.com/rss/search?q=Purdue+Boilermakers+basketball+site:cbssports.com&hl=en-US&gl=US&ceid=US:en", False),
    ("https://news.google.com/rss/search?q=Purdue+Boilermakers+basketball+site:theathletic.com&hl=en-US&gl=US&ceid=US:en", False),
    ("https://news.google.com/rss/search?q=Purdue+Boilermakers+basketball+site:usatoday.com&hl=en-US&gl=US&ceid=US:en", False),
    ("https://news.google.com/rss/search?q=Purdue+Boilermakers+basketball+site:apnews.com&hl=en-US&gl=US&ceid=US:en", False),

    # --- Regional/beat (search RSS) ---
    ("https://www.wlfi.com/search/?f=rss&t=article&s=start_time&sd=desc&q=Purdue%20basketball", False),   # WLFI (Lafayette)
    ("https://www.journalgazette.net/search/?f=rss&c=news*&q=Purdue%20basketball", False),                # Fort Wayne JG
    ("https://www.nwitimes.com/search/?f=rss&t=article&q=Purdue%20basketball&s=start_time&sd=desc", False),# NW Indiana Times
]

# Reddit subs (keyword-filtered)
REDDIT_SR = ["Boilermakers", "CollegeBasketball"]

# YouTube channels we trust (by display name). We also keyword-filter titles/descriptions.
YOUTUBE_CHANNEL_ALLOW = [
    "Field of 68",
    "Sleepers Media",
    "Purdue Athletics",
    "PurdueSports",
    "BTN",
    "Big Ten Network",
    "BoilerUpload",
    "BoilerBall",
]

TEAM_KEYWORDS = [
    "Purdue", "Boilermaker", "Boilermakers", "Purdue MBB", "BoilerBall",
    "Matt Painter", "Braden Smith", "Fletcher Loyer", "Caleb Furst", "Trey Kaufman",
    "Mason Gillis", "Zach Edey", "Boilers"
]

HTTP_TIMEOUT = 20
UA = {"User-Agent": "purdue-mbb-feed/1.0 (+https://example.com)"}
# ------------ END CONFIG ------------


def _parse_date_guess(s: str) -> str:
    if not s:
        return datetime.now(timezone.utc).isoformat()
    try:
        dt = eut.parsedate_to_datetime(s)  # RFC 2822 (common in RSS)
        if not dt.tzinfo:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    except Exception:
        pass
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))  # ISO fallback
        if not dt.tzinfo:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()


def _clean(s: str) -> str:
    return html.unescape((s or "").strip())


def _looks_purdue(text: str) -> bool:
    t = (text or "").lower()
    return any(k.lower() in t for k in TEAM_KEYWORDS)


def fetch_rss() -> List[Dict]:
    out: List[Dict] = []
    for url, team_specific in FEEDS:
        try:
            feed = feedparser.parse(url)
            for e in feed.entries[:50]:
                title = _clean(getattr(e, "title", ""))
                link = getattr(e, "link", "")
                if not title or not link:
                    continue
                summary = _clean(getattr(e, "summary", ""))

                # Filter only if not explicitly team-specific
                if not team_specific and not (_looks_purdue(title) or _looks_purdue(summary)):
                    continue

                pub = (
                    getattr(e, "published", None)
                    or getattr(e, "updated", None)
                    or getattr(e, "pubDate", None)
                )
                published_at = _parse_date_guess(str(pub))

                out.append({
                    "title": title,
                    "url": link,
                    "published_at": published_at,
                    "source": "News",
                    "description": summary[:240],
                })
        except Exception:
            continue
    return out


def fetch_reddit() -> List[Dict]:
    items: List[Dict] = []
    for sr in REDDIT_SR:
        try:
            r = requests.get(
                f"https://www.reddit.com/r/{sr}/new.json?limit=30",
                headers=UA,
                timeout=HTTP_TIMEOUT
            )
            r.raise_for_status()
            for ch in r.json().get("data", {}).get("children", []):
                d = ch.get("data", {})
                title = _clean(d.get("title", ""))
                body = _clean(d.get("selftext", ""))
                if not title:
                    continue
                if not (_looks_purdue(title) or _looks_purdue(body)):
                    continue
                permalink = d.get("permalink", "")
                created_utc = d.get("created_utc", None)
                if created_utc:
                    published_at = datetime.fromtimestamp(created_utc, tz=timezone.utc).isoformat()
                else:
                    published_at = datetime.now(timezone.utc).isoformat()
                items.append({
                    "title": title,
                    "url": f"https://reddit.com{permalink}" if permalink else "https://reddit.com",
                    "published_at": published_at,
                    "source": f"Reddit r/{sr}",
                    "description": body[:240],
                })
        except Exception:
            continue
    return items


def fetch_youtube() -> List[Dict]:
    if not YOUTUBE_API_KEY:
        return []
    results: List[Dict] = []
    queries = ["Purdue basketball", "Purdue Boilermakers basketball", "Purdue MBB"]
    seen = set()
    for q in queries:
        try:
            url = (
                "https://www.googleapis.com/youtube/v3/search"
                f"?key={YOUTUBE_API_KEY}"
                "&part=snippet&order=date&type=video&maxResults=30"
                f"&q={requests.utils.quote(q)}"
            )
            r = requests.get(url, timeout=HTTP_TIMEOUT)
            r.raise_for_status()
            for it in r.json().get("items", []):
                vid = it.get("id", {}).get("videoId")
                if not vid or vid in seen:
                    continue
                sn = it.get("snippet", {}) or {}
                title = _clean(sn.get("title", ""))
                desc = _clean(sn.get("description", ""))
                ch = _clean(sn.get("channelTitle", "")) or "YouTube"
                when = _parse_date_guess(sn.get("publishedAt", ""))

                allowed_channel = any(ch.lower() == a.lower() for a in YOUTUBE_CHANNEL_ALLOW)
                if not (allowed_channel or _looks_purdue(title) or _looks_purdue(desc)):
                    continue

                results.append({
                    "title": title,
                    "url": f"https://www.youtube.com/watch?v={vid}",
                    "published_at": when,
                    "source": ch,
                    "description": desc[:240],
                })
                seen.add(vid)
        except Exception:
            continue
    return results


def _dedupe(items: List[Dict]) -> List[Dict]:
    seen = set()
    out: List[Dict] = []
    for x in items:
        key = (x.get("title", "").strip().lower(), x.get("url", "").strip().lower())
        if key in seen:
            continue
        seen.add(key)
        out.append(x)
    return out


def collect_all() -> List[Dict]:
    items: List[Dict] = []
    items.extend(fetch_rss())
    items.extend(fetch_reddit())
    items.extend(fetch_youtube())
    items = _dedupe(items)
    items.sort(key=lambda i: i.get("published_at", ""), reverse=True)
    return items[:200]


if __name__ == "__main__":
    import json
    print(json.dumps(collect_all(), indent=2))
