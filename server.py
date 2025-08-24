# server.py
import os, time, glob, sys
from flask import Flask, jsonify, Response
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Try to import the collector; if it fails, keep the app up and surface the reason.
COLLECT_IMPORT_ERROR = None
try:
    from collect import collect_all, collect_debug  # expects collect.py at repo root
except Exception as e:
    COLLECT_IMPORT_ERROR = f"{type(e).__name__}: {e}"

    def collect_all():
        # Return empty list so /api/news works, but include a hint in /api/debug
        return []

    def collect_debug():
        return {
            "import_error": COLLECT_IMPORT_ERROR,
            "cwd": os.getcwd(),
            "sys_path": sys.path,
            "files_in_app": sorted(os.listdir("/app")) if os.path.exists("/app") else [],
            "glob_py_at_root": sorted(glob.glob("*.py")),
            "env": {
                "PYTHONPATH": os.environ.get("PYTHONPATH"),
            },
        }

CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "300"))
_cache_data = None
_cache_ts = 0

# ---------------- API ROUTES ----------------

@app.route("/api/news")
def api_news():
    global _cache_data, _cache_ts
    now = time.time()
    if not _cache_data or (now - _cache_ts) > CACHE_TTL_SECONDS:
        _cache_data = collect_all()
        _cache_ts = now
    return jsonify(_cache_data or [])

@app.route("/api/news/raw")
def api_news_raw():
    return jsonify(collect_all())

@app.route("/api/refresh", methods=["POST", "GET"])
def refresh():
    global _cache_data, _cache_ts
    _cache_data = None
    _cache_ts = 0
    return {"status": "refreshed"}

@app.route("/api/debug")
def api_debug():
    dbg = collect_debug()
    # If import failed, add more context
    if COLLECT_IMPORT_ERROR:
        dbg["note"] = "collect.py did not import; see import_error and files_in_app above."
    return jsonify(dbg)

@app.route("/api/health")
def api_health():
    return {"status": "ok"}

@app.route("/healthz")
def healthz():
    return {"status": "ok"}

# ---------------- SIMPLE UI ----------------

@app.route("/ui")
@app.route("/ui/")
def ui():
    html = """<!doctype html>
<html>
<head><meta charset="utf-8"><title>Purdue Men's Basketball — Live Feed</title></head>
<body style="font-family:system-ui, sans-serif; max-width:900px; margin:20px auto;">
  <h1>Purdue Men's Basketball — Live Feed</h1>
  <div style="margin:8px 0;">
    <button onclick="refresh()">Force Refresh</button>
    <button onclick="loadRaw()">Load Fresh (no cache)</button>
    <a href="/api/debug" target="_blank">debug</a>
  </div>
  <div id="meta" style="color:#666;margin:6px 0;"></div>
  <div id="list"></div>
<script>
async function renderFrom(url){
  const res = await fetch(url);
  const items = await res.json();
  const meta = document.getElementById('meta');
  const list = document.getElementById('list');
  meta.textContent = `Loaded ${items.length} • ${new Date().toLocaleString()}`;
  if(!items.length){
    list.innerHTML = '<p>No items found.</p>'; return;
  }
  list.innerHTML = items.map(i => `
    <div style="border:1px solid #ddd; border-radius:8px; padding:10px; margin:8px 0;">
      <a href="${i.url}" target="_blank" style="font-weight:bold">${(i.title||'').replace(/</g,'&lt;').replace(/>/g,'&gt;')}</a><br>
      <small>${new Date(i.published_at).toLocaleString()} • ${i.source||''}</small>
      <p>${(i.description||'')}</p>
    </div>`).join('');
}
async function load(){ return renderFrom('/api/news'); }
async function loadRaw(){ return renderFrom('/api/news/raw'); }
async function refresh(){ await fetch('/api/refresh'); await load(); }
load();
</script>
</body>
</html>"""
    return Response(html, mimetype="text/html")

# ---------------- ENTRY ----------------

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
