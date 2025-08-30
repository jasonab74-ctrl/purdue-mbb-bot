#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import sys
import threading
import time
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path
from flask import Flask, send_from_directory, render_template, jsonify, make_response, request

APP_DIR = Path(__file__).parent.resolve()
ITEMS_PATH = APP_DIR / "items.json"
LOCK_PATH = APP_DIR / ".collect.lock"
LAST_RUN_PATH = APP_DIR / ".last_collect.json"

# How often to refresh (minutes). Floor at 5 minutes.
REFRESH_MIN = int(os.environ.get("FEED_REFRESH_MIN", "30"))
REFRESH_SEC = max(300, REFRESH_MIN * 60)

# If items.json is 0 items OR older than this, /items.json will do a one-shot refresh.
STALE_MIN = max(5, int(os.environ.get("STALE_MIN", "15")))

# Consider a lock stale after this many seconds (e.g., collector crashed mid-run)
STALE_LOCK_SEC = int(os.environ.get("STALE_LOCK_SEC", "180"))

app = Flask(
    __name__,
    static_folder=str(APP_DIR / "static"),
    template_folder=str(APP_DIR / "templates"),
)

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _write_last_run(payload: dict) -> None:
    try:
        LAST_RUN_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

def _read_last_run() -> dict:
    try:
        return json.loads(LAST_RUN_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _collect_cmds() -> list[list[str]]:
    exe = sys.executable or "python"
    return [
        [exe, str(APP_DIR / "collect.py")],
        ["python", str(APP_DIR / "collect.py")],
        ["python3", str(APP_DIR / "collect.py")],
    ]

def _lock_is_stale() -> bool:
    try:
        if not LOCK_PATH.exists():
            return False
        mtime = datetime.fromtimestamp(LOCK_PATH.stat().st_mtime, timezone.utc)
        return (datetime.now(timezone.utc) - mtime) > timedelta(seconds=STALE_LOCK_SEC)
    except Exception:
        return True  # if we can't read it, treat as stale so we don't deadlock

def _clear_stale_lock():
    try:
        if _lock_is_stale():
            LOCK_PATH.unlink(missing_ok=True)
    except Exception:
        pass

def _acquire_lock(force: bool) -> dict | None:
    # Try to clear stale lock first
    _clear_stale_lock()

    if LOCK_PATH.exists():
        if force:
            # 🔐 HARD OVERRIDE: if caller passed force=1, blow away any lock
            try:
                LOCK_PATH.unlink(missing_ok=True)
            except Exception:
                pass
        else:
            return {"skipped": True, "reason": "lock_exists", "invoked_at": utc_now_iso()}

    try:
        LOCK_PATH.touch(exist_ok=False)
    except FileExistsError:
        return {"skipped": True, "reason": "lock_exists", "invoked_at": utc_now_iso()}
    return None  # success

def _release_lock():
    try:
        LOCK_PATH.unlink(missing_ok=True)
    except Exception:
        pass

def run_collect_once(force: bool = False) -> dict:
    """Run collect.py safely. Return a summary dict (always)."""
    lock_fail = _acquire_lock(force=force)
    if lock_fail:
        _write_last_run(lock_fail)
        return lock_fail

    try:
        last_err = None
        for cmd in _collect_cmds():
            try:
                proc = subprocess.run(
                    cmd,
                    cwd=str(APP_DIR),
                    capture_output=True,
                    text=True,
                    timeout=max(90, REFRESH_SEC // 2),  # give GN a bit longer
                )
                # Try to parse collector JSON summary from stdout
                try:
                    payload = json.loads((proc.stdout or "").strip() or "{}")
                except Exception:
                    payload = {}
                # Always attach runner & rc & tails for debugging
                payload.update({
                    "runner": " ".join(cmd),
                    "rc": proc.returncode,
                    "stdout_tail": (proc.stdout or "")[-1200:],
                    "stderr_tail": (proc.stderr or "")[-1200:],
                    "invoked_at": utc_now_iso(),
                })
                _write_last_run(payload)
                return payload
            except Exception as e:
                last_err = str(e)

        payload = {"error": "spawn_failed", "detail": last_err, "invoked_at": utc_now_iso()}
        _write_last_run(payload)
        return payload
    finally:
        _release_lock()

def scheduler_loop():
    # Immediate pass on boot so items.json populates quickly
    run_collect_once(force=False)
    while True:
        time.sleep(REFRESH_SEC)
        run_collect_once(force=False)

def ensure_scheduler_started():
    _clear_stale_lock()
    t = threading.Thread(target=scheduler_loop, name="collector-scheduler", daemon=True)
    t.start()

def _read_items_file() -> dict:
    if ITEMS_PATH.exists():
        try:
            return json.loads(ITEMS_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {"items": [], "generated_at": utc_now_iso()}
    return {"items": [], "generated_at": utc_now_iso()}

def _is_stale_or_empty(data: dict) -> bool:
    items = data.get("items") or []
    if not isinstance(items, list):
        return True
    if len(items) == 0:
        return True
    try:
        mtime = datetime.fromtimestamp(ITEMS_PATH.stat().st_mtime, timezone.utc)
        return (datetime.now(timezone.utc) - mtime) > timedelta(minutes=STALE_MIN)
    except Exception:
        return True

# ----------------------- Routes -----------------------

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/items.json")
def items_json():
    data = _read_items_file()
    # Self-heal: if empty or stale, kick a refresh (non-blocking) and re-read.
    if _is_stale_or_empty(data):
        run_collect_once(force=False)
        data = _read_items_file()
    resp = make_response(json.dumps(data))
    resp.headers["Content-Type"] = "application/json; charset=utf-8"
    resp.headers["Cache-Control"] = "no-store, max-age=0"
    return resp

@app.route("/fight_song.mp3")
def fight_song():
    resp = send_from_directory(str(APP_DIR), "fight_song.mp3", conditional=True)
    resp.headers["Accept-Ranges"] = "bytes"
    resp.headers["Cache-Control"] = "public, max-age=604800"
    return resp

@app.route("/health")
def health():
    ok = True
    data = _read_items_file()
    items = data.get("items", [])
    count = len(items) if isinstance(items, list) else 0
    try:
        mtime = datetime.fromtimestamp(ITEMS_PATH.stat().st_mtime, timezone.utc).isoformat()
    except Exception:
        mtime, ok = None, False
    return jsonify({
        "ok": ok,
        "items": count,
        "mtime": mtime,
        "now": utc_now_iso(),
        "last_run": _read_last_run(),
        "lock_exists": LOCK_PATH.exists(),
    })

@app.route("/diag")
def diag():
    out = {"now": utc_now_iso(), "refresh_min": REFRESH_MIN, "stale_min": STALE_MIN, "stale_lock_sec": STALE_LOCK_SEC}
    data = _read_items_file()
    items = data.get("items") or []
    out["items_count"] = len(items) if isinstance(items, list) else 0
    out["generated_at"] = data.get("generated_at")
    out["lock_exists"] = LOCK_PATH.exists()
    try:
        out["items_mtime"] = datetime.fromtimestamp(ITEMS_PATH.stat().st_mtime, timezone.utc).isoformat()
    except Exception:
        out["items_mtime"] = None
    out["last_run"] = _read_last_run()
    sample = []
    for it in items[:5]:
        sample.append({"title": (it.get("title") or "")[:90], "source": it.get("source"), "date": it.get("date")})
    out["sample"] = sample
    return jsonify(out)

@app.route("/collect-now", methods=["POST", "GET"])
def collect_now():
    """Manual trigger; add ?force=1 to ignore any existing lock."""
    force = request.args.get("force") in ("1", "true", "yes")
    payload = run_collect_once(force=force)
    return jsonify(payload)

@app.route("/unlock", methods=["POST", "GET"])
def unlock():
    """Hard unlock: delete lock file and report status."""
    existed = LOCK_PATH.exists()
    _clear_stale_lock()
    try:
        LOCK_PATH.unlink(missing_ok=True)
    except Exception:
        pass
    return jsonify({"ok": True, "existed_before": existed, "now_exists": LOCK_PATH.exists(), "ts": utc_now_iso()})

# Start scheduler
ensure_scheduler_started()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
