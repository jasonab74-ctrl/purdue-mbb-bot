# server.py
import os
import json
import datetime
import subprocess
from typing import Any, Dict, List, Optional

from flask import (
    Flask,
    jsonify,
    request,
    send_from_directory,
    make_response,
)

# Flask app (no templates needed for /)
app = Flask(__name__, static_folder="static")

# Keep the same refresh key you’ve been using
REFRESH_KEY = os.getenv("MBB_REFRESH_KEY", "mbb_refresh_6P7wP9dXr2Jq")

# ----------------------------- file helpers ---------------------------------- #

def _first_existing(paths: List[str]) -> Optional[str]:
    for p in paths:
        if os.path.isfile(p):
            return p
    return None

def _read_json(paths: List[str]):
    p = _first_existing(paths)
    if not p:
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def load_items() -> List[Dict[str, Any]]:
    candidates = [
        "items.json",
        "news.json",
        os.path.join("data", "items.json"),
        os.path.join("data", "news.json"),
        os.path.join("cache", "items.json"),
        os.path.join("app", "items.json"),
        os.path.join("app", "data", "items.json"),
    ]
    data = _read_json(candidates)
    if isinstance(data, dict) and isinstance(data.get("items"), list):
        return data["items"]
    if isinstance(data, list):
        return data
    return []

def load_last_modified() -> str:
    candidates = [
        "last-mod.json",
        os.path.join("data", "last-mod.json"),
        os.path.join("app", "last-mod.json"),
        os.path.join("app", "data", "last-mod.json"),
    ]
    obj = _read_json(candidates)
    if isinstance(obj, dict) and "modified" in obj:
        return str(obj["modified"])

    # fallback: newest timestamp-like field from items
    items = load_items()
    for key in ("updated", "pubDate", "published", "date"):
        try:
            vals = [
                i.get(key)
                for i in items
                if isinstance(i, dict) and isinstance(i.get(key), str)
            ]
            if vals:
                return sorted(vals, reverse=True)[0]
        except Exception:
            pass

    # last resort: mtime of common files
    for p in ["items.json", "news.json", os.path.join("data", "items.json")]:
        if os.path.isfile(p):
            ts = datetime.datetime.utcfromtimestamp(os.path.getmtime(p))
            return ts.strftime("%Y-%m-%d %H:%M:%S")

    return "never"

def _send_index_html():
    """
    Serve index.html WITHOUT Jinja. We try root, then static/, then app/.
    """
    root = app.root_path
    candidates = [
        os.path.join(root, "index.html"),
        os.path.join(root, "static", "index.html"),
        os.path.join(root, "app", "index.html"),
    ]
    for full in candidates:
        if os.path.isfile(full):
            directory, filename = os.path.split(full)
            # Send with no-cache to reflect latest “Updated:” quickly
            resp = make_response(send_from_directory(directory, filename))
            resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            resp.headers["Pragma"] = "no-cache"
            resp.headers["Expires"] = "0"
            return resp
    # If nothing found, give a helpful message
    return (
        "index.html not found. Place it at repo root (preferred), "
        "or static/index.html, or app/index.html.",
        500,
    )

# ------------------------------- routes -------------------------------------- #

@app.after_request
def no_cache_dynamic(resp):
    if request.path in ("/api/items", "/api/last-mod"):
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
    return resp

@app.route("/", methods=["GET", "HEAD"])
def home():
    return _send_index_html()

# If you visit /?v=sites keep same behavior
@app.route("/sites", methods=["GET", "HEAD"])
def sites_redirect():
    return _send_index_html()

@app.route("/api/items")
def api_items():
    return jsonify(load_items())

@app.route("/api/last-mod")
def api_last_mod():
    return jsonify({"modified": load_last_modified()})

@app.route("/api/refresh-now", methods=["POST"])
def api_refresh_now():
    key = request.args.get("key", "")
    if key != REFRESH_KEY:
        return jsonify({"ok": False, "error": "forbidden"}), 403
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

# convenience: /fight.mp3 -> static/fight.mp3
@app.route("/fight.mp3")
def fight_mp3():
    return send_from_directory(app.static_folder, "fight.mp3")

@app.route("/favicon.ico")
def favicon():
    # serve favicon.ico if present, else logo.png
    if os.path.isfile(os.path.join(app.static_folder, "favicon.ico")):
        return send_from_directory(app.static_folder, "favicon.ico")
    return send_from_directory(app.static_folder, "logo.png")

@app.route("/healthz")
def healthz():
    return jsonify({"ok": True, "time": datetime.datetime.utcnow().isoformat()})

# ---------------------------- local dev entry -------------------------------- #

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True, threaded=True)
