import re
import time
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any
import requests
import feedparser
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("collect")

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/127.0 Safari/537.36"
)
REQ_TIMEOUT = (6, 12)  # connect, read seconds

# --- Feeds: tightly scoped to men's basketball ---
FEEDS = [
    ("Google News", "https://news.google.com/rss/search?q=Purdue%20men%27s%20basketball&hl=en-US&gl=US&ceid=US:en"),
    ("Google News", "https://news.google.com/rss/search?q=Boilermakers%20men%27s%20basketball&hl=en-US&gl=US&ceid=US:en"),
    ("Hammer & Rails", "https://www.hammerandrails.com/rss/index.xml"),
    ("Journal & Courier", "https://rss.app/feeds/RF7ak4i8V5bXb8O7.xml"),  # fallback proxy; fine to keep
    ("Purdue Athletics", "https://purduesports.com/feeds/posts?path=mbball"),  # men's basketball path when available
    # Reddit (handle 429s gracefully)
    ("Reddit", "https://www.reddit.com/r/Boilermakers/search.rss?q=Purdue%20men%27s%20basketball&restrict_sr=on&sort=new&t=month"),
]

EXCLUDE_WORDS = re.compile(
    r"\b(football|wbb|women'?s|volleyball|baseball|softball|soccer|wrestling|hockey|golf|track|cross[- ]country)\b",
    re.I,
)

INCLUDE_HINTS = re.compile(
    r"\b(basketball|hoops|mbb)\b|Matt\s+Painter|Braden\s+Smith|Fletcher\s+Loyer|Lance\s+Jones|"
    r"Trey\s+Kaufman|Myles\s+Colvin|Purdue\s+vs\.|Boilermakers",
    re.I,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _iso_from_struct(t) -> str:
    if not t:
        return _now_iso()
    return datetime(*t[:6], tzinfo=timezone.utc).isoformat()


def canonicalize_url(u: str) -> str:
    """Strip tracking params to help dedupe."""
    try:
        p = urlparse(u)
        q = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
             if not k.lower().startswith(("utm_", "gclid", "fbclid"))]
        return urlunparse(p._replace(query=urlencode(q)))
    except Exception:
        return u


def parse_rss(url: str, source_name: str) -> List[Dict[str, Any]]:
    """Fetch RSS with requests (so we control timeouts/headers), then parse via feedparser."""
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": UA, "Accept": "application/rss+xml,application/xml;q=0.9,*/*;q=0.8"},
            timeout=REQ_TIMEOUT,
        )
        resp.raise_for_status()
    except requests.HTTPError as e:
        code = getattr(e.response, "status_code", None)
        log.warning("[rss-skip] %s -> %s", url, e)
        # Reddit rate limiting (429) is common; just skip
        return []
    except Exception as e:
        log.warning("[rss-skip] %s -> %s", url, e)
        return []

    d = feedparser.parse(resp.content)
    items = []
    for e in d.entries:
        title = (getattr(e, "title", "") or "").strip()
        link = canonicalize_url((getattr(e, "link", "") or "").strip())
        summary = (getattr(e, "summary", "") or "").strip()
        published = _iso_from_struct(getattr(e, "published_parsed", None) or getattr(e, "updated_parsed", None))

        if not title or not link:
            continue

        text = " ".join([title, summary]).lower()
        if "purdue" not in text and "boilermaker" not in text:
            # Still allow explicit MBB hints (e.g., player names), otherwise skip
            if not INCLUDE_HINTS.search(title) and not INCLUDE_HINTS.search(summary):
                continue

        if EXCLUDE_WORDS.search(title) or EXCLUDE_WORDS.search(summary):
            continue

        ok = INCLUDE_HINTS.search(title) or INCLUDE_HINTS.search(summary)
        if not ok:
            # Require explicit basketball context to avoid other sports
            continue

        items.append({
            "title": title,
            "url": link,
            "summary": summary,
            "published": published,
            "source": source_name,
            "source_type": "RSS",
        })
    return items


def dedupe(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for it in items:
        key = (it.get("title", "").lower(), it.get("url", ""))
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out


def collect_all() -> Dict[str, Any]:
    all_items: List[Dict[str, Any]] = []
    for source_name, url in FEEDS:
        batch = parse_rss(url, source_name)
        all_items.extend(batch)

    # Sort newest first
    all_items = dedupe(all_items)
    all_items.sort(key=lambda x: x.get("published", ""), reverse=True)

    return {
        "fetched_at": _now_iso(),
        "count": len(all_items),
        "items": all_items,
    }


def collect_debug() -> Dict[str, Any]:
    data = collect_all()
    by_source: Dict[str, int] = {}
    for it in data["items"]:
        by_source[it["source"]] = by_source.get(it["source"], 0) + 1
    return {
        "fetched_at": data["fetched_at"],
        "total": data["count"],
        "by_source": by_source,
        "example": data["items"][:3],
    }
