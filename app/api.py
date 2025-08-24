# app/api.py
import os
import time
import threading
from datetime import datetime, timezone
from urllib.parse import urlparse

from flask import Flask, jsonify, request, send_from_directory, redirect
import feedparser

# ---------- Config ----------
FEEDS = [
    # National / CBB
    "https://www.espn.com/espn/rss/ncb/news",
    "https://feeds.cbssports.com/rss/headlines/ncaab",
    "https://www.ncaa.com/news/basketball-men/rss.xml",
    # Purdue-focused
    "https://www.si.com/college/purdue/.rss/full/",
    "https://www.on3.com/teams/purdue-boilermakers/news/feed/",
    "https://www.247sports.com/college/purdue/Article/feed.rss",
    "https://www.jconline.com/search/?f=rss&t=article&c=news%2Fsports%2Fpurdue-boilers*&l=50&s=start_time&sd=desc",
    # Add more as you like
]
REFRESH_SECONDS = 300  # 5 minutes

# ---------- App ----------
app = Flask(__name__, static_folder="static", static_url_path="/static")

ARTICLES = []        # in-memory store of normalized articles
LAST_REFRESH = None  # timestamp of last successful refresh
LOCK = threading.Lock()

def _norm_source(link):
    try:
        host = urlparse(link).netloc
        return host.replace("www.", "")
    except Exception:
        return ""

def _normalize(entry):
    title = entry.get("title") or "(untitled)"
    link = entry.get("link") or ""
    summary = (entry.get("summary") or entry.get("description") or "").strip()
    published = ""
    if entry.get("published_parsed"):
        dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
        published = dt.isoformat()
    elif entry.get("updated_parsed"):
        dt = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
        published = dt.isoformat()
    source = _norm_source(link)
    return {
        "title": title,
        "link": link,
        "summary": summary,
        "published": published,
        "source": source,
    }

def refresh_feeds():
    global LAST_REFRESH, ARTICLES
    try:
        items = []
        for url in FEEDS:
            d = feedparser.parse(url)
            for e in d.entries[:50]:
                items.append(_normalize(e))
        # Simple de-dup by title+source
        seen = set()
        deduped = []
        for a in items:
            key = (a["title"].strip().lower(), a["source"])
            if key in seen:
                continue
            seen.add(key)
            deduped.append(a)

        # Sort newest first if we have timestamps
        def sort_key(a):
            return a["published"] or ""
        deduped.sort(key=sort_key, reverse=True)

        with LOCK:
            ARTICLES = deduped[:200]
            LAST_REFRESH = datetime.now(timezone.utc).isoformat()
    except Exception as exc:
        # Keep running even if one refresh fails
        print("Feed refresh error:", exc)

def _background_refresher():
    while True:
        refresh_feeds()
        time.sleep(REFRESH_SECONDS)

# Kick off background refresh on startup
threading.Thread(target=_background_refresher, daemon=True).start()

# ---------- Routes ----------
@app.route("/")
def root():
    # Redirect root to your UI
    return redirect("/ui/")

@app.route("/ui/")
def ui_index():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/api/health")
def health():
    with LOCK:
        count = len(ARTICLES)
        last = LAST_REFRESH
    return jsonify({"ok": True, "articles": count, "last_refresh": last})

@app.route("/api/articles")
def api_articles():
    with LOCK:
        data = list(ARTICLES)
    return jsonify({"articles": data})

@app.route("/api/search")
def api_search():
    q = (request.args.get("q") or "").strip().lower()
    with LOCK:
        if not q:
            results = list(ARTICLES)
        else:
            results = [
                a for a in ARTICLES
                if q in a["title"].lower()
                or q in a["summary"].lower()
                or q in a["source"].lower()
            ]
    return jsonify({"articles": results})

# Serve static files (logo, css, etc.) are handled by Flask static config

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)
