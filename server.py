# server.py
# Flask app for the Purdue MBB site with a safe YouTube thumbnail filter added.
# Drop-in: this keeps your existing render of index.html and data shape.
import os
import json
import urllib.parse as _up
from datetime import datetime
from flask import Flask, render_template, send_from_directory, abort

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(APP_ROOT, "data", "combined.json")

app = Flask(__name__, static_folder="static", template_folder="templates")


# ---- YouTube thumbnail helper (safe, additive) ----
def _yt_thumb(url: str):
    if not url:
        return None
    try:
        u = _up.urlparse(url)
        host = (u.netloc or "").lower()
        vid = None
        if "youtube.com" in host:
            qs = _up.parse_qs(u.query)
            vid = qs.get("v", [None])[0]
        elif "youtu.be" in host:
            vid = u.path.lstrip("/")
        if vid:
            return f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
    except Exception:
        pass
    return None

app.jinja_env.filters["yt_thumb"] = _yt_thumb
# ---------------------------------------------------


def _load_items():
    """Load your already-built merged feed results.
    Expected shape per item (keep whatever you already output):
      {
        "title": "...",
        "link": "https://...",
        "source": "Google News – Purdue Basketball",
        "published": "2025-08-29T08:00:00Z"  # or similar
        # Optional existing fields this update will use if present:
        # "image", "image_url", "media_image", "thumbnail"
      }
    """
    if not os.path.exists(DATA_PATH):
        return []
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            items = data if isinstance(data, list) else data.get("items", [])
            # Defensive: normalize a few fields that templates expect
            for it in items:
                if "published" in it and isinstance(it["published"], str):
                    it["_published_human"] = it["published"][:10]
            return items
    except Exception:
        return []


@app.route("/")
def index():
    items = _load_items()
    return render_template("index.html", items=items)


# Serve the fight song audio or other static assets if you keep them in /static
@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(os.path.join(APP_ROOT, "static"), filename)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=False)
