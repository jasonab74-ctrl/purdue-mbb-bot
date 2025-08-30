#!/usr/bin/env python3
import os, json
from flask import Flask, render_template, make_response, jsonify
from feeds import FEEDS, STATIC_LINKS

ITEMS_PATH = os.environ.get("ITEMS_PATH", "items.json")

app = Flask(__name__, static_folder="static", template_folder="templates")

def read_items():
    try:
        with open(ITEMS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"items": [], "meta": {"generated_at": "", "last_run": {"ts": ""}}}

@app.route("/")
def home():
    data = read_items()
    # Pass FEEDS to repopulate the Source dropdown
    return render_template(
        "index.html",
        items=data.get("items", []),
        meta=data.get("meta", {}),
        feeds=FEEDS,
        static_links=STATIC_LINKS,
    )

@app.route("/items.json")
def items_json():
    if not os.path.exists(ITEMS_PATH):
        return jsonify({"items": [], "meta": {}})
    with open(ITEMS_PATH, "r", encoding="utf-8") as f:
        payload = f.read()
    resp = make_response(payload)
    resp.headers["Content-Type"] = "application/json; charset=utf-8"
    # Prevent stale client cache so the 5-min poll always sees fresh data
    resp.headers["Cache-Control"] = "no-store, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    # Cheap ETag based on mtime
    try:
        resp.headers["ETag"] = str(os.path.getmtime(ITEMS_PATH))
    except Exception:
        pass
    return resp

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
