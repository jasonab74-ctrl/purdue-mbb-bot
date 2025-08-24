# server.py
import os
import time
from flask import Flask, jsonify
from flask_cors import CORS

from collect import collect_all

app = Flask(__name__)
CORS(app)

# simple in-memory cache so your API isn't hammering sources every request
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "300"))  # 5 minutes default
_cache_data = None
_cache_ts = 0

@app.route("/api/news")
def api_news():
    global _cache_data, _cache_ts
    now = time.time()
    if not _cache_data or (now - _cache_ts) > CACHE_TTL_SECONDS:
        try:
            _cache_data = collect_all()
        finally:
            _cache_ts = now
    return jsonify(_cache_data or [])

@app.route("/api/health")
def api_health():
    return {"status": "ok"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
