# server.py
# Flask app for Purdue MBB feed (safe, game-day pill support)

import os
import json
from datetime import datetime
from flask import Flask, render_template, send_from_directory, jsonify

# ---- config / paths
APP_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(APP_DIR, "static")
ITEMS_PATH = os.environ.get("ITEMS_PATH", os.path.join(APP_DIR, "items.json"))

# ---- imports from your feeds.py
from feeds import FEEDS, STATIC_LINKS

app = Flask(__name__, static_folder="static", template_folder="templates")


# ---------- helpers

def load_items_payload():
    """
    Load items.json once per request. If missing/corrupt, return empty structure.
    """
    try:
        with open(ITEMS_PATH, "r", encoding="utf-8") as f:
            payload = json.load(f)
            # normalize minimal structure
            if "items" not in payload:
                payload["items"] = []
            if "meta" not in payload:
                payload["meta"] = {"generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z"}
            return payload
    except Exception:
        # fallback empty payload
        return {
            "items": [],
            "meta": {"generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z"}
        }


def build_links_with_gameday(meta):
    """
    Start with STATIC_LINKS, and if collect.py marked a Game Day,
    prepend the special DraftKings pill.
    """
    links = list(STATIC_LINKS)  # copy so we never mutate the import

    gd = (meta or {}).get("gameday")
    if gd and gd.get("active") and gd.get("label") and gd.get("url"):
        # put the Game Day pill FIRST
        links.insert(0, {"label": gd["label"], "url": gd["url"]})

    return links


# ---------- routes

@app.route("/")
def index():
    payload = load_items_payload()
    items = payload.get("items", [])
    meta = payload.get("meta", {})
    updated = meta.get("generated_at")

    # Build quick links (with optional Game Day pill)
    links = build_links_with_gameday(meta)

    return render_template(
        "index.html",
        items=items,
        feeds=FEEDS,
        static_links=links,
        meta=meta,
        updated=updated,
        now=datetime.utcnow(),
    )


@app.route("/items.json")
def items_json():
    """
    Serve the current items.json so the client can auto-check for updates.
    """
    try:
        with open(ITEMS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return jsonify(data)
    except Exception:
        return jsonify({"items": [], "meta": {"error": "items.json not available"}}), 200


# ---- root-level icon routes for Safari / iOS quirks (non-breaking)

@app.route("/apple-touch-icon.png")
def apple_touch_icon():
    # If you’ve put apple-touch-icon.png in /static, this serves it at the root path
    return send_from_directory(STATIC_DIR, "apple-touch-icon.png")


@app.route("/favicon.ico")
def favicon_ico():
    """
    Serve a favicon at the root level. If you only have PNGs, this falls back to 32x32.
    """
    ico_path = os.path.join(STATIC_DIR, "favicon.ico")
    if os.path.exists(ico_path):
        return send_from_directory(STATIC_DIR, "favicon.ico")
    return send_from_directory(STATIC_DIR, "favicon-32x32.png")


# (Optional) serve a manifest if you add one later
@app.route("/site.webmanifest")
def site_webmanifest():
    path = os.path.join(STATIC_DIR, "site.webmanifest")
    if os.path.exists(path):
        return send_from_directory(STATIC_DIR, "site.webmanifest")
    # gentle fallback
    return jsonify({"name": "Purdue MBB Feed", "icons": []})


# (Optional) simple health route
@app.route("/health")
def health():
    return jsonify({"ok": True, "ts": datetime.utcnow().isoformat(timespec="seconds") + "Z"})


# ---------- run (for local dev only)
if __name__ == "__main__":
    # Local dev: python3 server.py
    # Prod: use gunicorn -w 4 -b 0.0.0.0:$PORT server:app
    app.run(host="127.0.0.1", port=5000, debug=False)
