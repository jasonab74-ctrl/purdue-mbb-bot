from flask import Flask, jsonify, request, Response, redirect
from flask_cors import CORS
from datetime import datetime, timezone
import json
import threading

# local
import collect

app = Flask(__name__)
CORS(app)

# ---------- Minimal UI (inline SVG so the logo never breaks) ----------
HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>Purdue Men's Basketball — Live Feed</title>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <style>
    :root {
      --bg: #ffffff;
      --text: #111827;
      --muted: #6b7280;
      --chip: #f3f4f6;
      --brand: #000000;
      --accent: #cfb991; /* Purdue gold */
    }
    * { box-sizing: border-box; }
    body {
      margin: 0; padding: 24px;
      font: 16px/1.45 ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Apple Color Emoji","Segoe UI Emoji";
      color: var(--text); background: var(--bg);
    }
    header { display:flex; align-items:center; gap:16px; margin-bottom:16px; }
    h1 { font-size: clamp(22px, 2.8vw, 36px); margin:0; }
    .toolbar { display:flex; gap:12px; align-items:center; flex-wrap:wrap; }
    .btn {
      appearance:none; border:0; background:#0f172a; color:#fff; padding:10px 14px; border-radius:10px;
      font-weight:600; cursor:pointer;
    }
    .btn.secondary { background:#111827; }
    .input, select {
      width: min(100%, 1000px);
      padding:12px 14px; border:1px solid #e5e7eb; border-radius:10px; background:#fff;
      font-size:14px;
    }
    .meta { color: var(--muted); margin-top:10px; }
    .list { margin-top:22px; display:grid; gap:10px; }
    .card {
      border:1px solid #e5e7eb; border-radius:12px; padding:14px; background:#fff;
      display:flex; flex-direction:column; gap:6px;
    }
    .card a { color:#0f172a; text-decoration:none; font-weight:600; }
    .card small { color:var(--muted); }
    .logo {
      width:52px; height:52px; display:inline-flex; align-items:center; justify-content:center;
      border-radius:12px; background:#fff; border:1px solid #e5e7eb;
    }
    .pill { background: var(--chip); padding:4px 8px; border-radius:999px; font-size:12px; color:#374151; }
    .row { display:flex; align-items:center; gap:8px; justify-content:space-between; flex-wrap:wrap; }
    .left { display:flex; align-items:center; gap:14px; }
    .right { display:flex; align-items:center; gap:10px; }
  </style>
</head>
<body>
  <header>
    <div class="logo" title="Purdue">
      <!-- inline Purdue 'P' (simple) -->
      <svg viewBox="0 0 64 64" width="34" height="34" aria-hidden="true">
        <defs>
          <linearGradient id="g" x1="0" x2="1">
            <stop offset="0" stop-color="#cfb991"/><stop offset="1" stop-color="#cfb991"/>
          </linearGradient>
        </defs>
        <path fill="#000" d="M6 14h35c9 0 15 6 15 13s-6 13-15 13H23l-5 10H6l7-13H5z"/>
        <path fill="url(#g)" d="M13 20h27c6 0 9 3 9 7s-3 7-9 7H22l-5 10h-6l7-13h-7z"/>
      </svg>
    </div>
    <h1>Purdue Men's Basketball — Live Feed</h1>
    <div class="right">
      <button class="btn" id="force">Force Refresh</button>
      <a class="pill" href="/api/debug">debug</a>
    </div>
  </header>

  <div class="toolbar">
    <input id="q" class="input" placeholder="Filter by keyword (e.g., 'Painter', 'Braden Smith')" />
    <select id="source">
      <option value="">All sources</option>
    </select>
  </div>
  <div class="meta" id="loaded">Loaded ...</div>

  <div class="list" id="list"></div>

  <script>
    const $q = document.getElementById('q');
    const $src = document.getElementById('source');
    const $list = document.getElementById('list');
    const $loaded = document.getElementById('loaded');
    const $force = document.getElementById('force');

    function fmtDate(s) {
      try { return new Date(s).toLocaleString(); } catch { return s; }
    }
    function itemRow(it) {
      const a = document.createElement('div');
      a.className = 'card';
      a.innerHTML = `
        <div class="row">
          <div class="left">
            <span class="pill">${it.source}</span>
            <a href="${it.link}" target="_blank" rel="noopener">${it.title}</a>
          </div>
          <small>${fmtDate(it.published)}</small>
        </div>
        ${it.summary ? `<small>${it.summary}</small>` : ``}
      `;
      return a;
    }

    let DATA = { items: [], sources: [], updated: null };

    function render() {
      const q = $q.value.trim().toLowerCase();
      const src = $src.value;
      let rows = DATA.items.slice();
      if (q) rows = rows.filter(r =>
        (r.title||'').toLowerCase().includes(q) ||
        (r.summary||'').toLowerCase().includes(q)
      );
      if (src) rows = rows.filter(r => r.source === src);
      $list.replaceChildren(...rows.map(itemRow));
      $loaded.textContent = DATA.updated ? `Loaded ${fmtDate(DATA.updated)} (${rows.length} items)` : 'Loaded';
    }

    async function load() {
      const res = await fetch('/api/news');
      const json = await res.json();
      DATA = json;
      // fill source dropdown
      $src.replaceChildren(new Option('All sources', ''));
      const uniq = [...new Set(DATA.items.map(i => i.source))].sort();
      for (const s of uniq) $src.appendChild(new Option(s, s));
      render();
    }

    $q.addEventListener('input', render);
    $src.addEventListener('change', render);
    $force.addEventListener('click', async () => {
      $force.disabled = true;
      try { await fetch('/api/refresh-now', { method: 'POST' }); } catch {}
      await load();
      $force.disabled = false;
    });

    load();
  </script>
</body>
</html>
"""

# -------------- Routes --------------

@app.route("/")
def ui_root():
    return Response(HTML, mimetype="text/html")

@app.route("/ui")
def ui_alias():
    return redirect("/", code=302)

@app.route("/api/news")
def api_news():
    data = collect.get_cached_or_collect()
    return jsonify(data)

@app.route("/api/news/raw")
def api_news_raw():
    data = collect.get_cached_or_collect(include_raw=True)
    return jsonify(data)

@app.route("/api/refresh-now", methods=["POST"])
def api_refresh_now():
    # refresh in this request
    data = collect.collect_all(force=True)
    return jsonify({"ok": True, "count": len(data["items"])})

@app.route("/api/debug")
def api_debug():
    dbg = collect.collect_debug()
    return Response(json.dumps(dbg, indent=2), mimetype="application/json")


# Run locally (Render uses Gunicorn: `server:app`)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=False)
