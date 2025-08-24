import time
import re
import html
import requests
import feedparser

UA = "Mozilla/5.0 (compatible; PurdueMBBBot/1.0; +https://purdue-mbb-api.onrender.com)"
TIMEOUT = (6, 15)  # (connect, read) seconds

# Lean on Google News for breadth (fast, stable), and Reddit for community.
RSS_SOURCES = [
    # Google News search tuned for Purdue MBB; excludes women's & football.
    ('Google News',
     'https://news.google.com/rss/search?q='
     + requests.utils.quote(
         '(("Purdue men\'s basketball") OR ("Purdue Boilermakers" AND basketball) OR "Matt Painter" OR "Purdue MBB") '
         '-"women\'s" -WBB -volleyball -football -soccer -softball -baseball'
       )
     + '&hl=en-US&gl=US&ceid=US:en'),

    # Reddit — r/Boilermakers, newest posts mentioning basketball/MBB.
    ('Reddit',
     'https://www.reddit.com/r/Boilermakers/search.rss?'
     'q=' + requests.utils.quote('basketball OR "men\'s basketball" OR MBB OR Painter OR Boilers')
     + '&restrict_sr=on&sort=new&t=month'),
]

NEGATIVE = re.compile(r"\b(women|volleyball|football|soccer|softball|baseball|wbb|wbk|w\.?b\.?b)\b", re.I)
MBB_HINT = re.compile(
    r"\b(MBB|men['’]s basketball|basketball team|Matt Painter|Boilermakers(?:\s+basketball)?|Painter|Braden Smith|Fletcher Loyer|Boilers)\b",
    re.I,
)

def _http_bytes(url):
    """Fetch bytes with UA + timeout (avoid feedparser doing the HTTP to reduce hangs)."""
    r = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT)
    # Reddit rate limit: if 429, wait a bit and surface as empty batch (we'll still show other sources)
    if r.status_code == 429:
        time.sleep(1.5)
        raise requests.HTTPError("429 Too Many Requests")
    r.raise_for_status()
    return r.content

def _parse_rss_bytes(b):
    return feedparser.parse(b)

def _clean_text(s):
    if not s:
        return ""
    s = html.unescape(s)
    # strip simple tags
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _looks_like_mbb(title, summary):
    t = (title or "")
    s = (summary or "")
    blob = f"{t}\n{s}"
    if NEGATIVE.search(blob):
        return False
    # accept if it mentions basketball + Purdue-ish term, or strong hints (MBB, Painter, etc.)
    if re.search(r"\b(basketball)\b", blob, re.I) and re.search(r"\b(Purdue|Boilermakers|Painter)\b", blob, re.I):
        return True
    if MBB_HINT.search(blob):
        return True
    return False

def collect_all():
    out = []
    now = int(time.time())
    for source_name, url in RSS_SOURCES:
        try:
            b = _http_bytes(url)
            feed = _parse_rss_bytes(b)
        except Exception:
            # Skip on any network error; keep the app responsive.
            continue

        for e in feed.get("entries", []):
            title = _clean_text(e.get("title"))
            summary = _clean_text(e.get("summary") or e.get("description"))
            link = e.get("link") or ""
            if not title or not link:
                continue
            if not _looks_like_mbb(title, summary):
                continue

            # published time
            ts = None
            for key in ("published_parsed", "updated_parsed", "created_parsed"):
                t = e.get(key)
                if t:
                    try:
                        ts = int(time.mktime(t))
                        break
                    except Exception:
                        pass
            if not ts:
                ts = now

            out.append({
                "title": title[:300],
                "summary": summary[:600] if summary else "",
                "link": link,
                "source": source_name,
                "published_ts": ts,
            })

        # be nice between sources
        time.sleep(0.4)

    # sort newest first & dedupe by link
    seen = set()
    deduped = []
    for item in sorted(out, key=lambda x: x["published_ts"], reverse=True):
        if item["link"] in seen:
            continue
        seen.add(item["link"])
        deduped.append(item)

    # keep a sane number
    return deduped[:80]

def collect_debug():
    items = collect_all()
    return {
        "now": int(time.time()),
        "counts": {"total": len(items), "by_source": _by_src(items)},
        "sample": items[:8],
        "sources": [s for s in RSS_SOURCES],
    }

def _by_src(items):
    d = {}
    for it in items:
        d[it["source"]] = d.get(it["source"], 0) + 1
    return d
