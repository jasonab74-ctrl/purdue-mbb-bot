#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, json
from datetime import datetime, timezone
from flask import Flask, render_template, send_file, send_from_directory, jsonify

APP_DIR = os.path.dirname(os.path.abspath(__file__))
ITEMS_PATH = os.environ.get("ITEMS_PATH", os.path.join(APP_DIR, "items.json"))

# Project modules
from feeds import FEEDS, STATIC_LINKS

app = Flask(__name__, static_folder="static", template_folder="templates")

def _now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def load_feed():
    """Load items.json in the most permissive way possible."""
    items = []
    meta = {"generated_at": _now_iso()}
    if not os.path.exists(ITEMS_PATH):
        return items, meta

    try:
        with open(ITEMS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        # If it’s corrupt or mid-write, just show empty rather than crashing
        return items, meta

    # Accept either {"items":[...], "meta":{...}} or a bare list
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        items = data.get("items", [])
        meta = data.get("meta", meta)
        # Normalize a few common keys so your template lines always render
        if "updated" in data and "generated_at" not in meta:
            meta["generated_at"] = data.get("updated")
        if "last_run" in data and isinstance(data["last_run"], dict) and "ts" in data["last_run"]:
            meta.setdefault("generated_at", data["last_run"]["ts"])
    return items, meta

@app.route("/")
def index():
    items, meta = load_feed()
    return render_template(
        "index.html",
        items=items,
        feeds=FEEDS,
        static_links=STATIC_LINKS,
        meta=meta,
    )

@app.route("/items.json")
def items_json():
    # Pass-through so your client-side refresh keeps working
    if not os.path.exists(ITEMS_PATH):
        return jsonify({"items": [], "meta": {"generated_at": _now_iso(), "note": "items.json not found"}}), 200
    return send_file(ITEMS_PATH, mimetype="application/json")

# ---- Favicon + iOS icon at ROOT (for Safari Favorites/Home Screen) ----
@app.route("/favicon.ico")
def favicon():
    return send_from_directory("static", "favicon.ico", mimetype="image/x-icon")

@app.route("/apple-touch-icon.png")
def apple_touch_icon():
    return send_from_directory("static", "apple-touch-icon.png", mimetype="image/png")

# Simple health endpoint (optional)
@app.route("/health")
def health():
    return jsonify({"ok": True, "ts": _now_iso()})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
