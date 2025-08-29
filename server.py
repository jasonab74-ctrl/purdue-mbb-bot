import os
import time
from flask import Flask, render_template, redirect, url_for
import feedparser

DEFAULT_FEED_URL = os.getenv(
    "FEED_URL",
    "https://news.google.com/rss/search?q=Purdue%20Basketball&hl=en-US&gl=US&ceid=US:en",
)

# No default photo to avoid wrong imagery. Set BG_IMAGE_URL in Railway if desired.
DEFAULT_BG_IMAGE = os.getenv("BG_IMAGE_URL", "")

CACHE_SECONDS = int(os.getenv("FEED_CACHE_SECONDS", "900"))

def create_app():
    app = Flask(__name__)

    @app.context_processor
    def inject_globals():
        return {
            "nav": [
                ("Home", url_for("home")),
                ("News", url_for("news")),
                ("Health", url_for("healthz")),
            ],
            "year": time.gmtime().tm_year,
            "bg_image_url": DEFAULT_BG_IMAGE,
        }

    @app.get("/")
    def home():
        return render_template("index.html")

    @app.get("/news")
    def news():
        items = get_news_items()
        return render_template("news.html", items=items)

    @app.get("/healthz")
    def healthz():
        return "ok", 200, {"Content-Type": "text/plain; charset=utf-8"}

    @app.get("/health")
    def health_redirect():
        return redirect(url_for("healthz"), code=302)

    return app

_last = {"ts": 0, "items": []}

def get_news_items():
    now = time.time()
    if now - _last["ts"] < CACHE_SECONDS and _last["items"]:
        return _last["items"]
    try:
        feed = feedparser.parse(DEFAULT_FEED_URL)
        items = []
        for e in feed.entries[:20]:
            items.append({
                "title": getattr(e, "title", "Untitled"),
                "link": getattr(e, "link", "#"),
                "published": getattr(e, "published", ""),
                "source": getattr(getattr(e, "source", {}), "title", ""),
            })
        _last["ts"] = now
        _last["items"] = items
        return items
    except Exception:
        return _last["items"]

app = create_app()
