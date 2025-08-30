#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import json
import threading
import time
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, send_from_directory, render_template, jsonify, make_response

APP_DIR = Path(__file__).parent.resolve()
ITEMS_PATH = APP_DIR / "items.json"
LOCK_PATH = APP_DIR / ".collect.lock"

# Env knob — default 30 minutes
REFRESH_MIN = int(os.environ.get("FEED_REFRESH_MIN", "30"))
REFRESH_SEC = max(300, REFRESH_MIN * 60)  # hard floor 5 min

app = Flask(
    __name__,
    static_folder=str(APP_DIR / "static"),
    template_folder=str(APP_DIR / "templates"),
)

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def run_collect_once() -> dict:
    """Call collect.py in a subprocess with a simple file lock to avoid overlap."""
    # non-blocking lock via filesystem
    try:
        LOCK_PATH.touch(exist_ok=False)
    except FileExistsError:
        return {"skipped": True, "reason": "lock_exists"}
    try:
        proc = subprocess.run(
            ["python", str(APP_DIR / "collect.py")],
            cwd=str(APP_DIR),
            capture_output=True,
            text=True,
            timeout=max(60, REFRESH_SEC // 2),
        )
        # Try to parse collector JSON summary from stdout; otherwise relay returncode
        try:
            payload = json.loads(proc.stdout.strip() or "{}")
        except Exception:
            payload = {"stdout": proc.stdout[-800:], "stderr": proc.stderr[-800:], "rc": proc.returncode}
        payload["invoked_at"] = utc_now_iso()
        return payload
    finally:
        try:
            LOCK_PATH.unlink(missing_ok=True)
        except Exception:
            pass

def scheduler_loop():
    # Do an immediate pass on boot so /items.json populates quickly
    run_collect_once()
    while True:
        time.sleep(REFRESH_SEC)
        run_collect_once()

def ensure_scheduler_started():
    t = threading.Thread(target=scheduler_loop, name="collector-scheduler", daemon=True)
    t.start()

# ----------------------- Routes -----------------------

@app.route("/")
def index():
    # index.html uses fetch('/items.json'); just render the template
    return render_template("index.html")

@app.route("/items.json")
def items_json():
    # Serve items with no caching so the page always reflects latest data
    if ITEMS_PATH.exists():
        resp = make_response(ITEMS_PATH.read_text(encoding="utf-8"))
    else:
        resp = make_response(json.dumps({"items": [], "generated_at": utc_now_iso()}))
    resp.headers["Content-Type"] = "application/json; charset=utf-8"
    resp.headers["Cache-Control"] = "no-store, max-age=0"
    return resp

@app.route("/fight_song.mp3")
def fight_song():
    # Range support is handled by Werkzeug when using send_from_directory
    resp = send_from_directory(str(APP_DIR), "fight_song.mp3", conditional=True)
    resp.headers["Accept-Ranges"] = "bytes"
    resp.headers["Cache-Control"] = "public, max-age=604800"
    return resp

@app.route("/health")
def health():
    ok = True
    count = 0
    mtime = None
    if ITEMS_PATH.exists():
        try:
            data = json.loads(ITEMS_PATH.read_text(encoding="utf-8"))
            items = data.get("items", [])
            count = len(items) if isinstance(items, list) else 0
            mtime = datetime.fromtimestamp(ITEMS_PATH.stat().st_mtime, timezone.utc).isoformat()
        except Exception:
            ok = False
    return jsonify({"ok": ok, "items": count, "mtime": mtime, "now": utc_now_iso()})

@app.route("/diag")
def diag():
    """Quick on-box debugging without opening Railway logs."""
    out = {"now": utc_now_iso(), "refresh_min": REFRESH_MIN}
    if ITEMS_PATH.exists():
        try:
            data = json.loads(ITEMS_PATH.read_text(encoding="utf-8"))
        except Exception:
            data = {"items": []}
        out["items_count"] = len(data.get("items", [])) if isinstance(data.get("items"), list) else 0
        out["generated_at"] = data.get("generated_at")
        out["items_mtime"] = datetime.fromtimestamp(ITEMS_PATH.stat().st_mtime, timezone.utc).isoformat()
        # Show a couple of sample sources for quick sanity
        sample = []
        for it in (data.get("items") or [])[:5]:
            sample.append({"title": it.get("title","")[:80], "source": it.get("source"), "date": it.get("date")})
        out["sample"] = sample
    else:
        out["items_count"] = 0
        out["generated_at"] = None
        out["items_mtime"] = None
    return jsonify(out)

# Static files (favicon etc.) are served automatically via /static/...

# Kick off the background scheduler when the app starts under Gunicorn
ensure_scheduler_started()

if __name__ == "__main__":
    # Dev run: python server.py
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
