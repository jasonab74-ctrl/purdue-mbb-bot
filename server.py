# server.py
import os, time, threading
from datetime import datetime, timezone
from urllib.parse import urlparse
from flask import Flask, jsonify, send_from_directory, request, redirect
import feedparser

# ---------- Purdue Basketball Sources ----------
FEEDS = [
    "https://purduesports.com/rss_feeds.aspx?path=mbball",  # Official site
    "https://www.si.com/college/purdue/.rss/full/",
    "https://www.247sports.com/college/purdue/Article/feed.rss",
    "https://www.on3.com/teams/purdue-boilermakers/news/feed/",
    "https://www.jconline.com/search/?f=rss&t=article&c=news%2Fsports%2Fpurdue-boilers*&l=50&s=start_time&sd=desc",
    "https://www.hammerandrails.com/rss/index.xml",

    # Reddit
    "https://www.reddit.com/r/Purdue/.rss",
    "https://www.reddit.com/r/Boilermakers/.rss",
    "https://www.reddit.com/r/CollegeBasketball/search.rss?q=Purdue&restrict_sr=on&sort=new",

    # National NCAA Basketball feeds
    "https://www.ncaa.com/news/basketball-men/rss.xml",
    "https://www.espn.com/espn/rss/ncb/news",
    "https://feeds.cbssports.com/rss/headlines/ncaab",
]

REFRESH_SECONDS = 300  # 5 minutes

# ---------- Basketball keyword filters ----------
INCLUDE_KWS = [
    "basketball", "mbb", "matt painter", "mackey",
    "march madness", "final four", "big ten", "ncaa",
    "zach edey", "braden smith", "fletcher loyer",
    "caleb furst", "trey kaufman", "mason gillis", "lance jones"
]

EXCLUDE_KWS = [
    "football", "nfl", "quarterback", "ryan walters", "odoom",
    "offense", "defense", "huskers", "raiders", "patriots",
    "mlb", "baseball", "hockey", "soccer", "golf", "ufc"
]

app = Flask(__name__, static_folder="static", static_url_path="/static")

ARTICLES = []
LAST_REFRESH = None
LOCK = threading.Lock()

FALLBACK_ARTICLES = [{
    "title": "Purdue MBB feed warming up…",
    "link": "https://purduesports.com/sports/mens-basketball",
    "summary": "If you see this, feeds are still loading. Try refresh.",
    "published": datetime.now(timezone.utc).isoformat(),
    "source": "purduesports.com",
}]

# ---------- Helpers ----------
def _host(link: str) -> str:
    try: return urlparse(link).netloc.replace("www.", "")
    except: return ""

def _norm(e):
    title = e.get("title") or "(untitled)"
    link = e.get("link") or ""
    # Prefer full article body if available
    summary = (e.get("content")[0].value if e.get("content") else e.get("summary") or e.get("description") or "").strip()
    ts = ""
    if getattr(e, "published_parsed", None):
        ts = datetime(*e.published_parsed[:6], tzinfo=timezone.utc).isoformat()
    elif getattr(e, "updated_parsed", None):
        ts = datetime(*e.updated_parsed[:6], tzinfo=timezone.utc).isoformat()
    return {"title": title, "link": link, "summary": summary, "published": ts, "source": _host(link)}

def _passes_filters(norm):
    text = (norm["title"] + " " + norm["summary"]).lower()
    if not any(kw in text for kw in INCLUDE_KWS): return False
    if any(bad in text for bad in EXCLUDE_KWS): return False
    return True

# ---------- Refresh feeds ----------
def refresh_feeds():
    global ARTICLES, LAST_REFRESH
    items = []
    for url in FEEDS:
        try:
            d = feedparser.parse(url)
            for e in d.entries[:40]:
                norm = _norm(e)
                if _passes_filters(norm):
                    items.append(norm)
        except Exception as ex:
            print("Feed error:", url, ex)

    # De-dup
    seen, unique = set(), []
    for a in items:
        key = (a["title"].strip().lower(), a["source"])
        if key not in seen:
            seen.add(key)
            unique.append(a)

    unique.sort(key=lambda a: a["published"] or "", reverse=True)
    with LOCK:
        ARTICLES[:] = unique[:200]
        LAST_REFRESH = datetime.now(timezone.utc).isoformat()

def _refresher():
    while True:
        refresh_feeds()
        time.sleep(REFRESH_SECONDS)

import threading
threading.Thread(target=_refresher, daemon=True).start()

# ---------- Routes ----------
@app.route("/healthz")
def healthz(): return "ok", 200

@app.route("/")
def root(): return redirect("/ui/")

@app.route("/ui/")
def ui(): return send_from_directory(app.static_folder, "index.html")

@app.route("/api/health")
def health():
    with LOCK: return jsonify({"ok": True, "articles": len(ARTICLES), "last_refresh": LAST_REFRESH})

@app.route("/api/refresh-now")
def refresh_now():
    refresh_feeds()
    with LOCK: return jsonify({"ok": True, "articles": len(ARTICLES), "last_refresh": LAST_REFRESH})

@app.route("/api/articles")
def api_articles():
    with LOCK: data = ARTICLES if ARTICLES else FALLBACK_ARTICLES
    return jsonify({"articles": data})

@app.route("/api/search")
def api_search():
    q = (request.args.get("q") or "").strip().lower()
    with LOCK:
        base = ARTICLES if ARTICLES else FALLBACK_ARTICLES
        res = [a for a in base if not q or q in (a["title"] + " " + a["summary"]).lower()]
    return jsonify({"articles": res})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)
