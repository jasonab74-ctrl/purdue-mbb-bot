#!/usr/bin/env python3
import os, json, csv, io
from datetime import datetime, timezone
from flask import Flask, render_template, make_response, jsonify, request
from feeds import FEEDS, STATIC_LINKS

ITEMS_PATH = os.environ.get("ITEMS_PATH", "items.json")

app = Flask(__name__, static_folder="static", template_folder="templates")

# ---------- helpers ----------
def read_items():
    try:
        with open(ITEMS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"items": [], "meta": {"generated_at": "", "last_run": {"ts": ""}}}

def parse_yyyy_mm_dd(s, default_ts=None):
    if not s:
        return default_ts
    try:
        dt = datetime.fromisoformat(s.strip())  # expects YYYY-MM-DD
        if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except Exception:
        return default_ts

def nocache(resp):
    resp.headers["Cache-Control"] = "no-store, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    try:
        resp.headers["ETag"] = str(os.path.getmtime(ITEMS_PATH))
    except Exception:
        pass
    return resp

# ---------- pages ----------
@app.route("/")
def home():
    data = read_items()
    return render_template(
        "index.html",
        items=data.get("items", []),
        meta=data.get("meta", {}),
        feeds=FEEDS,                 # repopulates Source dropdown
        static_links=STATIC_LINKS,   # keeps quick links
    )

@app.route("/items.json")
def items_json():
    if not os.path.exists(ITEMS_PATH):
        return jsonify({"items": [], "meta": {}})
    with open(ITEMS_PATH, "r", encoding="utf-8") as f:
        payload = f.read()
    resp = make_response(payload)
    resp.headers["Content-Type"] = "application/json; charset=utf-8"
    return nocache(resp)

# ---------- exports for auditing ----------
@app.route("/items.csv")
def items_csv():
    data = read_items()
    items = data.get("items", [])

    # Filter by ts using query params
    now_ts = int(datetime.now(timezone.utc).timestamp())
    start_ts = parse_yyyy_mm_dd(request.args.get("start"), 0)
    end_ts   = parse_yyyy_mm_dd(request.args.get("end"), now_ts)
    if start_ts is None: start_ts = 0
    if end_ts   is None: end_ts   = now_ts

    filtered = [it for it in items if int(it.get("ts", 0)) >= start_ts and int(it.get("ts", 0)) <= end_ts]
    # newest first (should already be, but enforce)
    filtered.sort(key=lambda x: int(x.get("ts", 0)), reverse=True)

    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["date", "source", "title", "link", "summary"])
    for it in filtered:
        w.writerow([it.get("date",""), it.get("source",""), it.get("title",""), it.get("link",""), it.get("summary","")])

    resp = make_response(out.getvalue())
    resp.headers["Content-Type"] = "text/csv; charset=utf-8"
    resp.headers["Content-Disposition"] = 'attachment; filename="items.csv"'
    return nocache(resp)

@app.route("/audit.txt")
def audit_txt():
    data = read_items()
    items = data.get("items", [])

    now_ts = int(datetime.now(timezone.utc).timestamp())
    start_ts = parse_yyyy_mm_dd(request.args.get("start"), 0)
    end_ts   = parse_yyyy_mm_dd(request.args.get("end"), now_ts)
    if start_ts is None: start_ts = 0
    if end_ts   is None: end_ts   = now_ts

    filtered = [it for it in items if int(it.get("ts", 0)) >= start_ts and int(it.get("ts", 0)) <= end_ts]
    filtered.sort(key=lambda x: int(x.get("ts", 0)), reverse=True)

    lines = []
    for it in filtered:
        lines.append(f"{it.get('date','')} — {it.get('source','')} — {it.get('title','')}  {it.get('link','')}")

    resp = make_response("\n".join(lines) + ("\n" if lines else ""))
    resp.headers["Content-Type"] = "text/plain; charset=utf-8"
    return nocache(resp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
