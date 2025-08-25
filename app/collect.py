# collect.py
import time, re, html, hashlib
from typing import List, Dict, Any
import feedparser
import requests

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0 Safari/537.36"
)
REQ_TIMEOUT = (6, 15)  # (connect, read)

SOURCES: List[Dict[str, str]] = [
    # Google News – multiple focused queries to increase volume but stay MBB
    {"name": "Google News", "url": "https://news.google.com/rss/search?q=%22Purdue%22%20%22men%27s%20basketball%22&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Google News", "url": "https://news.google.com/rss/search?q=%22Purdue%20Boilermakers%22%20basketball&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Google News", "url": "https://news.google.com/rss/search?q=%22Matt%20Painter%22%20Purdue&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Google News", "url": "https://news.google.com/rss/search?q=%22Braden%20Smith%22%20Purdue&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Google News", "url": "https://news.google.com/rss/search?q=%22Fletcher%20Loyer%22%20Purdue&hl=en-US&gl=US&ceid=US:en"},

    # Team/beat sites (some occasionally rate-limit; we fail soft)
    {"name": "Hammer & Rails", "url": "https://www.hammerandrails.com/rss/index.xml"},
    {"name": "Sports Illustrated (Purdue)", "url": "https://www.si.com/college/purdue/.rss"},
    {"name": "Journal & Courier Purdue", "url": "https://rss.app/feeds/2iN67Qv7t9C1p7dS.xml"},
    {"name": "Purdue Exponent", "url": "https://www.purdueexponent.org/search/?f=rss&c=news%2Csports&t=article&l=25&s=start_time&sd=desc"},
    {"name": "GoldandBlack", "url": "https://www.on3.com/feeds/goldandblack/purdue/"},

    # Reddit (soft-fail if 429)
    {"name": "Reddit r/Boilermakers", "url": "https://www.reddit.com/r/Boilermakers/search.rss?q=Purdue%20men%27s%20basketball&restrict_sr=on&sort=new&t=month"},
]

POSITIVE = [
    "basketball", "men's basketball", "mbb", "matt painter", "purdue hoops",
    "boilers hoops", "mackey", "braden smith", "fletcher loyer", "caleb furst",
    "trey kaufman", "will berg", "jack benter", "camden", "purdue guard",
    "purdue forward", "boilermakers guard", "big ten tournament", "ncaa tournament",
]

NEGATIVE = [
    "football","soccer","baseball","softball","volleyball","wrestling","hockey",
    "track","cross country","swimming","golf","tennis","rowing","women's",
    "women’s","wbb","wbasketball","soft launch", "recruiting visit (football)"
]

def _clean_text(s: str) -> str:
    if not s:
        return ""
    # decode HTML entities twice (some feeds double-escape)
    t = html.unescape(html.unescape(s))
    # strip tags
    t = re.sub(r"<[^>]+>", " ", t, flags=re.S)
    # collapse whitespace
    t = re.sub(r"\s+", " ", t).strip()
    return t

def _is_mbb_relevant(title: str, summary: str) -> bool:
    T = f"{title} {summary}".lower()
    if not any(k in T for k in POSITIVE):
        # allow Purdue + generic "roster" or "schedule" mentions if not negs
        if not (("purdue" in T) and ("basket" in T)):
            return False
    if any(k in T for k in NEGATIVE):
        # allow if explicitly men's basketball appears
        if "men" not in T or "basket" not in T:
            return False
    return True

def _epoch(entry: Any) -> int:
    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        v = entry.get(key)
        if v:
            try:
                return int(time.mktime(v))
            except Exception:
                pass
    return int(time.time())

def _fetch_bytes(url: str) -> bytes:
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQ_TIMEOUT)
        r.raise_for_status()
        return r.content
    except Exception:
        return b""

def parse_rss(url: str) -> feedparser.FeedParserDict:
    blob = _fetch_bytes(url)
    if blob:
        return feedparser.parse(blob)
    # fallback to feedparser’s internal fetcher (still with UA)
    return feedparser.parse(url, request_headers={"User-Agent": USER_AGENT})

def collect_all() -> Dict[str, Any]:
    seen = set()
    items: List[Dict[str, Any]] = []
    sources_state: List[Dict[str, Any]] = []
    for src in SOURCES:
        name, url = src["name"], src["url"]
        kept = 0
        try:
            d = parse_rss(url)
            fetched = len(d.entries or [])
            for e in d.entries or []:
                title = _clean_text(getattr(e, "title", "") or e.get("title", ""))
                link = (getattr(e, "link", "") or e.get("link", "") or "").strip()
                # pick first available body
                raw = e.get("summary", "") or e.get("description", "")
                if not raw and e.get("content"):
                    try:
                        raw = e["content"][0].get("value", "")
                    except Exception:
                        pass
                summary_text = _clean_text(raw)
                if not title and summary_text:
                    title = summary_text[:120] + "…"
                if not link:
                    # build a stable pseudo-link to dedupe
                    link = "about:blank#" + hashlib.md5((title + summary_text).encode("utf-8")).hexdigest()

                if not _is_mbb_relevant(title, summary_text):
                    continue

                key = (name, link)
                if key in seen:
                    continue
                seen.add(key)

                item = {
                    "title": title,
                    "link": link,
                    "source": name,
                    "summary_text": summary_text,
                    "published_ts": _epoch(e),
                }
                items.append(item)
                kept += 1
        except Exception:
            fetched = 0
        sources_state.append({"name": name, "url": url, "fetched": fetched, "kept": kept})

    items.sort(key=lambda x: x["published_ts"], reverse=True)
    return {
        "count": len(items),
        "items": items,
        "sources": sources_state,
        "updated": int(time.time()),
    }

# Utilities used by server.py
def collect_debug() -> Dict[str, Any]:
    return collect_all()
