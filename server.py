import flask_before_first_compat  # <- keep this FIRST
from flask import Flask
# server.py
import os
import json
import shutil
from typing import List, Dict, Any
from flask import Flask, render_template, send_from_directory, abort, make_response, jsonify

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(APP_ROOT, "static")
TEMPLATES_DIR = os.path.join(APP_ROOT, "templates")

# Candidate locations for the aggregated feed JSON
ITEMS_CANDIDATES = [
    os.path.join(APP_ROOT, "items.json"),
    os.path.join(APP_ROOT, "data", "items.json"),
    os.path.join(STATIC_DIR, "items.json"),
]

app = Flask(__name__, static_folder="static", template_folder="templates")

@app.get("/healthz")
def healthz():
    return "ok", 200

def _first_existing(path_list) -> str | None:
    for p in path_list:
        if os.path.exists(p):
            return p
    return None


def _read_items() -> List[Dict[str, Any]]:
    """
    Read aggregated items from whichever path exists.
    Accepts either:
      - a list of items, or
      - an object with 'items' (list) or 'results' (list).
    Returns [] if nothing loads.
    """
    src = _first_existing(ITEMS_CANDIDATES)
    if not src:
        return []
    try:
        with open(src, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, list):
            return raw
        if isinstance(raw, dict):
            if isinstance(raw.get("items"), list):
                return raw["items"]
            if isinstance(raw.get("results"), list):
                return raw["results"]
    except Exception:
        pass
    return []


def _ensure_items_in_static() -> str | None:
    """
    Copy the first existing items file into /static/items.json
    so it's always fetchable at /items.json and /static/items.json.
    Returns the destination path if successful.
    """
    os.makedirs(STATIC_DIR, exist_ok=True)
    src = _first_existing(ITEMS_CANDIDATES)
    if not src:
        return None
    dst = os.path.join(STATIC_DIR, "items.json")
    try:
        # Only copy if src is newer or dst missing
        if (not os.path.exists(dst)) or (os.path.getmtime(src) > os.path.getmtime(dst)):
            shutil.copy2(src, dst)
        return dst
    except Exception:
        return None


@app.before_first_request
def _bootstrap_static_items():
    _ensure_items_in_static()


@app.route("/")
def index():
    # Keep SSR: pass items to the template (if file readable)
    items = _read_items()
    return render_template("index.html", items=items)


@app.route("/items.json")
def items_json():
    """
    Always serve /items.json from /static/items.json.
    If it isn't there yet, try to copy it in place first.
    """
    dst = os.path.join(STATIC_DIR, "items.json")
    if not os.path.exists(dst):
        _ensure_items_in_static()
    if os.path.exists(dst):
        return send_from_directory(STATIC_DIR, "items.json", max_age=0)
    abort(404)


@app.route("/healthz")
def healthz():
    return make_response("ok", 200)


@app.route("/debug/paths")
def debug_paths():
    """
    Quick visibility into where the app sees items.json.
    """
    found = []
    for p in ITEMS_CANDIDATES:
        found.append({
            "path": p,
            "exists": os.path.exists(p),
            "size": (os.path.getsize(p) if os.path.exists(p) else None)
        })
    dst = os.path.join(STATIC_DIR, "items.json")
    resp = {
        "app_root": APP_ROOT,
        "static_dir": STATIC_DIR,
        "templates_dir": TEMPLATES_DIR,
        "candidates": found,
        "static_items_exists": os.path.exists(dst),
        "static_items_size": (os.path.getsize(dst) if os.path.exists(dst) else None),
    }
    return jsonify(resp)


# Optional static passthrough (Flask already serves /static/*)
@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(STATIC_DIR, filename, max_age=0)


if __name__ == "__main__":
    # Respect $PORT (Railway sets this)
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port, debug=False)
