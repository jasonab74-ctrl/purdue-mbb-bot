import os
import time
from functools import lru_cache
from flask import Flask, render_template, redirect, url_for
import feedparser

# --- Config ------------------------------------------------------------------

DEFAULT_FEED_URL = os.getenv(
    "FEED_URL",
    "https://news.google.com/rss/search?q=Purdue%20Basketball&hl=en-US&gl=US&ceid=US:en",
)

DEFAULT_BG_IMAGE = os.getenv(
    "BG_IMAGE_URL",
    # Neutral hoops background; set BG_IMAGE_URL in Railway to override.
    "https://images.unsplash.com/photo-1517649763962-0c623066013b?q=80&w=2400&auto=format&fit=crop"
)

CACHE_SECONDS = int(os.getenv("FEED_CACHE_SECONDS", "900"))  # 15 minutes


# --- App Factory --------------------------------------------------------------

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

    # Optional convenience redirect if someone hits /health
    @app.get("/health")
    def health_redirect():
        return redirect(url_for("healthz"), code=302)

    return app


# --- Feed helper with simple caching -----------------------------------------

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
        # Fail gracefully—return whatever we had (maybe empty)
        return _last["items"]

# So Gunicorn can also import as `server:app` if needed
app = create_app()
