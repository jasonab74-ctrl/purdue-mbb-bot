# app/collect.py
# Aggregate Purdue MBB feeds -> data/news.json
# Works with feeds.py (FEEDS list). Requires: feedparser

import os
import json
import time
import re
import html
import logging
from pathlib import Path
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse, parse_qsl

import feedparser

# ---------------------- Config ----------------------

# Where to write the merged JSON that server.py reads
DATA_PATH = Path(os.environ.get("DATA_PATH", "data/news.json"))

# Number of items to keep overall (after sorting)
MAX_TOTAL_ITEMS = int(os.environ.get("MAX_TOTAL_ITEMS", "500"))

# If you keep a Google News feed, limit how many of its items we take
GOOGLE_NEWS_MAX = int(os.environ.get("GOOGLE_NEWS_MAX", "10"))

# Identify ourselves for politeness / fewer 403s
REQUEST_HEADERS = {
    "User-Agent": "Purdue-MBB-FeedBot/1.0 (+https://github.com/you/yourrepo)"
}

# ---------------------- Feeds -----------------------

try:
    # Expect feeds.py to live alongside this file or on PYTHONPATH
    from feeds import FEEDS  # required
except Exception as e:
    raise SystemExit(f"ERROR: could not import FEEDS from feeds.py: {e}")

# Optional helper: if user kept a separate Google News tuple
try:
    from feeds import GOOGLE_NEWS_FEED  # optional
    HAS_GOOGLE_NEWS = True
except Exception:
    GOOGLE_NEWS_FEED = None
    HAS_GOOGLE_NEWS = False

# ---------------------- Utils ----------------------


def strip_tags(s: str) -> str:
    """Turn HTML into plain text (UI shows summary_text)."""
    if not s:
        return ""
    # Unescape entities first so tags like &lt;a&gt; become <a>
    s = html.unescape(s)
    # Remove tags
    s = re.sub(r"<[^>]+>", " ", s)
    # Collapse whitespace
    s = re.sub(r"\s+", " ", s).strip()
    return s


def unwrap_google_news(url: str) -> str:
    """If this is a news.google.com link, return the embedded original URL."""
    try:
        p = urlparse(url)
        if "news.google.com" in p.netloc:
            q = parse_qs(p.query)
            if "url" in q and q["url"]:
                return q["url"][0]
    except Exception:
        pass
    return url


def canonicalize_url(url: str) -> str:
    """Normalize URL (remove UTM etc.) for dedupe."""
    if not url:
        return url
    url = unwrap_google_news(url)

    p = urlparse(url)
    # strip tracking params commonly seen
    allow = []
    for k, v in parse_qsl(p.query, keep_blank_values=True):
        if not k.lower().startswith(("utm_", "gclid", "oc")):
            allow.append((k, v))
    new_qs = urlencode(allow, doseq=True)

    # Normalize scheme/host casing; path as-is
    p = p._replace(netloc=p.netloc.lower(), scheme=p.scheme.lower(), query=new_qs)
    return urlunparse(p)


def as_epoch(struct_time) -> int | None:
    try:
        return int(time.mktime(struct_time))
    except Exception:
        return None


def best_published_ts(entry) -> int:
    """Pick the best available timestamp for an entry; fallback to 'now'."""
    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        st = entry.get(key)
        if st:
            ts = as_epoch(st)
            if ts:
                return ts
    return int(time.time())


def parse_feed(name: str, url: str) -> list[dict]:
    """Return list of normalized items from a single feed."""
    logging.info("Fetching: %s — %s", name, url)
    d = feedparser.parse(url, request_headers=REQUEST_HEADERS)

    items = []
    for e in d.entries:
        title = e.get("title") or "(untitled)"
        link = e.get("link") or ""

        # Prefer 'content' -> 'summary' -> ''
        summary_html = ""
        if "content" in e and e.content:
            # content is a list of dicts
            summary_html = " ".join(part.get("value", "") for part in e.content)
        else:
            summary_html = e.get("summary", "") or e.get("description", "")

        # Some feeds (YT) have media descriptions in 'summary'; still fine
        pub_ts = best_published_ts(e)

        # Normalize / unwrap links for dedupe
        link = canonicalize_url(link)

        items.append(
            {
                "source": name,
                "title": strip_tags(title),
                "link": link,
                "summary": summary_html,  # keep raw for future, UI uses summary_text
                "summary_text": strip_tags(summary_html),
                "published_ts": pub_ts,
                # Optional extras (harmless if missing in UI)
                "published": e.get("published", "") or e.get("updated", "") or "",
                "id": e.get("id") or link,
            }
        )

    # Optional cap for Google News noise
    if "google news" in name.lower():
        items = items[:GOOGLE_NEWS_MAX]

    return items


# ---------------------- Core -----------------------


def collect_all() -> dict:
    """Fetch all feeds, merge, dedupe, sort newest->oldest, write JSON."""
    t0 = time.time()

    # Build list of (name, url) in desired order
    feed_list = list(FEEDS)
    if HAS_GOOGLE_NEWS and isinstance(GOOGLE_NEWS_FEED, tuple):
        feed_list.append(GOOGLE_NEWS_FEED)

    all_items: list[dict] = []
    for name, url in feed_list:
        try:
            all_items.extend(parse_feed(name, url))
        except Exception as e:
            logging.exception("Feed failed: %s — %s", name, e)

    # De-dupe by canonical link first, then fallback to (title, source)
    seen_links = set()
    deduped: list[dict] = []
    for it in all_items:
        key = (it.get("link") or "").lower()
        if key and key not in seen_links:
            seen_links.add(key)
            deduped.append(it)
            continue
        # Fallback key
        key2 = (it.get("title", "").lower(), it.get("source", "").lower())
        if key2 not in seen_links:
            seen_links.add(key2)
            deduped.append(it)

    # Sort newest → oldest
    deduped.sort(key=lambda x: x.get("published_ts", 0), reverse=True)

    # Trim overall
    if len(deduped) > MAX_TOTAL_ITEMS:
        deduped = deduped[:MAX_TOTAL_ITEMS]

    out = {
        "updated_ts": int(time.time()),
        "items": deduped,
        "took_ms": int((time.time() - t0) * 1000),
        "count": len(deduped),
    }

    # Ensure folder exists and write atomically
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = DATA_PATH.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    tmp.replace(DATA_PATH)

    logging.info("Wrote %s items to %s in %d ms", len(deduped), DATA_PATH, out["took_ms"])
    return out


# ---------------------- CLI ------------------------


def main():
    logging.basicConfig(
        level=os.environ.get("LOGLEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(message)s",
    )
    out = collect_all()
    # Print a tiny summary for logs/Render
    print(json.dumps({"count": out["count"], "updated_ts": out["updated_ts"]}))


if __name__ == "__main__":
    main()
