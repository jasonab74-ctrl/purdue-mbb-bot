import os
from flask import Flask, render_template, abort
import feedparser

app = Flask(__name__)

# Default to ESPN Purdue Men's Basketball RSS
DEFAULT_FEED = "https://www.espn.com/espn/rss/ncb/team?teamId=2509"
FEED_URL = os.getenv("FEED_URL", DEFAULT_FEED)

@app.get("/")
def home():
    return render_template("index.html")

@app.get("/healthz")
def healthz():
    return "ok", 200

@app.get("/news")
def news():
    try:
        feed = feedparser.parse(FEED_URL)
        items = []
        for e in (feed.entries or [])[:12]:
            items.append({
                "title": getattr(e, "title", "Untitled"),
                "url": getattr(e, "link", "#"),
                "published": getattr(e, "published", ""),
                "summary": getattr(e, "summary", ""),
            })
        return render_template("news.html", items=items, source=feed.feed.get("title", "Latest News"))
    except Exception as exc:
        # Keep the page up even if feed fails
        return render_template("news.html", items=[], error=str(exc), source="Latest News")
