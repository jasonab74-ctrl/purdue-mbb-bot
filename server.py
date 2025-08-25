# server.py
from __future__ import annotations
import threading
import time
from flask import Flask, jsonify, request, Response
from flask_cors import CORS

import collect  # local module

app = Flask(__name__)
CORS(app)

# ----------------- cache -----------------
_cache = collect.collect_debug_empty()
_cache_lock = threading.Lock()
_TTL_SEC = 15 * 60  # 15 minutes
_refresh_running = False


def _now() -> float:
    return time.time()


def _stale() -> bool:
    # _cache["updated"] is ms; compare to seconds
    if not _cache.get("updated"):
        return True
    age_s = (_now() - (_cache["updated"] / 1000.0))
    return age_s > _TTL_SEC


def _do_refresh():
    global _cache, _refresh_running
    try:
        data = collect.collect_all()
        with _cache_lock:
            _cache = data
    finally:
        _refresh_running = False


def _ensure_background_refresh():
    global _refresh_running
    if _refresh_running:
        return
    _refresh_running = True
    t = threading.Thread(target=_do_refresh, daemon=True)
    t.start()


# --------------- routes ------------------

@app.route("/")
@app.route("/ui")
def ui():
    # Minimal single-file UI (kept simple on purpose)
    HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Purdue Men's Basketball — Live Feed</title>
<link rel="icon" href="https://upload.wikimedia.org/wikipedia/commons/c/c4/Purdue_Boilermakers_logo.svg">
<style>
  :root { --bg:#f6f7fb; --card:#fff; --ink:#121417; --muted:#6b7280; --pill:#eef2ff; --pillText:#374151; }
  * { box-sizing: border-box; }
  body { margin: 0; font: 16px/1.45 system-ui, -apple-system, Segoe UI, Roboto, sans-serif; color: var(--ink); background: var(--bg); }
  header { display:flex; align-items:center; gap:16px; padding:20px 24px; }
  header img { height:42px; width:42px; }
  h1 { font-size: 28px; margin:0; }
  .bar { display:flex; gap:12px; padding: 0 24px 12px; align-items:center; }
  input, select { width:100%; padding:12px 14px; border:1px solid #d1d5db; border-radius:12px; background:#fff; }
  button { padding:10px 14px; border-radius:12px; border:0; background:#0f172a; color:#fff; cursor:pointer; }
  button:disabled { opacity:0.6; cursor:default; }
  .meta { color: var(--muted); font-size: 13px; padding: 0 24px; }
  .grid { padding: 12px 24px 28px; display:grid; grid-template-columns: repeat(auto-fill, minmax(380px, 1fr)); gap:14px; }
  .card { background:var(--card); border:1px solid #e5e7eb; border-radius:14px; padding:14px; display:flex; gap:10px; flex-direction:column; }
  .title { font-weight:600; font-size:16px; }
  .src { display:flex; gap:8px; align-items:center; }
  .pill { background:var(--pill); color:var(--pillText); padding:4px 8px; border-radius:999px; font-size:12px; }
  a { color:#0a58ca; text-decoration:none; }
  a:hover { text-decoration:underline; }
  .empty { color: var(--muted); text-align:center; margin: 60px 0 100px; }
</style>
</head>
<body>
  <header>
    <img alt="P" src="https://upload.wikimedia.org/wikipedia/commons/c/c4/Purdue_Boilermakers_logo.svg">
    <h1>Purdue Men's Basketball — Live Feed</h1>
    <div style="margin-left:auto; display:flex; gap:10px;">
      <button id="btnRefresh">Force Refresh</button>
      <a href="/api/debug" target="_blank" style="align-self:center; text-decoration:none;">debug</a>
    </div>
  </header>

  <div class="bar">
    <input id="q" placeholder="Filter by keyword (e.g., 'Painter', 'Braden Smith')" />
    <select id="source">
      <option value="">All sources</option>
    </select>
  </div>

  <div class="meta" id="meta">Loaded …</div>
  <div class="grid" id="grid"></div>
  <div class="empty" id="empty" style="display:none;">No items (try Force Refresh)</div>

<script>
const fmtTime = (ms) => ms ? new Date(ms).toLocaleString() : "never";
const $ = (id) => document.getElementById(id);

const state = { data: null };

function render() {
  const data = state.data || {items:[], updated:0};
  $("meta").textContent = "Loaded " + fmtTime(data.updated) + (data.items.length ? "" : "");
  const grid = $("grid");
  grid.innerHTML = "";
  const q = $("q").value.trim().toLowerCase();
  const srcVal = $("source").value;

  let items = data.items;
  if (q) items = items.filter(it =>
    (it.title||"").toLowerCase().includes(q) ||
    (it.summary||"").toLowerCase().includes(q) ||
    (it.source||"").toLowerCase().includes(q)
  );
  if (srcVal) items = items.filter(it => (it.source || "") === srcVal);

  $("empty").style.display = items.length ? "none" : "block";

  // sources dropdown
  const uniqueSources = [...new Set((data.items||[]).map(it => it.source).filter(Boolean))].sort();
  const sel = $("source");
  const prior = sel.value;
  sel.innerHTML = '<option value="">All sources</option>' + uniqueSources.map(s => `<option value="${s}">${s}</option>`).join("");
  if (prior) sel.value = prior;

  for (const it of items) {
    const published = it.published ? new Date(it.published).toLocaleString() : "";
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
      <div class="title"><a href="${it.link}" target="_blank" rel="noopener">${it.title}</a></div>
      <div class="src">
        <span class="pill">${it.source || "Source"}</span>
        <span class="meta">${published}</span>
      </div>
    `;
    grid.appendChild(card);
  }
}

async function load() {
  try {
    const r = await fetch("/api/news");
    state.data = await r.json();
  } catch (e) {
    state.data = {items:[], updated:0};
  }
  render();
}

async function forceRefresh() {
  $("btnRefresh").disabled = true;
  try {
    await fetch("/api/refresh-now", {method:"POST"});
  } catch {}
  // Poll for fresh cache (up to ~12s)
  let tries = 12;
  const start = Date.now();
  while (tries--) {
    await new Promise(r => setTimeout(r, 1000));
    const r = await fetch("/api/news?nocache=" + Date.now());
    const data = await r.json();
    if (data.updated && data.updated > start) {
      state.data = data;
      break;
    }
  }
  $("btnRefresh").disabled = false;
  render();
}

$("q").addEventListener("input", render);
$("source").addEventListener("change", render);
$("btnRefresh").addEventListener("click", forceRefresh);
load();
</script>
</body>
</html>"""
    return Response(HTML, mimetype="text/html")


@app.route("/api/news")
def api_news():
    # Always return cached data quickly; kick a background refresh if stale.
    if _stale():
        _ensure_background_refresh()
    with _cache_lock:
        return jsonify(_cache)


@app.route("/api/refresh-now", methods=["POST"])
def api_refresh_now():
    _ensure_background_refresh()
    return jsonify({"status": "refresh-started"})


@app.route("/api/debug")
def api_debug():
    # Lightweight: NEVER fetch here. Only show last-known cache & source stats.
    with _cache_lock:
        payload = {
            "count": _cache.get("count", 0),
            "items": [],  # don't dump items here; keep this light
            "sources": _cache.get("sources", []),
            "updated": _cache.get("updated", 0),
        }
    return jsonify(payload)


# ------------- local dev -------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
