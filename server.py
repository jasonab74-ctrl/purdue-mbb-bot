# server.py
from flask import Flask, jsonify, Response
import json, time
import collect  # must be in the same folder

app = Flask(__name__)
CACHE = {"data": None, "updated": 0}

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
    .list{display:grid;gap:10px}
    .card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:12px}
    .meta{color:var(--sub);font-size:13px;margin-bottom:6px;display:flex;gap:6px;align-items:center;flex-wrap:wrap}
    .source{background:var(--chip);color:var(--chip-text);padding:2px 8px;border-radius:999px;font-weight:700}
    .title{font-weight:800;font-size:18px;text-decoration:none;color:#111827}
    .title:hover{text-decoration:underline}
    /* If any snippet sneaks in, do not display it */
    .card p, .card .snippet { display:none !important; }
    @media (max-width:520px){.logo{width:44px;height:44px}.title{font-size:17px}}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="header">
      <div class="logo"><img alt="Purdue P" src="https://upload.wikimedia.org/wikipedia/commons/6/68/Purdue_Boilermakers_logo.svg"></div>
      <h1>Purdue Men's Basketball — Live Feed <span style="font-weight:600;color:#6b7280;font-size:12px;">vQL6</span></h1>
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

        // Only title + meta (no summaries)
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

def _collect_cached():
    now = int(time.time())
    if (not CACHE["data"]) or now - CACHE["updated"] > 900:
        CACHE["data"] = collect.collect_all()
        CACHE["updated"] = now
    return CACHE["data"]

@app.get("/")
def index():
    # No-cache so you don't get a stale HTML bundle
    resp = Response(HTML, mimetype="text/html")
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp

@app.get("/api/news")
def api_news():
    data = _collect_cached()
    items = []
    for it in data.get("items", []):
        items.append({
            "title": it.get("title"),
            "link": it.get("link"),
            "source": it.get("source"),
            "published_ts": it.get("published_ts"),
            # Back-compat: deliberately blank so old UIs can't show messy HTML
            "summary": "",
            "summary_text": "",
        })
    out = {"items": items, "updated_ts": data.get("updated", int(time.time()))}
    return jsonify(out)

@app.post("/api/refresh-now")
def api_refresh_now():
    CACHE["data"] = collect.collect_all()
    CACHE["updated"] = int(time.time())
    return jsonify({"ok": True, "updated_ts": CACHE["updated"], "count": CACHE["data"].get("count", 0)})

@app.get("/api/debug")
def api_debug():
    data = _collect_cached()
    sample = data.get("items", [])[:3]
    obj = {
        "by_source": {s["name"]: s.get("fetched", 0) for s in data.get("sources", [])},
        "example": sample,
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(CACHE["updated"])),
        "total": data.get("count", 0),
    }
    return Response(json.dumps(obj, ensure_ascii=False), mimetype="application/json")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
