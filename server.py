# server.py — ROOT file only. No /app involved.
# Clean HTML (NOT an f-string), working API, refresh endpoint, fight song, and diagnostics.

import json
import os
import subprocess
import time
from pathlib import Path
from flask import Flask, jsonify, request, Response, send_from_directory, abort

app = Flask(__name__, static_folder="static", static_url_path="/static")

# ---------------------------------
# Config you already use
# ---------------------------------
REFRESH_KEY = "mbb_refresh_6P7wP9dXr2Jq"  # same key you've been calling

# Try common data locations (works with your existing collect.py output)
DATA_CANDIDATES = [
    Path("data.json"),
    Path("items.json"),
    Path("data") / "items.json",
    Path("data") / "data.json",
]

def _items_path() -> Path | None:
    for p in DATA_CANDIDATES:
        if p.exists():
            return p
    return None

def _read_items() -> list:
    p = _items_path()
    if not p:
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []

def _last_mod_iso() -> str | None:
    p = _items_path()
    if not p:
        return None
    try:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(p.stat().st_mtime))
    except Exception:
        return None

# ---------------------------------
# HTML (NOTE: no f-string, no .format)
# ---------------------------------
INDEX_HTML = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>Purdue Men's Basketball News</title>
<link rel="icon" href="/static/logo.png" />
<link rel="apple-touch-icon" href="/static/logo.png" />
<meta name="theme-color" content="#cfb87c" />
<meta property="og:type" content="website" />
<meta property="og:site_name" content="Purdue MBB News" />
<meta property="og:title" content="Purdue MBB News" />
<meta property="og:description" content="Fast, clean Purdue men’s basketball feed." />
<meta property="og:image" content="/static/logo.png" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="Purdue MBB News" />
<meta name="twitter:description" content="Fast, clean Purdue men’s basketball feed." />
<meta name="twitter:image" content="/static/logo.png" />
<style>
  :root{
    --bg:#f6f4ef; --card:#fff; --ink:#111; --muted:#6b7280;
    --pill:#f1eee6; --border:#e7e2d6; --shadow:0 6px 20px rgba(0,0,0,.08);
  }
  *{box-sizing:border-box}
  body{margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial;color:var(--ink);background:var(--bg)}
  .wrap{max-width:980px;margin:0 auto}
  .header{position:sticky;top:0;z-index:50;background:var(--bg);padding:22px 14px;transition:padding .22s ease,box-shadow .22s ease;box-shadow:none}
  .header.shrink{padding:10px 14px;box-shadow:0 2px 18px rgba(0,0,0,.06)}
  .hero{background:var(--card);border:1px solid var(--border);border-radius:16px;box-shadow:var(--shadow);padding:16px;display:grid;grid-template-columns:auto 1fr;gap:14px;align-items:start}
  .logo{width:56px;height:56px;border-radius:14px;background:#f7f4e0;display:grid;place-items:center;overflow:hidden}
  .logo img{width:42px;height:42px;object-fit:contain}
  h1{margin:0;font-size:28px;line-height:1.2}
  .row{margin-top:12px;display:flex;flex-wrap:wrap;gap:10px;align-items:center}
  .pill{background:#111;color:#fff;padding:6px 12px;border-radius:999px;font-size:12px;letter-spacing:.04em}
  .updated{color:var(--muted);font-size:13px}
  .btn{background:var(--pill);padding:8px 14px;border-radius:999px;font-size:14px;color:#111;text-decoration:none;border:1px solid var(--border)}
  .btn:hover{filter:brightness(.98)}
  .site-dd{position:relative;display:inline-block}
  summary.btn{list-style:none;cursor:pointer}
  summary.btn::-webkit-details-marker{display:none}
  .sites{position:absolute;top:46px;left:0;background:var(--card);border:1px solid var(--border);border-radius:12px;box-shadow:var(--shadow);padding:8px;min-width:240px}
  .sites a{display:block;padding:10px 12px;border-radius:8px;color:#111;text-decoration:none;font-size:14px}
  .sites a:hover{background:#f6f2e8}
  .searchRow{margin-top:10px;display:flex;gap:10px;align-items:center}
  .search{flex:1;background:var(--pill);border:1px solid var(--border);border-radius:999px;padding:10px 14px;font-size:15px}
  .count{color:var(--muted);font-size:12px}
  .list{max-width:980px;margin:16px auto;padding:0 14px 28px;display:grid;gap:12px}
  .card{background:var(--card);border:1px solid var(--border);border-radius:16px;box-shadow:var(--shadow);padding:14px 16px}
  .meta{color:var(--muted);font-size:12px;display:flex;gap:10px;align-items:center}
  .source{font-weight:700;color:#222}
  .title{margin:6px 0 4px;font-size:17px;font-weight:800;line-height:1.3;color:#111;text-decoration:none;display:block}
  .desc{color:#444;font-size:14px}
  .empty{text-align:center;color:var(--muted);padding:40px 0}
  @media(max-width:560px){h1{font-size:24px}}
</style>
</head>
<body>
  <header class="header" id="hdr">
    <div class="wrap">
      <div class="hero">
        <div class="logo"><img src="/static/logo.png" alt="Purdue"></div>
        <div>
          <h1>Purdue Men's Basketball News</h1>
          <div class="row">
            <span class="pill">CURATED &amp; DE-CLUTTERED</span>
            <span class="updated">Updated: <span id="updated">…</span></span>
          </div>
          <div class="row" style="margin-top:10px">
            <a class="btn" href="https://www.hammerandrails.com/purdue-basketball" target="_blank" rel="noopener">H&amp;R</a>
            <a class="btn" href="https://www.espn.com/mens-college-basketball/team/_/id/2509/purdue-boilermakers" target="_blank" rel="noopener">ESPN</a>
            <a class="btn" href="https://www.on3.com/teams/purdue-boilermakers/" target="_blank" rel="noopener">GoldandBlack</a>
            <a class="btn" href="https://purduesports.com/sports/mens-basketball/schedule" target="_blank" rel="noopener">Schedule</a>
            <a class="btn" href="https://purduesports.com/sports/mens-basketball/roster" target="_blank" rel="noopener">Roster</a>
            <a class="btn" href="https://www.reddit.com/r/Boilermakers/" target="_blank" rel="noopener">Reddit</a>

            <details class="site-dd">
              <summary class="btn">More Sites</summary>
              <div class="sites">
                <a href="https://www.barstoolsports.com/topics/college-basketball" target="_blank" rel="noopener">Barstool (CBB)</a>
                <a href="https://sports.yahoo.com/college-basketball/" target="_blank" rel="noopener">Yahoo Sports (CBB)</a>
                <a href="https://www.si.com/college/purdue" target="_blank" rel="noopener">SI Purdue</a>
              </div>
            </details>
          </div>
          <div class="searchRow">
            <input id="q" class="search" placeholder="Search news (e.g., Edey, Field of 68)" />
            <span class="count"><span id="n">0</span> results</span>
            <button id="fightBtn" class="btn" type="button" title="Play the Purdue Fight Song">🎵 Fight Song</button>
          </div>
        </div>
      </div>
    </div>
  </header>

  <main class="list" id="list"></main>

  <audio id="fightAudio" src="/fight.mp3" preload="auto"></audio>

<script>
(function(){
  // Smooth header shrink
  const hdr = document.getElementById('hdr');
  let ticking = false;
  function applyShrink(){
    const y = window.scrollY || 0;
    if (y > 40) hdr.classList.add('shrink'); else if (y < 10) hdr.classList.remove('shrink');
    ticking = false;
  }
  window.addEventListener('scroll', ()=>{ if(!ticking){ requestAnimationFrame(applyShrink); ticking=true; }});
  applyShrink();

  const listEl = document.getElementById('list');
  const q = document.getElementById('q');
  const n = document.getElementById('n');
  const updatedEl = document.getElementById('updated');

  let ALL = [];

  function clean(s){
    if(!s) return "";
    const t=document.createElement('textarea'); t.innerHTML=String(s); const dec=t.value;
    const doc=new DOMParser().parseFromString(dec,"text/html");
    return (doc.body?doc.body.textContent:"").replace(/\s+/g," ").trim();
  }

  function render(items){
    listEl.innerHTML="";
    if(!items.length){ listEl.innerHTML='<div class="empty">No results. Try another search.</div>'; n.textContent='0'; return; }
    n.textContent=String(items.length);
    items.forEach(it=>{
      const src=it.source||it.site||"";
      const when=it.published||it.date||"";
      const title=it.title||"(untitled)";
      const url=it.link||"#";
      const desc=clean(it.summary_text || it.summary || it.description || "");

      const card=document.createElement('article');
      card.className="card";
      card.innerHTML = `
        <div class="meta"><span class="source">${src}</span><span>·</span><span>${when}</span></div>
        <a class="title" href="${url}" target="_blank" rel="noopener">${title}</a>
        ${desc ? `<div class="desc">${desc.length>220?desc.slice(0,220)+'…':desc}</div>` : ""}
      `;
      listEl.appendChild(card);
    });
  }

  function filterNow(){
    const v=(q.value||"").trim().toLowerCase();
    if(!v){ render(ALL); return; }
    const words=v.split(/\s+/).filter(Boolean);
    const out=ALL.filter(it=>{
      const hay=((it.title||"")+" "+(it.summary_text||it.summary||"")+" "+(it.source||"")).toLowerCase();
      return words.every(w=>hay.includes(w));
    });
    render(out);
  }
  q.addEventListener('input', filterNow);

  async function load(){
    try{
      const items = await fetch('/api/items').then(r=>r.json());
      ALL = Array.isArray(items)? items : [];
      render(ALL);
    }catch(e){ ALL=[]; render(ALL); }
    try{
      const m = await fetch('/api/last-mod').then(r=>r.json());
      if(m && m.modified) updatedEl.textContent = m.modified;
    }catch(e){}
  }
  load();
  setInterval(load, 5*60*1000);

  // Fight song button
  const fightBtn = document.getElementById('fightBtn');
  const fightAudio = document.getElementById('fightAudio');
  function syncFight(){
    if(!fightAudio) return;
    const on = !fightAudio.paused;
    fightBtn.textContent = on ? "⏸ Fight Song" : "🎵 Fight Song";
  }
  if(fightBtn && fightAudio){
    fightBtn.addEventListener('click', async ()=>{
      try{
        if(fightAudio.paused){ fightAudio.currentTime=0; fightAudio.volume=.7; await fightAudio.play(); }
        else { fightAudio.pause(); }
      }catch(e){}
    });
    ['play','playing','pause','ended','error'].forEach(ev=>fightAudio.addEventListener(ev, syncFight));
    syncFight();
  }
})();
</script>
</body>
</html>
"""

# ---------------------------
# Routes (ROOT only)
# ---------------------------

@app.get("/")
def home():
    return Response(INDEX_HTML, mimetype="text/html")

@app.get("/api/items")
def api_items():
    return jsonify(_read_items())

@app.get("/api/last-mod")
def api_last_mod():
    return jsonify({"modified": _last_mod_iso()})

@app.route("/api/refresh-now", methods=["GET","POST"])
def api_refresh_now():
    key = request.args.get("key") or request.headers.get("X-Refresh-Key") or request.form.get("key")
    if key != REFRESH_KEY:
        return jsonify({"ok": False, "error": "forbidden"}), 403
    try:
        # kick off collect.py without blocking
        subprocess.Popen(["python", "collect.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.get("/fight.mp3")
def fight_song():
    # expects file at ./static/fight.mp3
    path = Path(app.static_folder) / "fight.mp3"
    if path.exists():
        return send_from_directory(app.static_folder, "fight.mp3", mimetype="audio/mpeg", conditional=True)
    abort(404)

# Diagnostics to prove we're using ROOT server.py and to inspect static
@app.get("/__where")
def where():
    return "USING root/server.py"

@app.get("/__debug")
def debug():
    static_dir = Path(app.static_folder)
    try:
        files = sorted([p.name for p in static_dir.iterdir()]) if static_dir.exists() else []
    except Exception:
        files = []
    return jsonify({
        "cwd": str(Path.cwd()),
        "using_root_server_py": True,
        "static_dir": str(static_dir.resolve()),
        "fight_exists": (static_dir / "fight.mp3").exists(),
        "static_files": files[:200],
        "data_candidates": [str(p) for p in DATA_CANDIDATES],
        "chosen_data_file": str(_items_path()) if _items_path() else None,
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
