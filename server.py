import os
import time
from flask import Flask, render_template
import feedparser

FEED_URL = os.getenv(
    "FEED_URL",
    # Purdue MBB headlines RSS; safe default if you don't set FEED_URL
    "https://purduesports.com/rss/headlines.aspx?path=mbball",
)
CACHE_TTL = int(os.getenv("CACHE_TTL", "900"))  # 15 minutes


def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")

    cache = {"ts": 0, "items": []}

    def get_feed_items():
        nonlocal cache
        now = time.time()
        if cache["items"] and (now - cache["ts"] < CACHE_TTL):
            return cache["items"]

        parsed = feedparser.parse(FEED_URL)
        items = []
        for e in parsed.entries[:20]:
            items.append(
                {
                    "title": e.get("title", "Untitled"),
                    "link": e.get("link") or "#",
                    "published": e.get("published", ""),
                    "summary": e.get("summary", ""),
                }
            )
        cache = {"ts": now, "items": items}
        return items

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/news")
    def news():
        error = None
        items = []
        try:
            items = get_feed_items()
            if not items:
                error = "No items found from the feed yet."
        except Exception as exc:
            error = f"Error loading feed: {exc}"
        return render_template("news.html", items=items, error=error, feed_url=FEED_URL)

    @app.get("/healthz")
    def healthz():
        return "ok", 200, {"Content-Type": "text/plain; charset=utf-8"}

    return app


# Expose a module-level WSGI app so Gunicorn can load `server:app`
app = create_app()
