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
  <style>
  /* Safe, light polish — matches classes used in the script */
  .status { font-size: 12px; color: #666; margin: 6px 0 12px; }
  .card { padding: 12px 14px; border: 1px solid #eee; border-radius: 10px; margin: 10px 0; }
  .title { font-weight: 700; text-decoration: none; display: inline-block; margin-bottom: 6px; }
  .title:hover { text-decoration: underline; }
  .meta { font-size: 12px; color: #777; margin-bottom: 8px; }
  .summary { margin: 0; line-height: 1.4; }
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
(async function () {
  // ----------------- helpers -----------------
  function stripTags(html) {
    if (!html) return '';
    const div = document.createElement('div');
    div.innerHTML = html;
    return div.textContent || div.innerText || '';
  }

  function fmtDate(tsOrIso) {
    if (!tsOrIso) return '';
    // supports epoch seconds (number) or ISO string
    const ms = typeof tsOrIso === 'number'
      ? tsOrIso * 1000
      : Date.parse(tsOrIso);
    if (Number.isNaN(ms)) return '';
    return new Date(ms).toLocaleString();
  }

  function el(tag, className, text) {
    const e = document.createElement(tag);
    if (className) e.className = className;
    if (text != null) e.textContent = text;
    return e;
  }

  // ----------------- fetch -----------------
  const res = await fetch('/api/news', { cache: 'no-store' });
  const data = await res.json();

// --- Sort newest → oldest safely ---
function itemTs(it) {
  // prefer epoch seconds if present; otherwise parse ISO
  if (typeof it.published_ts === 'number') return it.published_ts;
  if (it.published) {
    const ms = Date.parse(it.published);
    if (!Number.isNaN(ms)) return Math.floor(ms / 1000);
  }
  return 0; // unknown date goes to the bottom
}

const items = (data.items || [])
  .slice()
  .sort((a, b) => itemTs(b) - itemTs(a));
  // ----------------- render -----------------
  // IMPORTANT: make sure your list container has id="feed"
  // (If it doesn't, just change its id to "feed" in the HTML markup.)
  const list = document.querySelector('#feed');
  if (!list) {
    console.warn('No #feed container found');
    return;
  }
  list.innerHTML = '';

  // top status line (optional — shows when data was loaded and count)
  const status = el('div', 'status',
    `Loaded ${fmtDate(data.updated_ts || data.updated)} • ${items.length} items`);
  list.appendChild(status);

  for (const it of items) {
    const card = el('div', 'card');

    // source + time (small line)
    const meta = el(
      'div',
      'meta',
      `${it.source || 'Source'} • ${fmtDate(it.published_ts || it.published)}`
    );

    // clean title text, clickable link (no HTML blobs)
    const titleLink = el('a', 'title', stripTags(it.title || 'Untitled'));
    titleLink.href = it.link || '#';
    titleLink.target = '_blank';
    titleLink.rel = 'noopener';

    // clean summary/description (no HTML)
    const sum = el('p', 'summary', stripTags(it.summary || it.description || ''));

    card.appendChild(titleLink);
    card.appendChild(meta);
    card.appendChild(sum);
    list.appendChild(card);
  }
})();
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
