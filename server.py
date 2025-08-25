import time
import logging
from flask import Flask, jsonify, request, Response
from flask_cors import CORS

from collect import collect_all, collect_debug  # our scraper

# --- Flask setup ---
app = Flask(__name__, static_folder="static", static_url_path="/static")
CORS(app)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# --- simple in-memory cache ---
_CACHE = None
_CACHE_TS = 0.0
TTL_SECONDS = 10 * 60  # 10 minutes


def _get_cached(force: bool = False):
    """Return cached data, optionally forcing a refresh."""
    global _CACHE, _CACHE_TS
    if force or not _CACHE or (time.time() - _CACHE_TS) > TTL_SECONDS:
        logging.info("Refreshing cache (force=%s)...", force)
        _CACHE = collect_all()
        _CACHE_TS = time.time()
    return _CACHE


HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Purdue Men's Basketball — Live Feed</title>
  <style>
    :root { --fg:#0b0b0c; --sub:#666; --chip:#eef2ff; --pill:#334155; --link:#1d4ed8; }
    *{box-sizing:border-box} body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Inter,Arial,sans-serif;
      margin:0;padding:24px;color:var(--fg);background:#fff}
    header{display:flex;align-items:center;gap:16px;margin-bottom:16px}
    h1{font-size:28px;margin:0}
    img.logo{height:36px;width:auto;object-fit:contain}
    .bar{display:flex;gap:12px;align-items:center;margin:12px 0 20px}
    input[type="search"]{flex:1;padding:10px 12px;border:1px solid #d1d5db;border-radius:8px;font-size:14px}
    select,button{padding:10px 12px;border:1px solid #d1d5db;border-radius:8px;background:#fff;font-size:14px;cursor:pointer}
    button.primary{background:#111827;color:#fff;border-color:#111827}
    .meta{color:var(--sub);font-size:12px;margin-top:2px}
    .card{border:1px solid #e5e7eb;border-radius:12px;padding:12px 14px;margin-bottom:10px}
    .row{display:flex;gap:8px;align-items:center}
    .chip{background:var(--chip);color:#1e3a8a;border-radius:999px;padding:2px 8px;font-size:12px}
    .empty{color:var(--sub);padding:32px;text-align:center}
    a{color:var(--link);text-decoration:none} a:hover{text-decoration:underline}
    .nowrap{white-space:nowrap}
  </style>
</head>
<body>
  <header>
    <img src="/static/logo.png" class="logo" alt="Purdue" onerror="this.style.display='none'"/>
    <h1>Purdue Men's Basketball — Live Feed</h1>
    <div class="nowrap" style="margin-left:auto;">
      <button id="btn-refresh" class="primary">Force Refresh</button>
      <a href="/api/debug" target="_blank" style="margin-left:10px;">debug</a>
    </div>
  </header>

  <div class="bar">
    <input id="q" type="search" placeholder="Filter by keyword (e.g., 'Painter', 'Braden Smith')" />
    <select id="src">
      <option value="">All sources</option>
    </select>
  </div>

  <div id="stamp" class="meta"></div>
  <div id="list"></div>

  <script>
    const list = document.getElementById('list');
    const q = document.getElementById('q');
    const src = document.getElementById('src');
    const stamp = document.getElementById('stamp');
    const btn = document.getElementById('btn-refresh');

    let data = { items: [], fetched_at: null };

    function render() {
      const term = (q.value || '').toLowerCase().trim();
      const srcFilter = src.value;
      let items = data.items.slice();

      if (term) {
        items = items.filter(it =>
          (it.title || '').toLowerCase().includes(term) ||
          (it.summary || '').toLowerCase().includes(term)
        );
      }
      if (srcFilter) items = items.filter(it => it.source === srcFilter);

      list.innerHTML = '';
      if (!items.length) {
        list.innerHTML = '<div class="empty">No items (try Force Refresh)</div>';
        return;
      }
      for (const it of items) {
        const div = document.createElement('div');
        div.className = 'card';
        div.innerHTML = `
          <div class="row">
            <span class="chip">${it.source}</span>
            <a href="${it.url}" target="_blank">${it.title}</a>
          </div>
          <div class="meta">${new Date(it.published || it.added_at || Date.now()).toLocaleString()} · ${it.source_type}</div>
          <div style="margin-top:6px">${(it.summary || '').replace(/</g,'&lt;')}</div>
        `;
        list.appendChild(div);
      }
    }

    function populateSources() {
      const all = [...new Set(data.items.map(i => i.source))].sort();
      src.innerHTML = '<option value="">All sources</option>' +
        all.map(s => `<option value="${s}">${s}</option>`).join('');
    }

    async function load() {
      const r = await fetch('/api/news?nocache=' + Date.now());
      data = await r.json();
      stamp.textContent = 'Loaded ' + new Date(data.fetched_at).toLocaleString();
      populateSources();
      render();
    }

    q.addEventListener('input', render);
    src.addEventListener('change', render);
    btn.addEventListener('click', async () => {
      btn.disabled = true; btn.textContent = 'Refreshing...';
      try {
        await fetch('/api/refresh-now', { method: 'POST' });
      } catch {}
      await load();
      btn.disabled = false; btn.textContent = 'Force Refresh';
    });

    load();
  </script>
</body>
</html>
"""

# -------------------- Routes --------------------

@app.get("/")
def ui():
    return Response(HTML, mimetype="text/html")


@app.get("/api/news")
def api_news():
    data = _get_cached(force=False)
    return jsonify(data)


@app.get("/api/news/raw")
def api_news_raw():
    return jsonify(collect_all())


@app.post("/api/refresh-now")
def api_refresh_now():
    _get_cached(force=True)
    return jsonify({"ok": True, "refreshed_at": time.time()})


@app.get("/api/debug")
def api_debug():
    dbg = collect_debug()
    return jsonify(dbg)


@app.get("/healthz")
def health():
    return jsonify({"ok": True})


# Gunicorn looks for "app"
if __name__ == "__main__":
    # Local dev: python server.py
    app.run(host="0.0.0.0", port=10000, debug=True)
