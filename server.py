from flask import Flask, render_template, jsonify, abort
from jinja2 import TemplateNotFound
import json, os
from json import JSONDecodeError

app = Flask(__name__, template_folder="templates", static_folder="static")
ITEMS_PATH = os.environ.get("ITEMS_PATH", "items.json")

# Try to import STATIC_LINKS for the buttons row; fall back to [] if not present.
try:
    from feeds import STATIC_LINKS
except Exception:
    STATIC_LINKS = []

def read_items():
    """
    Never crash the server if items.json is missing or malformed.
    """
    try:
        with open(ITEMS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("items", []), data.get("meta", {})
    except (FileNotFoundError, JSONDecodeError, OSError):
        return [], {"generated_at": "", "items_count": 0}

@app.route("/healthz")
def healthz():
    return "ok", 200

@app.route("/api/items")
def api_items():
    items, meta = read_items()
    return jsonify({"items": items, "meta": meta})

@app.route("/")
def index():
    items, meta = read_items()
    try:
        return render_template("index.html",
                               items=items, meta=meta, static_links=STATIC_LINKS)
    except TemplateNotFound:
        # Minimal fallback page so we never 500
        return (
            "<!doctype html><meta charset='utf-8'>"
            "<h1>Feed</h1>"
            f"<p>Items: {len(items)}</p>"
            "<p>JSON: <a href='/api/items'>/api/items</a></p>",
            200,
            {"Content-Type": "text/html; charset=utf-8"},
        )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
