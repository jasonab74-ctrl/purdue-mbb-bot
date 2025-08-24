from __future__ import annotations
import time, re, html
from typing import Dict, List
import requests
import feedparser

UA = "purdue-mbb-bot/1.0 (+https://purdue-mbb-api.onrender.com)"
CONNECT_TO = 5
READ_TO = 10

# Sources: keep it small & fast so gunicorn doesn’t time out
GOOGLE_NEWS = (
    'https://news.google.com/rss/search?q='
    '"Purdue%20men%27s%20basketball"%20OR%20'
    '"Boilermakers%20basketball"%20OR%20'
    '"Matt%20Painter"%20OR%20'
    '"Purdue%20Boilermakers"%20basketball&hl=en-US&gl=US&ceid=US:en'
)
REDDIT_RSS = (
    "https://www.reddit.com/r/Boilermakers/search.rss"
    "?q=Purdue%20men%27s%20basketball&restrict_sr=on&sort=new&t=month"
)

NEG = re.compile(
    r"\b(football|soccer|volleyball|softball|baseball|women'?s|wbb|hockey|wrestling|golf|swim|track)\b",
    re.I,
)
# Require Purdue + basketball context somewhere
REQ = re.compile(r"\b(purdue|boilermaker)\b.*\b(basketball|mbb|painter)\b", re.I)

_last_errors: List[str] = []
_last_skips: List[str] = []

def _get(url: str) -> bytes | None:
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=(CONNECT_TO, READ_TO))
        r.raise_for_status()
        return r.content
    except Exception as e:
        _last_errors.append(f"[get-fail] {url} -> {e}")
        return None

def parse_rss(url: str, label: str) -> List[Dict]:
    data = _get(url)
    if data is None:
        return []
    d = feedparser.parse(data)
    items = []
    for e in d.entries[:40]:
        title = html.unescape(getattr(e, "title", "") or "")
        summary = html.unescape(getattr(e, "summary", "") or "")
        link = getattr(e, "link", "") or ""
        published = getattr(e, "published", "") or getattr(e, "updated", "") or ""
        text = f"{title} {summary}"

        # MBB-only filter
        if NEG.search(text):
            _last_skips.append(f"[neg] {label} :: {title[:70]}")
            continue
        if not (("purdue" in text.lower() or "boilermaker" in text.lower()) and ("basketball" in text.lower() or "painter" in text.lower() or "mbb" in text.lower())):
            _last_skips.append(f"[not-mbb] {label} :: {title[:70]}")
            continue

        items.append({
            "title": title.strip(),
            "summary": summary.strip(),
            "link": link,
            "published": published,
            "source": label,
        })
    return items

def collect_all() -> Dict:
    start = time.time()
    items: List[Dict] = []
    stats = {"by_source": {}, "errors": [], "skips": 0}

    # Google News
    g = parse_rss(GOOGLE_NEWS, "Google News")
    items.extend(g); stats["by_source"]["Google News"] = len(g)

    # Reddit (skip cleanly if rate-limited)
    before_errs = len(_last_errors)
    r = parse_rss(REDDIT_RSS, "Reddit")
    items.extend(r); stats["by_source"]["Reddit"] = len(r)
    if len(_last_errors) > before_errs and "429" in _last_errors[-1]:
        # mark that we skipped due to rate limit
        stats["by_source"]["Reddit_note"] = "rate-limited; skipped"

    # sort newest-ish first when pub date string present
    def _key(x):  # crude; feedparser dates vary widely
        return x.get("published", ""), x.get("title", "")
    items.sort(key=_key, reverse=True)

    # trim to 150 to keep payloads tight
    items = items[:150]

    stats["skips"] = len(_last_skips)
    stats["errors"] = list(_last_errors)[-8:]
    stats["elapsed_ms"] = int((time.time() - start) * 1000)

    # Reset skip log between runs so it doesn’t grow forever
    _last_skips.clear()
    return {"items": items, "stats": stats}

def collect_debug() -> Dict:
    # One lightweight sample to show counters without doing a full scrape
    return {
        "sources": ["Google News", "Reddit"],
        "notes": "Filters men’s basketball only; excludes football/baseball/etc; Reddit may rate-limit (we skip).",
        "errors_tail": list(_last_errors)[-8:],
    }
