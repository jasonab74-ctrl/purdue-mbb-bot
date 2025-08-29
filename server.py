# server.py
import os
import json
from typing import List, Dict, Any

from flask import Flask, render_template, send_from_directory, abort, make_response

APP_ROOT = os.path.dirname(os.path.abspath(__file__))

# Create app
app = Flask(
    __name__,
    static_folder="static",
    template_folder="templates",
)

# Candidate locations for the aggregated feed JSON
ITEMS_CANDIDATES = [
    os.path.join(APP_ROOT, "items.json"),
    os.path.join(APP_ROOT, "data", "items.json"),
    os.path.join(APP_ROOT, "static", "items.json"),
]


def _read_items() -> List[Dict[str, Any]]:
    """
    Read aggregated items from whichever path exists.
    Accepts either:
      - a list of items, or
      - an object with 'items' (list) inside.
    Returns [] if nothing loads.
    """
    for fp in ITEMS_CANDIDATES:
        try:
            if os.path.exists(fp):
                with open(fp, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                if isinstance(raw, list):
                    return raw
                if isinstance(raw, dict):
                    if isinstance(raw.get("items"), list):
                        return raw["items"]
                    # Some collectors may use 'results'
                    if isinstance(raw.get("results"), list):
                        return raw["results"]
        except Exception:
            # If a file is corrupt, try the next candidate
            continue
    return []


@app.route("/")
def index():
    """
    Server-side render: pass whatever we can load into the template as `items`.
    Your template may also have a client-side fallback that fetches /items.json.
    """
    items = _read_items()
    # Do not mutate or enforce a shape—your template logic decides what to show.
    return render_template("index.html", items=items)


@app.route("/items.json")
def items_json():
    """
    Serve items.json from whichever path exists so the client can fetch it.
    This avoids hard-coding where the collector writes it.
    """
    for fp in ITEMS_CANDIDATES:
        if os.path.exists(fp):
            directory = os.path.dirname(fp) if os.path.dirname(fp) else APP_ROOT
            filename = os.path.basename(fp)
            # Use send_from_directory to preserve correct content-type & caching
            return send_from_directory(directory, filename, max_age=0)
    abort(404)


@app.route("/healthz")
def healthz():
    # Simple health endpoint for Railway
    return make_response("ok", 200)


# Optional: keep a static passthrough (Flask already serves from static_folder)
@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(os.path.join(APP_ROOT, "static"), filename, max_age=0)


if __name__ == "__main__":
    # Local run: respects $PORT if set; defaults to 8080 to match Railway logs
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port, debug=False)
