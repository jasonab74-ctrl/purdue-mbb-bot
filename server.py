# server.py
import os, time
from flask import Flask, jsonify, Response
from flask_cors import CORS
from collect import collect_all

app = Flask(__name__)
CORS(app)

CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "300"))
_cache_data = None
_cache_ts = 0

@app.route("/api/news")
def api_news():
    global _cache_data, _cache_ts
    now = time.time()
    if not _cache_data or (now - _cache_ts) > CACHE_TTL_SECONDS:
        _cache_data = collect_all()
        _cache_ts = now
    return jsonify(_cache_data or [])

@app.route("/api/health")
def api_health():
    return {"status": "ok"}

@app.route("/ui")
def ui():
    # minimal UI that pulls from /api/news on same host
    html = """<!doctype html><meta charset="utf-8">
<title>Purdue Men's Basketball — Live Feed</title>
<div id="list" style="max-width:900px;margin:24px auto;font:16px system-ui;"></div>
<script>
(async () => {
  const res = await fetch('/api/news');
  const items = await res.json();
  const list = document.getElementById('list');
  list.innerHTML = items.map(i =>
    `<div style="border:1px solid #e8e8ea;border-radius:12px;padding:12px;margin:8px 0">
       <a href="${i.url}" target="_blank" style="font-weight:600;text-decoration:none">${i.title}</a>
       <div style="color:#666;font-size:13px;margin-top:6px">${new Date(i.published_at).toLocaleString()} • ${i.source||''}</div>
     </div>`
  ).join('');
})();
</script>"""
    return Response(html, mimetype="text/html")

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
