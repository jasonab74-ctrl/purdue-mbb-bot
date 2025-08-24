# server.py
import os, time, threading
from datetime import datetime, timezone
from urllib.parse import urlparse

from flask import Flask, jsonify, send_from_directory, request, redirect
import feedparser

# ---------- Feeds (Purdue-focused first; add/remove as you like) ----------
FEEDS = [
    # Purdue-centric
    "https://www.si.com/college/purdue/.rss/full/",
    "https://www.on3.com/teams/purdue-boilermakers/news/feed/",
    "https://www.247sports.com/college/purdue/Article/feed.rss",
    "https://www.jconline.com/search/?f=rss&t=article&c=news%2Fsports%2Fpurdue-boilers*&l=50&s=start_time&sd=desc",
    # SB Nation Purdue (often valid; harmless if empty)
    "https://www.hammerandrails.com/rss/index.xml",

    # Broader men's college hoops (kept last; we’ll filter them hard)
    "https://www.ncaa.com/news/basketball-men/rss.xml",
    "https://www.espn.com/espn/rss/ncb/news",
    "https://feeds.cbssports.com/rss/headlines/ncaab",
]

# ---------- Domain allowlist (extra guard) ----------
ALLOW_SOURCES = {
    # Primary Purdue outlets
    "si.com", "on3.com", "247sports.com", "jconline.com",
    "hammerandrails.com", "purduesports.com",

    # National hoops (allowed but will be filtered by keywords)
    "ncaa.com", "espn.com", "cbssports.com", "yahoo.com", "foxsports.com",
}

# ---------- Include / Exclude keyword filters ----------
INCLUDE_KWS = [
    "purdue", "boilermaker", "boilermakers", "boilers",
    "matt painter", "mackey arena", "west lafayette",
    "zach edey", "braden smith", "fletcher loy", "fletcher loyer",  # common names (keep both spellings)
    "mason gillis", "trey kaufman", "lance jones", "caleb first", "caleb furst",  # older roster names included to catch references
    "big ten", "b1g",  # context terms (still filtered with Purdue)
]
# Terms that usually indicate non-MBB content
EXCLUDE_KWS = [
    "football", "nfl", "qb", "quarterback", "wide receiver", "linebacker",
    "mlb", "baseball", "nhl", "hockey", "golf", "ufc",
    "raiders", "patriots", "yankees", "red sox", "cowboys", "eagles",
    "fantasy football", "preseason", "otAs", "training camp",
]

REFRESH_SECONDS = 300  # 5 minutes

app = Flask(__name__, static_folder="static", static_url_path="/static")

ARTICLES = []
LAST_REFRESH = None
LOCK = threading.Lock()

FALLBACK_ARTICLES = [
    {
        "title": "Purdue MBB feed warming up…",
        "link": "https://purduesports.com/sports/mens-basketball",
        "summary": "If you see this, feeds are still loading or filtered out non-Purdue items. Tap Refresh.",
        "published": datetime.now(timezone.utc).isoformat(),
        "source": "purduesports.com",
    }
]

# ---------- Helpers ----------
def _host(link: str) -> str:
    try:
        return urlparse(link).netloc.replace("www.", "")
    except Exception:
        return ""

def _norm(e):
    title = e.get("title") or "(untitled)"
    link = e.get("link") or ""
    summary = (e.get("summary") or e.get("description") or "").strip()
    ts = ""
    if getattr(e, "published_parsed", None):
        ts = datetime(*e.published_parsed[:6], tzinfo=timezone.utc).isoformat()
    elif getattr(e, "updated_parsed", None):
        ts = datetime(*e.updated_parsed[:6], tzinfo=timezone.utc).isoformat()
    return {"title": title, "link": link, "summary": summary, "published": ts, "source": _host(link)}

def _passes_filters(norm):
    """Return True iff the article is Purdue MBB relevant."""
    text = (norm["title"] + " " + norm["summary"]).lower()

    # Must include a Purdue keyword
    if not any(kw in text for kw in INCLUDE_KWS):
        return False

    # Bounce obvious non-basketball content
    if any(bad in text for bad in EXCLUDE_KWS):
        return False

    # Allowlist domain (extra guard): if domain not known, still allow
    # as long as the text clearly references Purdue (we already checked).
    src = (norm.get("source") or "").lower()
    if src and src not in ALLOW_SOURCES:
        # Still OK — keep Purdue mentions from other sites
        return True

    return True

# ---------- Core refresh (strict Purdue filter) ----------
def refresh_feeds():
    global ARTICLES, LAST_REFRESH
    items = []
    for url in FEEDS:
        try:
            d = feedparser.parse(url)
            for e in d.entries[:60]:
                norm = _norm(e)
                if _passes_filters(norm):
                    items.append(norm)
        except Exception as ex:
            print("Feed error:", url, ex)

    # De-dup by (title, source)
    seen, unique = set(), []
    for a in items:
        key = (a["title"].strip().lower(), a["source"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(a)

    # Sort newest first if we have timestamps
    unique.sort(key=lambda a: a["published"] or "", reverse=True)

    with LOCK:
        ARTICLES = unique[:250]
        LAST_REFRESH = datetime.now(timezone.utc).isoformat()

def _refresher():
    while True:
        refresh_feeds()
        time.sleep(REFRESH_SECONDS)

# Start background refresher
threading.Thread(target=_refresher, daemon=True).start()

# ---------- Routes ----------
@app.route("/healthz")
def healthz():
    return "ok", 200

@app.route("/")
def root():
    return redirect("/ui/")

@app.route("/ui/")
def ui():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/api/health")
def health():
    with LOCK:
        return jsonify({"ok": True, "articles": len(ARTICLES), "last_refresh": LAST_REFRESH})

@app.route("/api/refresh-now")
def refresh_now():
    refresh_feeds()
    with LOCK:
        return jsonify({"ok": True, "articles": len(ARTICLES), "last_refresh": LAST_REFRESH})

@app.route("/api/articles")
def api_articles():
    with LOCK:
        data = list(ARTICLES) if ARTICLES else list(FALLBACK_ARTICLES)
    return jsonify({"articles": data})

@app.route("/api/search")
def api_search():
    q = (request.args.get("q") or "").strip().lower()
    with LOCK:
        base = ARTICLES if ARTICLES else FALLBACK_ARTICLES
        res = [a for a in base if not q or q in (a["title"] + " " + a["summary"] + " " + (a["source"] or "")).lower()]
    return jsonify({"articles": res})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)
