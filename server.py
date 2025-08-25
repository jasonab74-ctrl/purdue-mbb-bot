# server.py
from __future__ import annotations
import json
from pathlib import Path
from flask import Flask, Response, request, jsonify

# IMPORTANT: use the collector inside the app package
from app import collect

APP = Flask(__name__)
DATA_PATH = Path("data/news.json")

HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Purdue Men's Basketball — Live Feed</title>
  <style>
    :root {
      --bg:#fafafa; --card:#fff; --text:#0f172a; --sub:#6b7280; --border:#e5e7eb;
      --chip:#eef2ff; --chip-text:#3730a3; --btn:#0b1220;
    }
    *{box-sizing:border-box}
    body{margin:0;background:var(--bg);color:var(--text);font:16px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial}
    .wrap{max-width:1080px;margin:22px auto 60px;padding:0 16px}
    .header{display:flex;align-items:center;gap:16px;flex-wrap:wrap}
    .logo{width:52px;height:52px}
    .logo img{width:100%;height:auto;display:block}
    h1{font-size:clamp(22px,3.6vw,36px);margin:0;font-weight:800;letter-spacing:-.02em;line-height:1.1}
    .right{margin-left:auto;display:flex;gap:10px;align-items:center}
    .btn{background:var(--btn);color:#fff;border:0;border-radius:10px;padding:10px 14px;font-weight:700;cursor:pointer}
    .controls{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:12px 0}
    input[type="search"],select{border:1px solid var(--border);background:#fff;border-radius:10px;padding:12px}
    input[type="search"]{flex:1 1 520px}
    .quicklinks{display:flex;flex-wrap:wrap;gap:12px;margin:14px 0}
    .quicklinks a{display:inline-block;background:#fff;border:1px solid var(--border);padding:8px 12px;border-radius:999px;text-decoration:none;color:#1f3aff;font-weight:600}
    .quicklinks a:hover{background:#f3f4f6}
    .loaded{color:var(--sub);font-size:13px;margin:8px 0 10px}
    .list{display:grid;gap:10px} /* tighter spacing */
    .card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:12px}
    .meta{color:var(--sub);font-size:13px;margin-bottom:6px;display:flex;gap:6px;align-items:center;flex-wrap:wrap}
    .source{background:var(--chip);color:var(--chip-text);padding:2px 8px;border-radius:999px;font-weight:700}
    .title{font-weight:800;font-size:18px;text-decoration:none;color:#111827}
    .title:hover{text-decoration:underline}
    @media (max-width:520px){.logo{width:44px;height:44px}.title{font-size:17px}}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="header">
      <div class="logo"><img alt="Purdue P" src="https://upload.wikimedia.org/wikipedia/commons/6/68/Purdue_Boilermakers_logo.svg"></div>
      <h1>Purdue Men's Basketball — Live Feed</h1>
      <div class="right">
        <button id="refresh" class="btn">Force Refresh</button>
        <a href="/api/debug" target="_blank" rel="noopener" style="text-decoration:none;color:#1f3aff;font-weight:600">debug</a>
      </div>
    </div>

    <!-- 🔗 Quick Links (all six) -->
    <div class="quicklinks">
      <a href="https://purduesports.com/sports/mens-basketball" target="_blank" rel="noopener">Official MBB</a>
      <a href="https://purduesports.com/sports/mens-basketball/schedule" target="_blank" rel="noopener">Schedule</a>
      <a href="https://purduesports.com/sports/mens-basketball/roster" target="_blank" rel="noopener">Roster</a>
      <a href="https://www.hammerandrails.com/mens-basketball" target="_blank" rel="noopener">Hammer & Rails</a>
      <a href="https://www.reddit.com/r/Boilermakers/" target="_blank" rel="noopener">Reddit r/Boilermakers</a>
      <a href="https://www.reddit.com/r/PurdueBasketball/" target="_blank" rel="noopener">Reddit r/PurdueBasketball</a>
    </div>

    <div class="controls">
      <input id="q" type="search" placeholder="Filter by keyword (e.g., 'Painter', 'Braden Smith')" />
      <select id="src"><option value="">All sources</option></select>
    </div>

    <div id="loaded" class="loaded">Loaded …</div>
    <div id="list" class="list"></div>
  </div>

  <script>
    const $ = s => document.querySelector(s);
    const list = $("#list"), q = $("#q"), src = $("#src"), loaded = $("#loaded"), btn = $("#refresh");
    let DATA = {items:[], updated_ts:null};

    function tsPretty(ts){ if(!ts) return ""; return new Date(ts*1000).toLocaleString(); }

    function render(items){
      list.innerHTML = "";
      items.forEach(it=>{
        const card = document.createElement("div"); card.className="card";
        const meta = document.createElement("div"); meta.className="meta";
        const chip = document.createElement("span"); chip.className="source"; chip.textContent = it.source || "RSS";
        const dot = document.createElement("span"); dot.textContent = "•";
        const when = document.createElement("time"); when.textContent = it.published_ts ? new Date(it.published_ts*1000).toLocaleString() : "";
        meta.append(chip,dot,when);

        const a = document.createElement("a");
        a.className="title"; a.href = it.link || "#"; a.target="_blank"; a.rel="noopener";
        a.textContent = it.title || "(untitled)";

        // Only title + meta (no summaries/verbiage)
        card.append(meta,a);
        list.append(card);
      });
    }

    function applyFilters(){
      const t = q.value.trim().toLowerCase();
      const only = src.value;
      const items = (DATA.items||[]).filter(it=>{
        const okSrc = !only || it.source===only;
        const txt = (it.title||"");
        const okText = !t || txt.toLowerCase().includes(t);
        return okSrc && okText;
      });
      render(items);
    }

    async function load(){
      const r = await fetch("/api/news",{cache:"no-store"});
      const json = await r.json();
      DATA = json || {items:[]};
      loaded.textContent = "Loaded "+(DATA.updated_ts?tsPretty(DATA.updated_ts):"");
      const uniques = Array.from(new Set((DATA.items||[]).map(i=>i.source).filter(Boolean))).sort();
      src.innerHTML = '<option value="">All sources</option>'+uniques.map(s=>`<option>${s}</option>`).join("");
      applyFilters();
    }

    async function forceRefresh(){
      btn.disabled = true;
      try{ await fetch("/api/refresh-now",{method:"POST"}); }catch(e){}
      await load();
      btn.disabled = false;
    }

    q.addEventListener("input", applyFilters);
    src.addEventListener("change", applyFilters);
    btn.addEventListener("click", forceRefresh);
    document.addEventListener("DOMContentLoaded", load);
  </script>
</body>
</html>"""

@APP.get("/")
def home():
    return Response(HTML, mimetype="text/html")

@APP.get("/api/news")
def api_news():
    if not DATA_PATH.exists():
        payload = collect.collect_all()
        return jsonify(payload)
    return Response(DATA_PATH.read_text(encoding="utf-8"), mimetype="application/json")

@APP.post("/api/refresh-now")
def refresh_now():
    payload = collect.collect_all()
    return jsonify({"ok": True, "count": payload.get("count", 0), "updated_ts": payload.get("updated_ts")})

@APP.get("/api/debug")
def debug():
    info = {"data_path": str(DATA_PATH.resolve()), "exists": DATA_PATH.exists(), "size_bytes": DATA_PATH.stat().st_size if DATA_PATH.exists() else 0}
    return jsonify(info)

if __name__ == "__main__":
    APP.run(host="0.0.0.0", port=8000, debug=False)
