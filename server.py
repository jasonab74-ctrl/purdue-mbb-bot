#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
from flask import Flask, render_template, send_file, jsonify, request, abort
from datetime import datetime, timezone

# Our existing modules
from feeds import FEEDS, STATIC_LINKS
import collect as collector  # uses collect.collect() to rebuild items.json

APP_DIR = os.path.dirname(os.path.abspath(__file__))
ITEMS_PATH = os.environ.get("ITEMS_PATH", os.path.join(APP_DIR, "items.json"))
COLLECT_TOKEN = os.environ.get("COLLECT_TOKEN", "")  # set this in Railway

app = Flask(__name__, static_folder="static", template_folder="templates")

def _load_items():
    """
    Load items.json safely. If it doesn't exist yet, return empty structure.
    """
    if not os.path.exists(ITEMS_PATH):
        return {"items": [], "meta": {"generated_at": None}}
    try:
        with open(ITEMS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        # Never break the page if json is malformed; show empty list
        return {"items": [], "meta": {"generated_at": None}}

@app.route("/")
def index():
    data = _load_items()
    items = data.get("items", [])
    meta = data.get("meta", {})
    return render_template(
        "index.html",
        items=items,
        meta=meta,
        feeds=FEEDS,
        static_links=STATIC_LINKS
    )

@app.route("/items.json")
def items_json():
    # Serve the file directly for the client auto-refresh check
    return send_file(ITEMS_PATH, mimetype="application/json", conditional=True)

@app.route("/collect")
def run_collect():
    """
    Safe, token-protected trigger for the fetcher.
    - Use COLLECT_TOKEN env var.
    - Call with /collect?token=SECRET
    - Returns the new item count and timestamp.
    """
    token = request.args.get("token", "")
    if not COLLECT_TOKEN or token != COLLECT_TOKEN:
        # Hide whether token is configured; just 404 to keep it quiet.
        abort(404)

    try:
        count = collector.collect()  # writes items.json atomically
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        return jsonify({"ok": True, "count": count, "ts": ts})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# Optional: simple health endpoint for uptime checks
@app.route("/healthz")
def healthz():
    return jsonify({"ok": True})

if __name__ == "__main__":
    # Local dev
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=True)
