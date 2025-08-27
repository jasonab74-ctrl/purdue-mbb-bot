#!/usr/bin/env python3
from flask import Flask, jsonify, render_template, request, abort, url_for
from datetime import datetime, timezone
from pathlib import Path
import json, subprocess

app = Flask(__name__, static_folder="static", template_folder="templates")
DATA_PATH = Path("data.json")
REFRESH_KEY = "mbb_refresh_6P7wP9dXr2Jq"

def load_data():
    if DATA_PATH.exists():
        return json.loads(DATA_PATH.read_text())
    return {"modified": "never", "count": 0, "items": []}

@app.get("/")
def index():
    return render_template("index.html", modified=load_data().get("modified","never"))

@app.get("/api/items")
def api_items():
    return jsonify(load_data())

@app.get("/api/last-mod")
def api_last_mod():
    return jsonify({"modified": load_data().get("modified","never")})

@app.route("/api/refresh-now", methods=["GET","POST"])
def refresh_now():
    key = request.args.get("key") or request.form.get("key")
    if key != REFRESH_KEY:
        abort(403)
    try:
        subprocess.check_call(["python", "collect.py"])
        when = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        return jsonify({"ok": True, "refreshed": when})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
