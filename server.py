# server.py
import os, time, threading
from datetime import datetime, timezone
from urllib.parse import urlparse

from flask import Flask, jsonify, send_from_directory, request, redirect
import feedparser

# ---------- Feeds: Purdue-focused + NCAA men's basketball ----------
FEEDS = [
    # Purdue-focused outlets
    "https://www.si.com/college/purdue/.rss/full/",
    "https://www.on3.com/teams/purdue-boilermakers/news/feed/",
    "https://www.247sports.com/college/purdue/Article/feed.rss",
    "https://www.jconline.com/search/?f=rss&t=article&c=news%2Fsports%2Fpurdue-boilers*&l=50&s=start_time&sd=desc",

    # NCAA men's basketball for broader context (still filtered below)
    "https://www.ncaa.com/news/basketball-men/rss.xml",
    "https://www.espn.com/espn/rss/ncb/news",
    "https://feeds.cbssports.com/rss/headlines/ncaab",
]

REFRESH_SECONDS = 300  # background refresh every 5 min

app = Flask(__name__, static_folder="static", static_url_path="/static")

ARTICLES = []
LAST_REFRESH = None
LOCK = threading.Lock()

FALLBACK_ARTICLES = [
    {
        "title": "Purdue MBB feed warming up…",
        "link": "https://www.purduesports.com/",
        "summary": "If you see this, feeds are still loading or returned nothing new yet. Try Refresh.",
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

# ---------- Core refresh (Purdue-only filter) ----------
def refresh_feeds():
    global ARTICLES, LAST_REFRESH
    items = []
    for url in FEEDS:
        try:
            d = feedparser.parse(url)
            for e in d.entries[:50]:
                norm = _norm(e)
                text = (norm["title"] + " " + norm["summary"]).lower()
                # keep only Purdue men's hoops adjacent content
                if ("purdue" in text) or ("boilermaker" in text):
                    items.append(norm)
        except Exception a
