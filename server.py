from __future__ import annotations
import os, time
from flask import Flask, jsonify, request, Response
from flask_cors import CORS
from collect import collect_all, collect_debug

app = Flask(__name__, static_folder="static")
CORS(app)

CACHE_TTL = int(os.getenv("CACHE_TTL", "300"))  # seconds
_cache = {"items": [], "stats": {}, "fetched_at": 0}

def _stale() -> bool:
    return (time.time() - (_cache["fetched_at"] or 0)) > CACHE_TTL

def _refresh_cache() -> None:
    global _cache
    data = collect_all()
    _cache = {
        "items": data["items"],
        "stats": data["stats"],
        "fetched_at": time.time(),
    }

@app.get("/api/news")
def api_news():
    """
    Returns cached news by default. Pass ?nocache=1 to force a fresh scrape for
    THIS request only (still updates cache).
    """
    nocache = request.args.get("nocache") == "1"
    if nocache or _stale() or not _cache["items"]:
        _refresh_cache()
    return jsonify({
        "items": _cache["items"],
        "stats": _cache["stats"],
        "fetched_at": _cache["fetched_at"],
        "ttl": CACHE_TTL,
    })

@app.post("/api/refresh-now")
def api_refresh_now():
    """
    Synchronous refresh (quick—uses tight timeouts).
    """
    _refresh_cache()
    return jsonify({"ok": True, "count": len(_cache["items"]), "fetched_at": _cache["fetched_at"]})

@app.get("/api/debug")
def api_debug():
    dbg = collect_debug()
    # include cache header info too
    dbg["cache"] = {
        "count": len(_cache["items"]),
        "fetched_at": _cache["fetched_at"],
        "stale": _stale(),
        "ttl": CACHE_TTL,
    }
    return jsonify(dbg)

# ---------- Very small front-end ----------
HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Purdue Men's Basketball — Live Feed</title>
  <link rel="icon" href="/static/logo.png">
  <style>
    :root { --text:#111; --muted:#666; --chip:#eef2ff; --border:#e5e7eb; --bg:#fafafa; }
    * { box-sizing: border-box; }
    body { margin: 0; font: 16px/1.4 system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; color: var(--text); background: var(--bg); }
    header { display:flex; gap:12px; align-items:center; padding:18px 20px; border-bottom:1px solid var(--border); background:#fff; position:sticky; top:0; z-index:1;}
    header img { width:36px; height:36px; border-radius:6px; object-fit:contain; }
    header h1 { font-size:22px; margin:0; font-weight:750; }
    .controls { display:flex; gap:8px; margin-left:auto; }
    button { border:1px solid var(--border); background:#fff; padding:8px 12px; border-radius:10px; cursor:pointer; }
    button:hover { background:#f3f4f6; }
    main { max-width:1100px; margin: 16px auto; padding: 0 16px 40px; }
    .filters { display:flex; gap:8px; margin: 10px 0 16px; }
    input, select { width:100%; padding:10px 12px; border:1px solid var(--border); border-radius:10px; background:#fff; }
    select { max-width:220px; }
    .meta { color:var(--muted); font-size:13px; margin-bottom:10px; }
    .card { background:#fff; border:1px solid var(--border); border-radius:14px; padding:14px; margin-bottom:10px; }
    .title { font-weight:700; margin:0 0 8px; }
    .row { display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
    .chip { background: var(--chip); border:1px solid #c7d2fe; color:#1e40af; padding:2px 8px; border-radius:999px; font-size:12px; }
    .src { color:var(--muted); font-size:13px; }
    .hidden { display:none; }
  </style>
</head>
<body>
  <header>
    <img src="/static/logo.png" alt="Purdue logo" onerror="this.style.display='none'">
    <h1>Purdue Men's Basketball — Live Feed</h1>
    <div class="controls">
      <button id="btnRefresh">Force Refresh</button>
      <button id="btnFresh">Load Fresh (no cache)</button>
      <a href="/api/debug" target="_blank" style="align-self:center;color:#2563eb;">debug</a>
    </div>
  </header>

  <main>
    <div class="filters">
      <input id="kw" placeholder="Filter by keyword (e.g., 'Painter', 'Braden Smith')" />
      <select id="src">
        <option value="">All sources</option>
        <option value="Google News">Google News</option>
        <option value="Reddit">Reddit</option>
      </select>
    </div>
    <div id="meta" class="meta"></div>
    <div id="list"></div>
  </main>

  <script>
    const $ = (s)=>document.querySelector(s);
    const list = $("#list"), meta=$("#meta"), kw=$("#kw"), src=$("#src");

    function render(data){
      const q = kw.value.trim().toLowerCase();
      const s = src.value;
      const items = (data.items || []).filter(x=>{
        const okSrc = !s || x.source === s;
        const text = (x.title+" "+(x.summary||"")).toLowerCase();
        const okQ = !q || text.includes(q);
        return okSrc && okQ;
      });
      meta.textContent = `${items.length} items — fetched ${new Date(data.fetched_at*1000).toLocaleString()}`;
      list.innerHTML = items.map(x=>`
        <div class="card">
          <div class="row" style="justify-content:space-between">
            <a class="title" href="${x.link}" target="_blank" rel="noopener">${x.title}</a>
            <span class="chip">${x.source}</span>
          </div>
          <div class="src">${x.published || ""}</div>
          <div>${x.summary || ""}</div>
        </div>`).join("") || "<div class='meta'>No results.</div>";
    }

    async function load(nocache){
      list.innerHTML = "<div class='meta'>Loading…</div>";
      const url = "/api/news"+(nocache?"?nocache=1":"");
      const r = await fetch(url);
      render(await r.json());
    }

    $("#btnFresh").onclick = ()=>load(true);
    $("#btnRefresh").onclick = async ()=>{
      await fetch("/api/refresh-now", {method:"POST"});
      load(false);
    };
    kw.oninput = ()=>load(false);
    src.onchange = ()=>load(false);

    load(false);
  </script>
</body>
</html>
"""

@app.get("/")
def ui():
    return Response(HTML, mimetype="text/html")


if __name__ == "__main__":
    # local dev: python server.py
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "10000")), debug=True)
