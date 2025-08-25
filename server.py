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
    :root { --bg:#fafafa; --card:#fff; --text:#111827; --sub:#6b7280; --brand:#0f172a; --chip:#eef2ff; --chip-text:#3730a3; --border:#e5e7eb; --accent:#cfb991; }
    *{box-sizing:border-box}
    html,body{margin:0;padding:0;background:var(--bg);color:var(--text);font:16px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,"Apple Color Emoji","Segoe UI Emoji"}
    .wrap{max-width:1080px;margin:24px auto 56px;padding:0 16px}
    .header{display:flex;align-items:center;gap:18px;margin-bottom:14px}
    .logo{width:54px;height:54px;flex:0 0 54px;display:flex;align-items:center;justify-content:center}
    .logo img{width:100%;height:auto;display:block}
    h1{font-size:clamp(22px,3.6vw,36px);line-height:1.1;margin:0;font-weight:800;letter-spacing:-.02em}
    .right{margin-left:auto;display:flex;gap:12px;align-items:center}
    .btn{background:#0b1220;color:#fff;border:0;padding:11px 14px;border-radius:10px;font-weight:600;cursor:pointer}

    .controls{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:14px 0 8px}
    input[type="search"]{flex:1 1 520px;padding:12px 14px;border:1px solid var(--border);border-radius:10px;background:#fff}
    select{padding:12px;border:1px solid var(--border);border-radius:10px;background:#fff}

    /* Quick links strip */
    .quicklinks{margin:10px 0 14px;padding:12px;border:1px solid var(--border);background:#fff;border-radius:12px}
    .quicklinks .title{font-weight:700;font-size:14px;color:var(--brand);margin:0 0 8px}
    .quicklinks .links{display:flex;flex-wrap:wrap;gap:10px}
    .quicklinks a{display:inline-block;text-decoration:none;border:1px solid var(--border);background:#f8fafc;padding:8px 10px;border-radius:999px;font-weight:600}
    .quicklinks a:hover{background:#eef2ff;border-color:#dbeafe}

    .meta{color:var(--sub);font-size:13px;margin:4px 0 10px;display:flex;align-items:center;gap:6px;flex-wrap:wrap}
    .source{background:var(--chip);color:var(--chip-text);padding:2px 8px;border-radius:999px;font-weight:600}
    .list{display:grid;gap:14px;margin-top:8px}
    .card{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:14px}
    .card a.title{font-weight:700;font-size:18px;text-decoration:none;color:var(--brand);display:inline-block}
    .card a.title:hover{text-decoration:underline}
    .loaded{color:var(--sub);font-size:13px;margin:12px 0}
    .tools a{color:#1f3aff;text-decoration:none}
    .tools a:hover{text-decoration:underline}
    @media (max-width:520px){.logo{width:46px;height:46px;flex-basis:46px}.btn{padding:10px 12px}.card a.title{font-size:17px}.quicklinks .links{gap:8px}}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="header">
      <div class="logo"><img alt="Purdue P" src="https://upload.wikimedia.org/wikipedia/commons/thumb/6/68/Purdue_Boilermakers_logo.svg/120px-Purdue_Boilermakers_logo.svg.png" /></div>
      <h1>Purdue Men's Basketball — Live Feed</h1>
      <div class="right">
        <button id="refresh" class="btn">Force Refresh</button>
        <span class="tools"><a href="/api/debug" target="_blank" rel="noopener">debug</a></span>
      </div>
    </div>

    <!-- Static Quick links (your request) -->
    <div class="quicklinks" aria-label="Reference links">
      <p class="title">Quick links</p>
      <div class="links">
        <a href="https://www.reddit.com/r/PurdueBasketball/" target="_blank" rel="noopener">r/PurdueBasketball</a>
        <a href="https://www.reddit.com/r/Boilermakers/" target="_blank" rel="noopener">r/Boilermakers</a>
        <a href="https://www.hammerandrails.com/mens-basketball" target="_blank" rel="noopener">Hammer &amp; Rails — MBB</a>
      </div>
    </div>

    <div class="controls">
      <input id="q" type="search" placeholder="Filter by keyword (e.g., 'Painter', 'Braden Smith')" />
      <select id="src"><option value="">All sources</option></select>
    </div>

    <div id="loaded" class="loaded">Loaded …</div>
    <div id="list" class="list"></div>
  </div>

  <script>
    const $ = (sel) => document.querySelector(sel);
    const list = $("#list"), q = $("#q"), src = $("#src"), loaded = $("#loaded"), refreshBtn = $("#refresh");
    let DATA = { items: [], updated_ts: null };

    function fmtTime(ts){ if(!ts) return ""; const d=new Date(ts*1000); return d.toLocaleString(); }

    // Render WITHOUT any snippet (removes the messy <a href> text entirely)
    function render(items){
      list.innerHTML = "";
      items.forEach(it=>{
        const card=document.createElement("div"); card.className="card";

        const meta=document.createElement("div"); meta.className="meta";
        const chip=document.createElement("span"); chip.className="source"; chip.textContent=it.source||"RSS";
        const dot=document.createElement("span"); dot.textContent="•";
        const when=document.createElement("time"); when.textContent = it.published_ts ? new Date(it.published_ts*1000).toLocaleString() : (it.published||"");
        meta.append(chip,dot,when);

        const a=document.createElement("a"); a.className="title"; a.href=it.link||"#"; a.target="_blank"; a.rel="noopener"; a.textContent=it.title||"(untitled)";

        card.append(meta,a);
        list.append(card);
      });
    }

    function applyFilters(){
      const term=q.value.trim().toLowerCase(), only=src.value;
      const items=(DATA.items||[]).filter(it=>{
        const okSrc=!only||(it.source===only);
        const inText=!term||((it.title||"").toLowerCase().includes(term));
        return okSrc && inText;
      });
      render(items);
    }

    async function load(){
      const r=await fetch("/api/news",{cache:"no-store"}); const json=await r.json(); DATA=json||{items:[]};
      loaded.textContent="Loaded "+(DATA.updated_ts?fmtTime(DATA.updated_ts):"");
      const unique=Array.from(new Set((DATA.items||[]).map(i=>i.source).filter(Boolean))).sort();
      src.innerHTML='<option value="">All sources</option>'+unique.map(s=>`<option>${s}</option>`).join("");
      applyFilters();
    }

    async function forceRefresh(){ refreshBtn.disabled=true; try{ await fetch("/api/refresh-now",{method:"POST"}); }catch{} await load(); refreshBtn.disabled=false; }

    q.addEventListener("input",applyFilters); src.addEventListener("change",applyFilters); refreshBtn.addEventListener("click",forceRefresh);
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
