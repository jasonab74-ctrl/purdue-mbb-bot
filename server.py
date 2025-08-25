# collect.py
import time
import re
import html
import hashlib
from typing import List, Dict, Any
import feedparser
import requests

# ---------- Config ----------
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0 Safari/537.36"
)
REQ_TIMEOUT = (6, 15)  # (connect, read)

# Add/adjust feeds any time. These are stable and relevant.
SOURCES: List[Dict[str, str]] = [
    # Google News query (focused on Purdue men's basketball)
    {"name": "Google News", "url": "https://news.google.com/rss/search?q=%22Purdue%22%20%22men%27s%20basketball%22&hl=en-US&gl=US&ceid=US:en"},

    # Hammer & Rails men's basketball section
    {"name": "Hammer & Rails", "url": "https://www.hammerandrails.com/rss/index.xml"},

    # Reddit (broad Purdue + basketball sub)
    {"name": "Reddit r/Boilermakers", "url": "https://www.reddit.com/r/Boilermakers/search.rss?q=men%27s%20basketball&restrict_sr=on&sort=new&t=month"},
    {"name": "Reddit r/PurdueBasketball", "url": "https://www.reddit.com/r/PurdueBasketball/.rss"},
]

# Light relevance gating to keep results on-topic for Purdue MBB
POSITIVE = [
    "men's basketball", "purdue basketball", "purdue men's",
    "boilermakers", "mackey", "big ten", "ncaa",
    "matt painter", "braden smith", "fletcher loyer", "caleb furst",
    "trey kaufman", "will berg", "jack benter"
]
REQUIRE_PURDUE = True  # require "purdue" somewhere in title/summary unless clearly from Purdue sources


# ---------- Helpers ----------
def _clean_text(s: str) -> str:
    """Decode entities, strip HTML tags, collapse whitespace."""
    if not s:
        return ""
    # Some feeds double-escape
    t = html.unescape(html.unescape(s))
    # Remove tags
    t = re.sub(r"<[^>]+>", " ", t, flags=re.S)
    # Collapse spaces
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _epoch(entry: Any) -> int:
    """Choose best available timestamp, fallback to now."""
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


def _parse_rss(url: str) -> feedparser.FeedParserDict:
    blob = _fetch_bytes(url)
    if blob:
        return feedparser.parse(blob)
    # fallback to feedparser’s own request (with UA)
    return feedparser.parse(url, request_headers={"User-Agent": USER_AGENT})


def _is_relevant(title: str, summary: str, source_name: str) -> bool:
    T = f"{title} {summary}".lower()
    # Sources that are inherently Purdue-focused can pass without "purdue"
    source_is_purdue = any(sn in source_name.lower() for sn in [
        "hammer & rails", "purduebasketball", "boilermakers"
    ])
    if REQUIRE_PURDUE and not source_is_purdue and "purdue" not in T:
        return False
    if any(k in T for k in POSITIVE):
        return True
    # If it's clearly labeled men's basketball in general + Purdue keyword present, allow
    if "basketball" in T and "purdue" in T:
        return True
    return False


# ---------- Public API ----------
def collect_all() -> Dict[str, Any]:
    seen = set()
    items: List[Dict[str, Any]] = []
    sources_state: List[Dict[str, Any]] = []

    for src in SOURCES:
        name, url = src["name"], src["url"]
        kept = 0
        fetched = 0
        try:
            d = _parse_rss(url)
            entries = d.entries or []
            fetched = len(entries)

            for e in entries:
                title = _clean_text(getattr(e, "title", "") or e.get("title", ""))
                link = (getattr(e, "link", "") or e.get("link", "") or "").strip()

                # pick any available body
                raw = e.get("summary", "") or e.get("description", "")
                if not raw and e.get("content"):
                    try:
                        raw = e["content"][0].get("value", "")
                    except Exception:
                        pass

                summary_text = _clean_text(raw)

                # basic dedupe key
                if not link:
                    link = "about:blank#" + hashlib.md5((title + summary_text).encode("utf-8")).hexdigest()

                if not title and summary_text:
                    title = summary_text[:120] + "…"

                if not _is_relevant(title, summary_text, name):
                    continue

                key = (name, link)
                if key in seen:
                    continue
                seen.add(key)

                item = {
                    "title": title,
                    "link": link,
                    "source": name,
                    "summary_text": summary_text,  # cleaned (no HTML)
                    "published_ts": _epoch(e),
                }
                items.append(item)
                kept += 1
        except Exception:
            # soft-fail a source
            pass

        sources_state.append({"name": name, "url": url, "fetched": fetched, "kept": kept})

    # newest → oldest
    items.sort(key=lambda x: x.get("published_ts", 0), reverse=True)

    return {
        "count": len(items),
        "items": items,
        "sources": sources_state,
        "updated": int(time.time()),
    }


# Optional debug passthrough used by /api/debug if you want
def collect_debug() -> Dict[str, Any]:
    return collect_all()
