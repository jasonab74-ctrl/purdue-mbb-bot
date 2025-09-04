#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
from datetime import datetime, timezone
from flask import Flask, render_template, send_file, jsonify, request

APP_DIR = os.path.dirname(__file__)
ITEMS_PATH = os.path.join(APP_DIR, "items.json")

# Serve /static/* by default; templates/ for Jinja
app = Flask(__name__, static_folder="static", template_folder="templates")

# Import after app to avoid circulars
import collect as collector  # uses feeds.py and writes items.json
from feeds import STATIC_LINKS, FEEDS

def _read_items():
    """Read items.json safely; cap to 50."""
    if not os.path.exists(ITEMS_PATH):
        return {"updated": None, "count": 0, "items": []}
    try:
        with open(ITEMS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        items = (data.get("items") or [])[:50]
        return {"updated": data.get("updated"), "count": len(items), "items": items}
    except Exception:
        return {"updated": None, "count": 0, "items": []}

@app.route("/")
def index():
    data = _read_items()
    updated = data.get("updated")
    # Let template JS render friendly times
    sources = [s if isinstance(s, dict) else {"name": s[0], "url": s[1]} for s in FEEDS]
    return render_template(
        "index.html",
        items=data.get("items", []),
        updated=updated,
        sources=sources,
        static_links=STATIC_LINKS,
    )

@app.route("/items.json")
def items_json():
    return jsonify(_read_items())

# Open collector endpoint to repopulate items.json on demand
@app.route("/collect-open", methods=["POST", "GET"])
def collect_open():
    try:
        items = collector.collect()
        collector.write_items(items, ITEMS_PATH)
        return jsonify({"ok": True, "wrote": len(items)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# Simple health/debug endpoint so you can confirm both issues in seconds
@app.route("/health")
def health():
    static_audio = os.path.exists(os.path.join(app.static_folder, "fight-song.mp3"))
    items_data = _read_items()
    return jsonify({
        "ok": True,
        "items_count": items_data.get("count", 0),
        "items_json_exists": os.path.exists(ITEMS_PATH),
        "static_audio_exists": static_audio,
        "items_path": ITEMS_PATH,
        "static_folder": os.path.abspath(app.static_folder),
    })

# Optional: direct route to test audio delivery
@app.route("/test-fight-song")
def test_fight_song():
    path = os.path.join(app.static_folder, "fight-song.mp3")
    if not os.path.exists(path):
        return "fight-song.mp3 not found in /static", 404
    return send_file(path, mimetype="audio/mpeg")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
