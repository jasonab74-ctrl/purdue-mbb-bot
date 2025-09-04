#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
from datetime import datetime, timezone
from flask import Flask, render_template, send_file, jsonify, request, abort

from feeds import STATIC_LINKS, FEEDS
import collect as collector  # use collector.collect() to rebuild items.json

APP_DIR = os.path.dirname(__file__)
ITEMS_PATH = os.path.join(APP_DIR, "items.json")

app = Flask(__name__)

def _read_items():
    if not os.path.exists(ITEMS_PATH):
        return {"updated": None, "count": 0, "items": []}
    try:
        with open(ITEMS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Hard cap at 50 here too, just in case
        data["items"] = (data.get("items") or [])[:50]
        data["count"] = len(data["items"])
        return data
    except Exception:
        return {"updated": None, "count": 0, "items": []}

@app.route("/")
def index():
    data = _read_items()
    updated = data.get("updated")
    updated_human = None
    if updated:
        try:
            dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
            updated_human = dt.astimezone(timezone.utc).strftime("%b %-d • %I:%M %p UTC")
        except Exception:
            updated_human = updated
    return render_template("index.html",
                           items=data.get("items", []),
                           updated=updated_human,
                           sources=[f if isinstance(f, dict) else {"name": f[0], "url": f[1]} for f in FEEDS],
                           static_links=STATIC_LINKS)

@app.route("/items.json")
def items_json():
    return jsonify(_read_items())

# Open endpoint to rebuild now (no auth; you're on hobby tier)
@app.route("/collect-open", methods=["POST", "GET"])
def collect_open():
    try:
        items = collector.collect()
        collector.write_items(items, ITEMS_PATH)
        return jsonify({"ok": True, "wrote": len(items)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/health")
def health():
    ok = os.path.exists(ITEMS_PATH)
    return jsonify({"ok": ok, "items_path": ITEMS_PATH})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
