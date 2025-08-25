from __future__ import annotations
import time
from flask import Flask, jsonify, Response, request
from flask_cors import CORS
from collect import collect_all, collect_debug

app = Flask(__name__, static_folder="static")
CORS(app, resources={r"/api/*": {"origins": "*"}})

CACHE_TTL = 600  # 10 minutes
_cache_data = None
_cache_at = 0

def get_cached():
    global _cache_data, _cache_at
    now = time.time()
    if not _cache_data or (now - _cache_at) > CACHE_TTL:
        _cache_data = collect_all()
        _cache_at = now
    return _cache_data

@app.get("/api/news")
def api_news():
    return jsonify(get_cached())

@app.get("/api/news/raw")
def api_news_raw():
    # just a synonym here; you could return pre-filter if you want
    return jsonify(get_cached())

@app.get("/api/debug")
def api_debug():
    # safer: don’t burn cache here; do a fresh sample but still bounded by budgets
    dbg = collect_debug()
    return jsonify(dbg)

@app.post("/api/refresh-now")
def api_refresh_now():
    global _cache_data, _cache_at
    _cache_data = collect_all()
    _cache_at = time.time()
    return jsonify({"ok": True, "count": _cache_data["count"], "updated": _cache_data["updated"]})

# --------------------- Simple UI (served at / and /ui) ----------------------

HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Purdue Men's Basketball — Live Feed</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  :root { --fg:#111; --muted:#666; --bg:#fff; --chip:#f2f4f7; }
  body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 32px; color: var(--fg); background: var(--bg); }
  header { display:flex; align-items:center; gap:14px; flex-wrap:wrap; margin-bottom: 18px; }
  header img { height: 36px; width: 36px; object-fit: contain; }
  h1 { font-weight: 700; margin: 0; }
  .row { display:flex; gap:12px; flex-wrap:wrap; margin: 14px 0 22px; }
  input[type="search"] { flex:1; min-width: 260px; padding:10px 12px; border:1px solid #ddd; border-radius:8px; }
  select { padding:10px 12px; border:1px solid #ddd; border-radius:8px; }
  .meta { color: var(--muted); font-size: 12px; }
  .card { border:1px solid #eee; border-radius:12px; padding:14px 14px; margin: 10px 0; }
  .card a.title { font-weight: 600; text-decoration: none; }
  .src { display:inline-block; font-size:12px; background: var(--chip); padding:4px 8px; border-radius:999px; margin-left: 8px; }
  .bar { display:flex; gap:8px; align-items:center; margin:10px 0 18px; }
  .btn { border:1px solid #ddd; background:white; border-radius:8px; padding:6px 10px; cursor:pointer; }
</style>
</head>
<body>
  <header>
    <img src="/static/logo.png" onerror="this.style.display='none'">
    <h1>Purdue Men's Basketball — Live Feed</h1>
    <span id="time" class="meta"></span>
  </header>

  <div class="bar">
    <button id="refresh" class="btn">Force Refresh</button>
    <button id="fresh" class="btn">Load Fresh (no cache)</button>
    <a class="meta" href="/api/debug" target="_blank" rel="noopener">debug</a>
  </div>

  <div class="row">
    <input id="q" type="search" placeholder="Filter by keyword (e.g., 'Painter', 'Braden Smith')" />
    <select id="src"></select>
  </div>

  <div id="list"></div>

<script>
const $ = (s) => document.querySelector(s);
const list = $("#list"), q = $("#q"), src = $("#src"), timeSpan=$("#time");

function fmtTime(ts){
  if(!ts) return "";
  const d = new Date(ts*1000);
  return "Loaded " + d.toLocaleString();
}

function render(data){
  timeSpan.textContent = fmtTime(data.updated);
  const sources = ["All sources", ...Array.from(new Set(data.items.map(i=>i.source)))];
  src.innerHTML = sources.map((s,i)=>`<option value="${s}">${s}</option>`).join("");
  draw(data.items);
}

function draw(items){
  const term = q.value.trim().toLowerCase();
  const chosen = src.value;
  const fil = items.filter(i=>{
    const t = (i.title+" "+(i.summary||"")).toLowerCase();
    const hit = !term || t.includes(term);
    const sOK = (chosen==="All sources" || chosen==="" || i.source===chosen);
    return hit && sOK;
  });
  list.innerHTML = fil.map(i=>`
    <div class="card">
      <a class="title" href="${i.link}" target="_blank" rel="noopener">${i.title}</a>
      <span class="src">${i.source}</span>
      <div class="meta">${i.published||""}</div>
      <div>${(i.summary||"").slice(0,200)}</div>
    </div>
  `).join("");
}

async function loadCached(){
  const r = await fetch("/api/news");
  const j = await r.json();
  render(j);
}

async function loadFresh(){
  await fetch("/api/refresh-now", {method:"POST"});
  await loadCached();
}

$("#refresh").onclick = loadFresh;
$("#fresh").onclick = loadFresh;
q.oninput = ()=>loadCached().then(()=>draw(JSON.parse(sessionStorage.last || "{}").items||[]));
src.onchange = ()=>loadCached();

loadCached();
</script>
</body>
</html>
"""

@app.get("/")
@app.get("/ui")
def ui():
    return Response(HTML, mimetype="text/html")
