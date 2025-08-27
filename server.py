# server.py
import os
import json
import datetime
import subprocess
from typing import Any, Dict, List, Tuple

from flask import (
    Flask,
    jsonify,
    render_template,
    request,
    send_from_directory,
    redirect,
    url_for,
    make_response,
)

# ────────────────────────────────────────────────────────────────────────────────
# Flask: templates at repo root (.) and static assets in ./static
# ────────────────────────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder="static", template_folder=".")

# Refresh key (kept backward-compatible with what you've been using)
REFRESH_KEY = os.getenv("MBB_REFRESH_KEY", "mbb_refresh_6P7wP9dXr2Jq")


# ────────────────────────────────────────────────────────────────────────────────
# Helpers to load cached data written by collect.py
# ────────────────────────────────────────────────────────────────────────────────
def _first_existing(paths: List[str]) -> str | None:
    for p in paths:
        if os.path.isfile(p):
            return p
    return None


def _read_json_from(paths: List[str]) -> Any:
    """
    Tries several likely file locations. Returns parsed JSON or sensible default.
    """
    found = _first_existing(paths)
    if not found:
        return None
    try:
        with open(found, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def load_items() -> List[Dict[str, Any]]:
    """
    Returns the list of news items produced by collect.py.
    We try multiple common filenames/locations to be robust.
    """
    candidates = [
        "items.json",
        "news.json",
        "data/items.json",
        "data/news.json",
        "cache/items.json",
        "app/items.json",
        "app/data/items.json",
    ]
    data = _read_json_from(candidates)
    if isinstance(data, dict) and "items" in data and isinstance(data["items"], list):
        return data["items"]
    if isinstance(data, list):
        return data
    return []


def load_last_modified() -> str:
    """
    Returns the last-modified string written by collect.py,
    or a best-effort fallback.
    """
    candidates = [
        "last-mod.json",
        "data/last-mod.json",
        "app/last-mod.json",
        "app/data/last-mod.json",
    ]
    obj = _read_json_from(candidates)
    if isinstance(obj, dict) and "modified" in obj:
        return str(obj["modified"])

    # Fallback: try to infer from item timestamps or file mtimes
    items = load_items()
    for key in ("updated", "pubDate", "published", "date"):
        try:
            # Find the max timestamp-like field if present
            vals = [
                i.get(key)
                for i in items
                if isinstance(i, dict) and isinstance(i.get(key), str)
            ]
            if vals:
                return sorted(vals, reverse=True)[0]
        except Exception:
            pass

    # Last resort: mtime of any items.json we can find
    for path in [
        "items.json",
        "news.json",
        "data/items.json",
        "data/news.json",
    ]:
        if os.path.isfile(path):
            ts = datetime.datetime.utcfromtimestamp(os.path.getmtime(path))
            return ts.strftime("%Y-%m-%d %H:%M:%S")

    # Nothing found
    return "never"


# ────────────────────────────────────────────────────────────────────────────────
# Routes
# ────────────────────────────────────────────────────────────────────────────────
@app.after_request
def add_no_cache_headers(resp):
    """
    Keep pages fresh while allowing static files to be cached by the browser.
    """
    if request.path in ("/", "/api/items", "/api/last-mod"):
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
    return resp


@app.route("/", methods=["GET", "HEAD"])
def index():
    # Render index.html that lives in the repo root (template_folder=".")
    return render_template("index.html", modified=load_last_modified())


@app.route("/api/items")
def api_items():
    return jsonify(load_items())


@app.route("/api/last-mod")
def api_last_mod():
    return jsonify({"modified": load_last_modified()})


@app.route("/api/refresh-now", methods=["POST"])
def api_refresh_now():
    """
    Triggers a background refresh by running collect.py.
    Guarded by the known key (?key=...).
    """
    key = request.args.get("key", "")
    if key != REFRESH_KEY:
        return jsonify({"ok": False, "error": "forbidden"}), 403

    # Fire and forget; Render’s logs will show collect.py output.
    try:
        subprocess.Popen(
            ["python", "collect.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/fight.mp3")
def fight_root_redirect():
    """
    Convenience route so /fight.mp3 works in addition to /static/fight.mp3
    """
    static_dir = os.path.join(app.root_path, "static")
    return send_from_directory(static_dir, "fight.mp3")


@app.route("/favicon.ico")
def favicon():
    # Serve your logo as favicon if you want
    static_dir = os.path.join(app.root_path, "static")
    logo_name = "logo.png"
    if os.path.isfile(os.path.join(static_dir, "favicon.ico")):
        return send_from_directory(static_dir, "favicon.ico")
    return send_from_directory(static_dir, logo_name)


@app.route("/ping")
def ping():
    return jsonify({"ok": True, "time": datetime.datetime.utcnow().isoformat()})


# ────────────────────────────────────────────────────────────────────────────────
# Entrypoint (for local runs). Render uses gunicorn via the start command.
# ────────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Local dev convenience
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True, threaded=True)
