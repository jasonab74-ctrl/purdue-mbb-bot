# server.py
from __future__ import annotations
import os
import time
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS

from collect import collect_all, collect_debug

app = Flask(__name__, static_folder="static")
CORS(app)

# ---- Simple cache so requests don't trigger network every time ----
CACHE_TTL = int(os.getenv("CACHE_TTL", "600"))  # seconds
_cache_data = None
_cache_ts = 0.0


def _refresh_cache():
    global _cache_data, _cache_ts
    _cache_data = collect_all()
    _cache_ts = time.time()
    return {
        "status": "ok",
        "items": 0 if _cache_data is None else len(_cache_data),
        "loaded_at": _cache_ts,
        "ttl": CACHE_TTL,
    }


def _get_cache():
    if _cache_data is None or (time.time() - _cache_ts) > CACHE_TTL:
        _refresh_cache()
    return _cache_data


# ---- Routes ----
@app.get("/")
def root():
    # Serve the existing UI (index.html) from /static
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/news")
def api_news():
    return jsonify(_get_cache())


@app.get("/api/news/raw")
def api_news_raw():
    # same as /api/news, kept for back-compat
    return jsonify(_get_cache())


@app.post("/api/refresh-now")
def api_refresh_now():
    return jsonify(_refresh_cache())


@app.get("/api/debug")
def api_debug():
    dbg = collect_debug()
    dbg["cache_items"] = 0 if _cache_data is None else len(_cache_data)
    dbg["cache_loaded_at"] = _cache_ts
    dbg["cache_ttl"] = CACHE_TTL
    return jsonify(dbg)


@app.get("/healthz")
def healthz():
    return "ok", 200


if __name__ == "__main__":
    # Local dev
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "10000")), debug=False)
