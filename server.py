#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import threading
import time
from datetime import datetime, timezone

from flask import Flask, render_template, send_file, jsonify, request, abort

# Our existing modules
from feeds import FEEDS, STATIC_LINKS
import collect as collector  # has collect.collect() that writes items.json

APP_DIR = os.path.dirname(os.path.abspath(__file__))
ITEMS_PATH = os.environ.get("ITEMS_PATH", os.path.join(APP_DIR, "items.json"))
COLLECT_TOKEN = os.environ.get("COLLECT_TOKEN", "")  # set this in Railway
ENABLE_AUTO_COLLECT = os.environ.get("ENABLE_AUTO_COLLECT", "1") == "1"
COLLECT_EVERY_SECONDS = int(os.environ.get("COLLECT_EVERY_SECONDS", "1800"))

app = Flask(__name__, static_folder="static", template_folder="templates")

def _load_items():
    if not os.path.exists(ITEMS_PATH):
        return {"items": [], "meta": {"generated_at": None}}
    try:
        with open(ITEMS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"items": [], "meta": {"generated_at": None}}

def _ensure_first_build():
    """Build items.json once on boot if missing, without killing the app if it fails."""
    if not os.path.exists(ITEMS_PATH):
        try:
            count = collector.collect()
            print(f"[boot] collected {count} items", flush=True)
        except Exception as e:
            print(f"[boot] collect failed: {e}", flush=True)

def _auto_collect_loop():
    """Background refresher."""
    while True:
        try:
            count = collector.collect()
            ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
            print(f"[auto] collected {count} items @ {ts}", flush=True)
        except Exception as e:
            print(f"[auto] collect failed: {e}", flush=True)
        time.sleep(COLLECT_EVERY_SECONDS)

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
    if not os.path.exists(ITEMS_PATH):
        # Return an empty-but-valid JSON so the UI doesn't break
        return jsonify({"items": [], "meta": {"generated_at": None}})
    return send_file(ITEMS_PATH, mimetype="application/json", conditional=True)

@app.route("/collect")
def run_collect():
    """
    Safe, token-protected trigger for the fetcher.
    Call with /collect?token=SECRET  (COLLECT_TOKEN env var)
    """
    token = request.args.get("token", "")
    if not COLLECT_TOKEN or token != COLLECT_TOKEN:
        abort(404)

    try:
        count = collector.collect()
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        return jsonify({"ok": True, "count": count, "ts": ts})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/healthz")
def healthz():
    return jsonify({"ok": True})

# ---- App boot hooks ----
_ensure_first_build()
if ENABLE_AUTO_COLLECT:
    t = threading.Thread(target=_auto_collect_loop, daemon=True)
    t.start()

if __name__ == "__main__":
    # Local dev runner
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=True)
