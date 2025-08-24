# app/api.py
import os, time, threading
from datetime import datetime, timezone
from urllib.parse import urlparse
from flask import Flask, jsonify, send_from_directory, request, redirect
import feedparser

# ---------- Config ----------
FEEDS = [
    # Two reliable test feeds to guarantee content
    "https://hnrss.org/frontpage",
    "https://www.espn.com/espn/rss/news",
    # Add your college hoops / Purdue sources below
    "https://www.espn.com/espn/rss/ncb/news",
    "https://feeds.cbssports.com/rss/headlines/ncaab",
    "https://www.ncaa.com/news/basketball-men/rss.xml",
    "https://www.si.com/college/purdue/.rss/full/",
    "https://www.on3.com/teams/purdue-boilermakers/news/feed/",
    "https://www.247sports.com/college/purdue/Article/feed.rss",
]
REFRESH_SECONDS = 300

app = Flask(__name__, static_folder="static", static_url_path="/static")

ARTICLES = []
LAST_REFRESH = None
LOCK = threading.Lock()

FALLBACK_ARTICLES = [
    {
        "title": "Welcome to Purdue MBB News",
        "link": "https://purdue.edu",
        "summary": "If you’re seeing this, feeds are still loading. The UI is working.",
        "published": datetime.now(timezone.utc).isoformat(),
        "source": "purdue.edu",
    },
    {
        "title": "Tip: Use the search box",
        "link": "https://onrender.com",
        "summary": "Type ‘Purdue’ or ‘ESPN’ to filter results once feeds load.",
        "published": datetime.now(timezone.utc).isoformat(),
        "source": "system",
    },
]

def _host(link):
    try:
        h = urlparse(link).netloc
        return h.replace("www.", "")
    except Exception:
        return ""

def _norm(e):
    title = e.get("title") or "(untitled)"
    link = e.get("link") or ""
    summary = (e.get("summary") or e.get("description") or "").strip()
    ts = None
    if getattr(e, "published_parsed", None):
        ts = datetime(*e.published_parsed[:6], tzinfo=timezone.utc).isoformat()
    elif getattr(e, "updated_parsed", None):
        ts = datetime(*e.updated_parsed[:6], tzinfo=timezone.utc).isoformat()
    return {
        "title": title,
        "link": link,
        "summary": summary,
        "published": ts or "",
        "source": _host(link),
    }

def refresh_feeds():
    global ARTICLES, LAST_REFRESH
    items = []
    for url in FEEDS:
        try:
            d = feedparser.parse(url)
            for e in d.entries[:40]:
                items.append(_norm(e))
        except Exception as ex:
            print("Feed error:", url, ex)
    # de-dup by (title, source)
    seen = set()
    unique = []
    for a in items:
        key = (a["title"].strip().lower(), a["source"])
        if key in seen: 
            continue
        seen.add(key)
        unique.append(a)
    unique.sort(key=lambda a: a["published"] or "", reverse=True)
    with LOCK:
        ARTICLES = unique[:250]
        LAST_REFRESH = datetime.now(timezone.utc).isoformat()

def refresher():
    while True:
        refresh_feeds()
        time.sleep(REFRESH_SECONDS)

threading.Thread(target=refresher, daemon=True).start()

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
        if not q:
            res = list(base)
        else:
            res = [a for a in base if q in a["title"].lower() or q in a["summary"].lower() or q in a["source"].lower()]
    return jsonify({"articles": res})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
