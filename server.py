#!/usr/bin/env python3
import os, json, subprocess
from flask import Flask, Response, request, send_from_directory

app = Flask(__name__, static_url_path="/static", static_folder="static")

# ---------------- API ----------------
@app.get("/api/items")
def api_items():
    try:
        with open("items.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = []
    return Response(json.dumps(data), mimetype="application/json")

@app.get("/api/last-mod")
def api_lastmod():
    try:
        with open("last_modified.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {"modified": "unknown"}
    return Response(json.dumps(data), mimetype="application/json")

@app.post("/api/refresh-now")
def api_refresh_now():
    expected = os.getenv("REFRESH_KEY", "")
    key = request.args.get("key", "")
    if not expected or key != expected:
        return Response(json.dumps({"ok": False}), status=403, mimetype="application/json")
    try:
        subprocess.check_call(["python", "collect.py"])
        return Response(json.dumps({"ok": True}), mimetype="application/json")
    except Exception as e:
        return Response(json.dumps({"ok": False, "err": str(e)}), status=500, mimetype="application/json")

# ---------------- UI ----------------
HTML = r"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"/>
<title>Purdue Men's Basketball News</title>
<link rel="icon" href="/static/logo.png">
<style>
:root{
  --bg:#f6f3ec; --card:#ffffff; --ink:#1f1f1f; --muted:#6c6c6c;
  --pill:#f1ede3; --pill-dot:#c19a00; --border:rgba(0,0,0,.08);
  --gold:#f5d87c; --gold-ink:#16130a;
}
*{box-sizing:border-box}
html,body{height:100%}
body{
  margin:0;
  font:16px/1.45 -apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Inter,Helvetica,Arial;
  color:var(--ink); background:var(--bg);
  -webkit-font-smoothing:antialiased; -moz-osx-font-smoothing:grayscale;
}
a{color:inherit;text-decoration:none}

.header{position:sticky; top:0; z-index:10; background:var(--bg);
  transition:all .25s ease; border-bottom:1px solid transparent;}
.header.shrink{box-shadow:0 8px 30px -12px rgba(0,0,0,.25); border-bottom-color:var(--border)}

.wrap{max-width:950px; margin:0 auto; padding:14px}
.card{background:var(--card); border-radius:16px; box-shadow:0 6px 30px rgba(0,0,0,.06); border:1px solid var(--border)}

.top{display:flex; gap:14px; align-items:center; padding:10px 12px}
.logo{width:40px; height:40px; border-radius:10px; background:#f5d87c url('/static/logo.png') center/70% no-repeat; border:1px solid var(--border)}
.h1{font-weight:800; font-size:22px; line-height:1.15; letter-spacing:-.2px}
.badge{display:inline-flex; gap:8px; align-items:center; background:#111; color:#fff; border-radius:999px; padding:.28rem .65rem; font-size:.8rem}
.metaTop{margin-left:auto; color:var(--muted); font-size:.86rem; white-space:nowrap}

/* chip row */
.pills{display:flex; gap:10px; align-items:center; padding:0 12px 10px 12px; overflow-x:auto; overflow-y:visible}
.pills::-webkit-scrollbar{display:none}
.pill{display:inline-flex; gap:10px; align-items:center; background:var(--pill);
  padding:.6rem .9rem; border-radius:999px; border:1px solid var(--border); white-space:nowrap}
.btn{cursor:pointer; background:#fff}
.dot{width:8px;height:8px;border-radius:50%;background:var(--pill-dot)}

/* fight song distinct */
.songBtn{background:var(--gold); color:var(--gold-ink); font-weight:700; border-color:#dfc35f;
  box-shadow:0 2px 0 rgba(0,0,0,.06) inset}
.songBtn.playing{background:#111; color:#fff; border-color:#111}

/* controls */
.controls{display:flex; gap:10px; align-items:center; padding:0 12px 12px 12px}
.search{flex:1; border:1px solid var(--border); border-radius:12px; background:#fff; padding:.75rem .9rem; font-size:16px}
.count{color:var(--muted); font-size:12px}

/* list */
.list{display:flex; flex-direction:column; gap:12px; margin-top:12px}
.item{background:var(--card); border:1px solid var(--border); border-radius:14px; padding:12px 14px}
.meta{display:flex; gap:8px; align-items:center; font-size:.82rem; color:var(--muted); margin-bottom:6px; flex-wrap:wrap}
.source{font-weight:600; color:#444}
.title{font-weight:800; font-size:18px; line-height:1.25}
.sum{color:#474747; margin-top:6px; display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden}
.tag{margin-left:6px; font-size:.72rem; border:1px solid var(--border); border-radius:999px; padding:.1rem .45rem; background:#eef3ff}

/* ---------- Sites overlay ---------- */
.overlay{position:fixed; inset:0; background:rgba(0,0,0,.35);
  display:none; z-index:9999; align-items:center; justify-content:center; padding:16px;
  opacity:0; transition:opacity .15s ease}
.overlay.show{display:flex; opacity:1}
.sheet{background:#fff; border-radius:14px; border:1px solid var(--border);
  box-shadow:0 20px 40px rgba(0,0,0,.25);
  width:min(720px, 92vw); max-height:85vh; overflow:auto;
  transform:translateY(6px); transition:transform .18s ease}
.overlay.show .sheet{transform:translateY(0)}
.sheetHead{display:flex; align-items:center; justify-content:space-between; padding:14px 16px; border-bottom:1px solid var(--border)}
.sheetTitle{font-weight:800}
.xBtn{background:#f3f3f3; border:1px solid var(--border); border-radius:10px; padding:.4rem .6rem; cursor:pointer}
.links{display:grid; grid-template-columns:repeat(auto-fill,minmax(240px,1fr)); gap:10px; padding:14px 16px}
.links a{display:block; padding:.55rem .6rem; border:1px solid var(--border); border-radius:10px}
.links a:hover{background:#fafafa}

/* Mobile */
@media (max-width:680px){
  body{font-size:15px}
  .wrap{padding:10px}
  .card{border-radius:14px; box-shadow:0 4px 18px rgba(0,0,0,.06)}
  .top{padding:8px 10px}
  .logo{width:34px;height:34px;border-radius:8px}
  .h1{font-size:20px}
  .badge{font-size:.75rem; padding:.22rem .55rem}
  .metaTop{font-size:.78rem}

  .controls{position:sticky; top:64px; z-index:7; background:var(--bg); padding:8px 10px 10px 10px}
  .header.shrink + main .controls{top:52px}
  .search{padding:.8rem .95rem; font-size:16px}

  .item{padding:12px}
  .title{font-size:17px}
  .meta{font-size:.78rem}
}
@media (max-width:380px){
  .h1{font-size:19px}
  .badge{display:none}
  .metaTop{display:none}
}
</style>
</head>
<body>
<header class="header">
  <div class="wrap card">
    <div class="top">
      <div class="logo"></div>
      <div>
        <div class="h1">Purdue Men's Basketball News</div>
        <div class="badge">● CURATED &amp; DE-CLUTTERED</div>
      </div>
      <div class="metaTop"><span id="updated">Updated: —</span></div>
    </div>

    <div class="pills" id="pillsRow">
      <button class="pill btn" id="sitesBtn" aria-haspopup="dialog" aria-expanded="false">More Sites ▾</button>
      <button class="pill btn songBtn" id="songBtn" aria-pressed="false">► Play Fight Song</button>
    </div>

    <div class="controls">
      <input id="q" class="search" placeholder="Search news (e.g., Edey, Field of 68)" />
      <span class="count"><span id="count">0</span> results</span>
    </div>
  </div>
</header>

<!-- Sites overlay -->
<div class="overlay" id="sitesOverlay" role="dialog" aria-modal="true" aria-labelledby="sitesTitle">
  <div class="sheet" role="document">
    <div class="sheetHead">
      <div class="sheetTitle" id="sitesTitle">Quick Links</div>
      <button class="xBtn" id="closeSites" aria-label="Close">✕</button>
    </div>
    <div class="links">
      <a target="_blank" href="https://www.hammerandrails.com/">Hammer &amp; Rails</a>
      <a target="_blank" href="https://goldandblack.com/">GoldandBlack</a>
      <a target="_blank" href="https://www.espn.com/mens-college-basketball/team/_/id/2509/purdue-boilermakers">ESPN — Purdue MBB</a>
      <a target="_blank" href="https://www.cbssports.com/college-basketball/teams/PUR/purdue-boilermakers/">CBS — Purdue MBB</a>
      <a target="_blank" href="https://www.barstoolsports.com/tag/purdue-boilermakers">Barstool — Purdue tag</a>
      <a target="_blank" href="https://www.youtube.com/@TheFieldOf68">YouTube — Field of 68</a>
      <a target="_blank" href="https://www.youtube.com/@SleepersMedia">YouTube — Sleepers Media</a>
      <a target="_blank" href="https://www.reddit.com/r/Boilermakers/">Reddit /r/Boilermakers</a>
      <a target="_blank" href="https://purduesports.com/sports/mens-basketball/schedule">Purdue — Schedule</a>
      <a target="_blank" href="https://purduesports.com/sports/mens-basketball/roster">Purdue — Roster</a>
    </div>
  </div>
</div>

<main class="wrap">
  <div id="list" class="list"></div>
</main>

<script>
// smooth shrink
(function(){
  const header=document.querySelector('.header');
  let ticking=false;
  function applyShrink(){
    const y=window.scrollY||0;
    if(y>40) header.classList.add('shrink'); else if(y<10) header.classList.remove('shrink');
    ticking=false;
  }
  window.addEventListener('scroll',()=>{ if(!ticking){ requestAnimationFrame(applyShrink); ticking=true; }});
  applyShrink();
})();

// --- Helpers to lock body without layout shift ---
let _lockScrollTop = 0;
function lockBody(){
  // compute scrollbar width to avoid horizontal jump
  const sbw = window.innerWidth - document.documentElement.clientWidth;
  _lockScrollTop = window.scrollY || document.documentElement.scrollTop || 0;
  document.body.style.paddingRight = sbw > 0 ? sbw + 'px' : '';
  // prevent background scroll but keep visual position
  document.body.style.position = 'fixed';
  document.body.style.top = `-${_lockScrollTop}px`;
  document.body.style.width = '100%';
}
function unlockBody(){
  document.body.style.position = '';
  document.body.style.top = '';
  document.body.style.width = '';
  document.body.style.paddingRight = '';
  window.scrollTo(0, _lockScrollTop);
}

// Sites overlay
const sitesBtn = document.getElementById('sitesBtn');
const overlay  = document.getElementById('sitesOverlay');
const closeBtn = document.getElementById('closeSites');
function openSites(){
  lockBody();
  overlay.classList.add('show');
  sitesBtn.setAttribute('aria-expanded','true');
}
function closeSites(){
  overlay.classList.remove('show');
  sitesBtn.setAttribute('aria-expanded','false');
  // wait for fade to end so we don't flash
  setTimeout(unlockBody, 120);
}
sitesBtn.addEventListener('click', openSites);
closeBtn.addEventListener('click', closeSites);
overlay.addEventListener('click', (e)=>{ if(e.target===overlay) closeSites(); });
document.addEventListener('keydown', (e)=>{ if(e.key==='Escape') closeSites(); });

// Fight song toggle
const songBtn=document.getElementById('songBtn');
let audio;
function setSongState(playing){
  songBtn.classList.toggle('playing', playing);
  songBtn.textContent = playing ? '⏸ Stop Fight Song' : '► Play Fight Song';
  songBtn.setAttribute('aria-pressed', String(playing));
}
songBtn.addEventListener('click', ()=>{
  if(!audio){
    audio=new Audio('/static/fight.mp3');
    audio.addEventListener('error',()=>alert('fight.mp3 not found in /static/'));
    audio.addEventListener('ended',()=>setSongState(false));
  }
  if(songBtn.classList.contains('playing')){
    audio.pause(); audio.currentTime=0; setSongState(false);
  }else{
    audio.currentTime=0; audio.play(); setSongState(true);
  }
});

// Render items
function esc(s){ return (s||'').replace(/[&<>"']/g, m=>({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m])); }
function pill(tag){ return `<span class="tag">${tag}</span>`; }
function fmtDate(iso){ try{ return new Date(iso).toLocaleString(); }catch{ return iso||''; } }

let ALL=[];
const listEl=document.getElementById('list');
const qEl=document.getElementById('q');
const countEl=document.getElementById('count');
const updEl=document.getElementById('updated');

function row(it){
  const isVid = it.is_video || (it.link||'').includes('youtube.com') || (it.link||'').includes('youtu.be');
  const vid = isVid ? pill('Video') : '';
  return `
  <a class="item" href="${esc(it.link)}" target="_blank" rel="noopener">
    <div class="meta"><span class="source">${esc(it.source)}</span> · <span>${esc(fmtDate(it.iso||''))}</span>${vid}</div>
    <div class="title">${esc(it.title||'')}</div>
    ${it.summary ? `<div class="sum">${esc(it.summary)}</div>` : ``}
  </a>`;
}
function render(){
  const q=(qEl.value||'').trim().toLowerCase();
  const filtered = !q ? ALL : ALL.filter(it=>{
    const hay=(it.title+' '+(it.summary||'')+' '+(it.source||'')).toLowerCase();
    return hay.includes(q);
  });
  countEl.textContent = filtered.length;
  listEl.innerHTML = filtered.map(row).join('');
}
fetch('/api/items').then(r=>r.json()).then(items=>{ ALL=items||[]; render(); });
fetch('/api/last-mod').then(r=>r.json()).then(b=>{
  if(b && b.modified) updEl.textContent = 'Updated: ' + b.modified.replace('T',' ');
});
qEl.addEventListener('input', render);
</script>
</body>
</html>
"""

@app.get("/")
def index():
    return Response(HTML, mimetype="text/html")

@app.get("/static/<path:path>")
def static_files(path):
    return send_from_directory(app.static_folder, path)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
