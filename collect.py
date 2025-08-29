#!/usr/bin/env python3
import os, json, time, hashlib, tempfile, logging
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests
import feedparser

# --- import topic config ----
# Only the FEEDS_META list is truly required. Everything else is optional.
from feeds import FEEDS_META  # list of {name, url, category}
# Optional configs with safe fallbacks:
try:
    from feeds import KEYWORDS_EXCLUDE
except Exception:
    KEYWORDS_EXCLUDE = []
try:
    from feeds import SPORT_TOKENS
except Exception:
    SPORT_TOKENS = []
try:
    from feeds import TOTAL_CAP
except Exception:
    TOTAL_CAP = 200
try:
    from feeds import PER_FEED_CAP
except Exception:
    PER_FEED_CAP = 60

# -------- logging ----------
logging.basicConfig(
    level=logging.INFO,
    format="[collector] %(asctime)s %(levelname)s: %(message)s",
)
log = logging.getLogger("collector")

OUTFILE = os.environ.get("ITEMS_PATH", "items.json")
REFRESH_MIN = int(os.environ.get("FEED_REFRESH_MIN", "30"))

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)
HTTP_TIMEOUT = (10, 15)  # (connect, read) seconds

session = requests.Session()
session.headers.update({"User-Agent": UA, "Accept": "application/rss+xml,application/xml;q=0.9,*/*;q=0.8"})


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def fetch_feed(url: str):
    """Fetch raw XML with requests (for UA/timeout control) then parse via feedparser."""
    try:
        resp = session.get(url, timeout=HTTP_TIMEOUT)
        resp.raise_for_status()
        parsed = feedparser.parse(resp.content)
        if parsed.bozo and getattr(parsed, "bozo_exception", None):
            log.warning("feed bozo=%s url=%s err=%s", parsed.bozo, url, parsed.bozo_exception)
        return parsed
    except Exception as e:
        log.error("fetch failed url=%s err=%s", url, e)
        return None


def norm_date(entry):
    # Try several date fields; fall back to now.
    for key in ("published_parsed", "updated_parsed"):
        val = entry.get(key)
        if val:
            try:
                return datetime(*val[:6], tzinfo=timezone.utc).timestamp()
            except Exception:
                pass
    # RFC 822 string fields
    for key in ("published", "updated"):
        val = entry.get(key)
        if val:
            try:
                ts = feedparser._parse_date(val)
                if ts:
                    return datetime(*ts[:6], tzinfo=timezone.utc).timestamp()
            except Exception:
                pass
    return time.time()


def hash_key(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8", "ignore")).hexdigest()[:16]


def text_in(s: str, tokens):
    s = (s or "").lower()
    return any(t.lower() in s for t in tokens)


def keep_entry(entry, hard_excludes, require_tokens):
    title = entry.get("title", "") or ""
    summary = entry.get("summary", "") or ""
    # Drop if any hard-negative appears in title/body
    if text_in(title, hard_excludes) or text_in(summary, hard_excludes):
        return False
    # If we were given positive tokens, require at least one to appear in title or summary
    if require_tokens:
        if not (text_in(title, require_tokens) or text_in(summary, require_tokens)):
            return False
    return True


def collect_once():
    items = []
    total_seen = 0
    total_kept = 0

    for f in FEEDS_META:
        name = f.get("name") or urlparse(f.get("url", "")).netloc
        url = f.get("url")
        category = f.get("category", "")

        if not url:
            log.warning("skip feed with no url: %s", f)
            continue

        parsed = fetch_feed(url)
        if not parsed or not parsed.entries:
            log.warning("no entries for %s", url)
            continue

        kept = 0
        for e in parsed.entries:
            total_seen += 1

            link = e.get("link") or ""
            title = e.get("title") or "(no title)"
            summary = e.get("summary", "")

            if not keep_entry(e, KEYWORDS_EXCLUDE, SPORT_TOKENS):
                continue

            ts = norm_date(e)
            item = {
                "id": hash_key(link or title),
                "title": title.strip(),
                "link": link,
                "source": name,
                "category": category,
                "date": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
                "summary": summary,
            }
            items.append(item)
            kept += 1
            total_kept += 1
            if kept >= PER_FEED_CAP:
                break

        log.info("feed kept=%d seen=%d name=%s", kept, len(parsed.entries), name)

    # Dedupe by id (or link), newest first
    seen = set()
    deduped = []
    for it in sorted(items, key=lambda x: x["date"], reverse=True):
        key = it["id"]
        if key in seen:
            continue
        seen.add(key)
        deduped.append(it)
        if len(deduped) >= TOTAL_CAP:
            break

    # Write atomically
    payload = {"generated_at": _now_iso(), "items": deduped}
    tmp_fd, tmp_path = tempfile.mkstemp(prefix="items.", suffix=".json")
    with os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False)
    os.replace(tmp_path, OUTFILE)

    log.info("wrote %d/%d items to %s", len(deduped), total_kept, OUTFILE)


def main_loop():
    while True:
        try:
            collect_once()
        except Exception as e:
            log.exception("unhandled error: %s", e)
        # Sleep between runs
        sleep_s = max(60, REFRESH_MIN * 60)
        log.info("sleeping %ss", sleep_s)
        time.sleep(sleep_s)


if __name__ == "__main__":
    main_loop()
