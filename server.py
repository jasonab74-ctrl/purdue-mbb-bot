import os
from flask import Flask, render_template

def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def home():
        return render_template("index.html")

    @app.get("/healthz")
    def healthz():
        # Plain-text healthcheck for Railway
        return "ok", 200, {"Content-Type": "text/plain; charset=utf-8"}

    @app.get("/news")
    def news():
        # Soft-dependency fetch of RSS (won't crash if feed is down)
        try:
            import feedparser
            FEED_URL = os.getenv(
                "FEED_URL",
                "https://purduesports.com/rss.aspx?path=mbball"
            )
            d = feedparser.parse(FEED_URL)

            items = []
            for e in d.entries[:15]:
                items.append(
                    {
                        "title": e.get("title", "(no title)"),
                        "link": e.get("link", "#"),
                        "published": e.get("published", ""),
                        "summary": e.get("summary", ""),
                    }
                )
        except Exception as ex:
            # Fail-soft: render page with a friendly message
            FEED_URL = None
            items = []
            print(f"[warn] RSS fetch failed: {ex}")

        return render_template("news.html", items=items, feed_url=FEED_URL)

    return app

# Optional local run: `python server.py`
if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    app = create_app()
    app.run(host="0.0.0.0", port=port)
