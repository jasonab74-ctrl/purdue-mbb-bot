import os, sys, json, pathlib, logging, threading, time, subprocess
from datetime import datetime, timezone
from flask import Flask, render_template, render_template_string, url_for, send_file, jsonify
from jinja2 import TemplateNotFound

logging.basicConfig(level=logging.INFO)
BASE_DIR = pathlib.Path(__file__).parent
app = Flask(__name__, static_folder="static", template_folder="templates")

# ===== Background refresher =====
REFRESH_MIN = int(os.getenv("FEED_REFRESH_MIN", "30"))
_started_refresher = False

def _run_collector_once():
    try:
        logging.info("[refresher] starting collector")
        proc = subprocess.run(
            [sys.executable, str(BASE_DIR / "collect.py")],
            capture_output=True, text=True, timeout=300
        )
        if proc.stdout: logging.info(proc.stdout.strip())
        if proc.stderr: logging.warning(proc.stderr.strip())
        logging.info("[refresher] collector finished with code %s", proc.returncode)
    except Exception as e:
        logging.exception("[refresher] collector error: %s", e)

def _refresher_loop():
    time.sleep(10)
    while True:
        _run_collector_once()
        for _ in range(REFRESH_MIN * 60):
            time.sleep(1)

def _ensure_refresher():
    global _started_refresher
    if not _started_refresher:
        threading.Thread(target=_refresher_loop, daemon=True).start()
        _started_refresher = True
        app.logger.info("[refresher] background refresher started (every %d min)", REFRESH_MIN)

# ---------- Inline fallback template ----------
INLINE_INDEX_TEMPLATE = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Purdue Men’s Basketball — Live Feed</title>
<link rel="icon" href="{{ url_for('static', filename='logo.png') }}" sizes="any">
<link rel="apple-touch-icon" href="{{ url_for('static', filename='apple-touch-icon.png') }}">
<link rel="manifest" href="{{ url_for('static', filename='manifest.webmanifest') }}">
<meta name="theme-color" content="#CFB87C">
<link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}?v={{ static_v }}">
</head>
<body>
  <div class="container">
    <header class="header">
      <div class="brand">
        <img src="{{ url_for('static', filename='logo.png') }}" alt="Purdue" class="logo" />
        <div>
          <h1>Purdue Men’s Basketball — Live Feed</h1>
          <div class="sub">({{ items|length }} dynamic items)</div>
          <div class="stamp" id="updatedStamp" data-iso="{{ last_updated_iso or '' }}">
            {% if last_updated_human %}Updated: {{ last_updated_human }}{% else %}Updated: never{% endif %}
          </div>
        </div>
      </div>
      <div class="actions"><button id="fightBtn" class="btn primary">▶︎ Fight Song</button></div>
      <nav class="quick" aria-label="Quick links">
        {% for q in quick_links %}<a href="{{ q.url }}" target="_blank" rel="noopener" class="pill">{{ q.label }}</a>{% endfor %}
      </nav>
    </header>

    <div id="notice" class="notice" style="display:none">
      New items available. <button id="refreshBtn" class="btn">Refresh</button>
    </div>

    <section class="controls">
      <input id="search" class="input" placeholder="Filter (e.g., Braden Smith, Matt Painter)" />
      <select id="sourceFilter" class="select">
        <option value="__all__">All sources</option>
        {% for s in sources %}<option value="{{ s }}">{{ s }}</option>{% endfor %}
      </select>
      <span class="muted" id="countNote"></span>
    </section>

    <main>
      {% if items and items|length %}
        <ul class="items" id="itemsList">
          {% for it in items %}
            <li class="item" data-source="{{ it.source|e }}">
              <div class="item-head">
                {% if it.link %}
                  <a href="{{ it.link }}" target="_blank" rel="noopener" class="title">{{ it.title }}</a>
                {% else %}
                  <span class="title">{{ it.title }}</span>
                {% endif %}
                {% if it.source %}<span class="badge">{{ it.source }}</span>{% endif %}
              </div>
              <div class="meta">{% if it.date %}{{ it.date }}{% endif %}</div>
              {% if it.description %}<p class="desc">{{ it.description }}</p>{% endif %}
            </li>
          {% endfor %}
        </ul>
      {% else %}
        <div class="empty">No dynamic items yet. Quick links above are always available.</div>
      {% endif %}
    </main>
  </div>

  <!-- Inline fight song playback (root-level file) -->
  <audio id="fightAudio" preload="metadata" playsinline webkit-playsinline>
    <source src="{{ fight_song_src }}" type="audio/mpeg">
  </audio>

  <div id="toast" style="display:none;position:fixed;left:50%;bottom:14px;transform:translateX(-50%);background:#111827;color:#fff;padding:10px 14px;border-radius:10px;box-shadow:0 6px 20px rgba(0,0,0,.2);font-size:.9rem;z-index:9999"></div>

  <script>
  (function(){
    const sel=document.getElementById('sourceFilter');
    const list=document.getElementById('itemsList');
    const note=document.getElementById('countNote');
    const search=document.getElementById('search');
    function applyFilter(){
      if(!list)return;
      const srcVal=sel.value, q=(search.value||"").toLowerCase();
      let shown=0;
      for(const li of list.querySelectorAll('.item')){
        const src=li.getAttribute('data-source')||'';
        const text=li.textContent.toLowerCase();
        const on=((srcVal==='__all__')||(src===srcVal)) && (!q || text.includes(q));
        li.style.display=on?'':'none'; if(on) shown++;
      }
      note.textContent=`${shown} shown`;
    }
    sel&&sel.addEventListener('change',applyFilter);
    search&&search.addEventListener('input',applyFilter);
    applyFilter();

    const btn=document.getElementById('fightBtn');
    const audio=document.getElementById('fightAudio');
    const toastEl=document.getElementById('toast');

    function toast(msg){
      if(!toastEl) return;
      toastEl.textContent=msg; toastEl.style.display='';
      setTimeout(()=>{toastEl.style.display='none'}, 2600);
    }

    if(btn&&audio){
      btn.addEventListener('click', ()=>{
        if (audio.readyState < 1) { try { audio.load(); } catch(_){} }
        if(audio.paused){
          audio.play().then(()=>{ btn.textContent='⏸︎ Pause'; })
          .catch(()=>{ toast('Could not play fight_song.mp3'); });
        }else{
          audio.pause(); btn.textContent='▶︎ Fight Song';
        }
      });
    }

    // Humanized "Updated:"
    const stamp = document.getElementById('updatedStamp');
    function humanize(iso){
      if(!iso) return "never";
      const t=new Date(iso), now=new Date(), diff=Math.max(0,(now-t)/1000);
      const units=[["day",86400],["hour",3600],["minute",60],["second",1]];
      for(const [n,s] of units){ if(diff>=s){ const v=Math.floor(diff/s); return v+" "+n+(v>1?"s":"")+" ago"; } }
      return "just now";
    }
    if(stamp){
      const iso=stamp.getAttribute('data-iso');
      stamp.textContent="Updated: "+humanize(iso);
      setInterval(()=>{ stamp.textContent="Updated: "+humanize(iso); }, 30000);
    }
    const notice=document.getElementById('notice');
    const refreshBtn=document.getElementById('refreshBtn');
    let lastIso=stamp?stamp.getAttribute('data-iso'):null;
    async function checkForNew(){
      try{
        const r=await fetch('/items.json',{method:'HEAD',cache:'no-store'});
        const lm=r.headers.get('Last-Modified');
        const newIso=lm?new Date(lm).toISOString():null;
        if(lastIso && newIso && new Date(newIso)>new Date(lastIso)){ notice.style.display=''; }
      }catch(_){}
    }
    refreshBtn&&refreshBtn.addEventListener('click',()=>location.reload());
    setInterval(checkForNew, 5*60*1000);
  })();
  </script>
</body></html>
"""

# ---------- Helpers ----------
def load_items():
    p = BASE_DIR / "items.json"
    if not p.exists():
        return []
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []
    raw_items = raw.get("items", raw) if isinstance(raw, (dict, list)) else []
    out=[]
    for it in (raw_items or []):
        if not isinstance(it, dict): continue
        out.append({
            "title": it.get("title") or "Untitled",
            "link": it.get("link") or "",
            "source": (it.get("source") or "").strip(),
            "date": it.get("date") or "",
            "description": it.get("description") or ""
        })
    return out

def quick_links():
    try:
        from feeds import STATIC_LINKS
        return [{"id": str(i), "label": x["label"], "url": x["url"]} for i, x in enumerate(STATIC_LINKS)]
    except Exception:
        return []

def fight_song_src():
    return url_for("fight_song_file")

def items_last_modified_iso():
    p = BASE_DIR / "items.json"
    if not p.exists():
        return None
    ts = p.stat().st_mtime
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()

def human_last_modified():
    iso = items_last_modified_iso()
    if not iso:
        return None
    dt = datetime.fromisoformat(iso)
    return dt.strftime("%Y-%m-%d %H:%M UTC")

def static_version():
    p = BASE_DIR / "static" / "style.css"
    try:
        return str(int(p.stat().st_mtime))
    except Exception:
        return "1"

# ---------- Routes ----------
@app.before_request
def _kick_refresher():
    _ensure_refresher()

@app.get("/")
def index():
    items = load_items()
    try:
        from feeds import FEEDS_META
        configured_sources = {f["name"] for f in FEEDS_META}
    except Exception:
        configured_sources = set()
    sources = sorted({it["source"] for it in items if it.get("source")} | configured_sources)

    try:
        return render_template(
            "index.html",
            items=items,
            sources=sources,
            quick_links=quick_links(),
            fight_song_src=fight_song_src(),
            last_updated_iso=items_last_modified_iso(),
            last_updated_human=human_last_modified(),
            static_v=static_version(),
        )
    except TemplateNotFound:
        return render_template_string(
            INLINE_INDEX_TEMPLATE,
            items=items,
            sources=sources,
            quick_links=quick_links(),
            fight_song_src=fight_song_src(),
            last_updated_iso=items_last_modified_iso(),
            last_updated_human=human_last_modified(),
            static_v=static_version(),
        )

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/items.json")
def items_json():
    p = BASE_DIR / "items.json"
    if p.exists():
        return send_file(p, mimetype="application/json", conditional=True)
    return jsonify({"items": []})

# -------- Fight song from ROOT --------
@app.get("/fight_song.mp3")
def fight_song_file():
    path = BASE_DIR / "fight_song.mp3"  # root-level file
    if not path.exists():
        app.logger.warning("fight_song.mp3 not found at %s", path)
        return ("", 404)
    resp = send_file(path, mimetype="audio/mpeg", conditional=True)
    resp.headers["Accept-Ranges"] = "bytes"
    resp.headers["Cache-Control"] = "public, max-age=604800"
    return resp
