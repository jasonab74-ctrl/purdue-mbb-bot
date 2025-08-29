import os
import time
import datetime as dt
from typing import List, Dict

import feedparser
from flask import Flask, render_template, jsonify


DEFAULT_FEED_URL = os.environ.get(
    "FEED_URL",
    # ESPN Purdue Men's Basketball RSS
    "https://www.espn.com/espn/rss/ncb/team?teamId=2509",
)


def create_app() -> Flask:
    app = Flask(__name__, static_folder="static", template_folder="templates")

    # ---- Config (env-overridable) -----------------------------------------
    app.config["FEED_URL"] = os.environ.get("FEED_URL", DEFAULT_FEED_URL)
    app.config["FEED_CACHE_SECONDS"] = int(os.environ.get("FEED_CACHE_SECONDS", "900"))
    app.config["SITE_NAME"] = os.environ.get("SITE_NAME", "Purdue Basketball")
    app.config["BG_IMAGE_URL"] = os.environ.get("BG_IMAGE_URL", "").strip()
    # -----------------------------------------------------------------------

    _feed_cache: Dict[str, object] = {"items": [], "ts": 0.0}

    def _fetch_feed() -> List[Dict[str, str]]:
        """Fetch and cache RSS items."""
        now = time.time()
        if _feed_cache["items"] and (now - float(_feed_cache["ts"]) < app.config["FEED_CACHE_SECONDS"]):
            return _feed_cache["items"]  # type: ignore[return-value]

        items: List[Dict[str, str]] = []
        try:
            parsed = feedparser.parse(
                app.config["FEED_URL"],
                request_headers={"User-Agent": "railway-purdue-hoops/1.0 (+https://railway.app)"},
            )
            for e in parsed.entries[:25]:
                items.append(
                    {
                        "title": getattr(e, "title", "(untitled)"),
                        "link": getattr(e, "link", "#"),
                        "published": getattr(e, "published", getattr(e, "updated", "")),
                    }
                )
        except Exception:
            # On any fetch/parse error, keep items empty; UI will handle gracefully.
            items = []

        _feed_cache["items"] = items
        _feed_cache["ts"] = now
        return items

    # ----------------------------- Routes ----------------------------------

    @app.get("/")
    def home():
        return render_template(
            "index.html",
            site_name=app.config["SITE_NAME"],
            bg_image_url=app.config["BG_IMAGE_URL"],
            year=dt.date.today().year,
        )

    @app.get("/news")
    def news():
        items = _fetch_feed()
        return render_template(
            "news.html",
            site_name=app.config["SITE_NAME"],
            items=items,
            bg_image_url=app.config["BG_IMAGE_URL"],
            year=dt.date.today().year,
        )

    @app.get("/api/news.json")
    def news_json():
        return jsonify({"items": _fetch_feed()})

    @app.get("/healthz")
    def healthz():
        return ("ok", 200, {"Content-Type": "text/plain; charset=utf-8"})

    return app


# For Gunicorn: server:app
app = create_app()
