import os, json, pathlib, logging
from flask import Flask, render_template, render_template_string
from jinja2 import TemplateNotFound

logging.basicConfig(level=logging.INFO)
BASE_DIR = pathlib.Path(__file__).parent

app = Flask(__name__, static_folder="static", template_folder="templates")

# Inline fallback so you never see a blank page if templates/ is off
INLINE_INDEX_TEMPLATE = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Purdue Men’s Basketball — Live Feed</title>
<link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body>
  <div class="container">
    <header class="header">
      <h1>Purdue Men’s Basketball — Live Feed</h1>
      <div class="sub">({{ items|length }} dynamic items)</div>
      <div class="actions">
        <button id="fightBtn" class="btn primary">▶︎ Fight Song</button>
      </div>
      <nav class="quick" aria-label="Quick links">
        {% for q in quick_links %}<a href="{{ q.url }}" target="_blank" rel="noopener" class="pill">{{ q.label }}</a>{% endfor %}
      </nav>
    </header>

    <section class="controls">
      <input id="search" class="input" placeholder="Filter (e.g., Painter, Braden Smith)" />
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
                {% if it.link %}<a href="{{ it.link }}" target="_blank" rel="noopener" class="title">{{ it.title }}</a>{% else %}<span class="title">{{ it.title }}</span>{% endif %}
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

  <audio id="fightAudio" preload="none">
    <source src="{{ fight_song_src }}" type="audio/mpeg">
  </audio>
  <script>
  (function(){
    const sel=document.getElementById('sourceFilter');
    const list=document.getElementById('itemsList');
    const note=document.getElementById('countNote');
    const search=document.getElementById('search');
    function applyFilter(){
      if(!list) return;
      const srcVal = sel.value;
      const q = (search.value||"").toLowerCase();
      let shown=0;
      for(const li of list.querySelectorAll('.item')){
        const src = li.getAttribute('data-source')||'';
        const text = li.textContent.toLowerCase();
        const matchSrc = (srcVal==='__all__') || (src===srcVal);
        const matchText = !q || text.includes(q);
        const on = matchSrc && matchText;
        li.style.display = on ? '' : 'none';
        if(on) shown++;
      }
      note.textContent = `${shown} shown`;
    }
    sel && sel.addEventListener('change', applyFilter);
    search && search.addEventListener('input', applyFilter);
    applyFilter();

    const btn = document.getElementById('fightBtn');
    const audio = document.getElementById('fightAudio');
    if(btn && audio){
      btn.addEventListener('click', async () => {
        try {
          if (audio.paused) { await audio.play(); btn.textContent='⏸︎ Pause'; }
          else { audio.pause(); btn.textContent='▶︎ Fight Song'; }
        } catch(e) {
          // if the local mp3 is missing or blocked, open YouTube fallback
          window.open('https://www.youtube.com/results?search_query=purdue+fight+song', '_blank');
        }
      });
    }
  })();
  </script>
</body></html>
"""

def load_items():
    p = BASE_DIR / "items.json"
    if not p.exists():
        app.logger.info("items.json not found — using empty list")
        return []
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        app.logger.exception("Failed to parse items.json — using empty list")
        return []
    raw_items = raw.get("items", raw) if isinstance(raw, (dict, list)) else []
    out=[]
    for it in (raw_items or []):
        if not isinstance(it, dict): continue
        out.append({
            "title": it.get("title") or it.get("name") or "Untitled",
            "link": it.get("link") or it.get("url") or "",
            "source": (it.get("source") or "").strip(),
            "date": it.get("date") or "",
            "description": it.get("description") or ""
        })
    return out

def quick_links():
    return [
        {"id":"hammerandrails","label":"Hammer & Rails","url":"https://www.hammerandrails.com/purdue-basketball"},
        {"id":"goldandblack","label":"GoldandBlack","url":"https://purdue.rivals.com/"},
        {"id":"espn","label":"ESPN — Purdue MBB","url":"https://www.espn.com/mens-college-basketball/team/_/id/2509/purdue-boilermakers"},
        {"id":"cbs","label":"CBS — Purdue MBB","url":"https://www.cbssports.com/college-basketball/teams/PURDUE/purdue-boilermakers/"},
        {"id":"barstool","label":"Barstool — Purdue Tag","url":"https://www.barstoolsports.com/tag/purdue"},
        {"id":"fieldof68","label":"YouTube — Field of 68","url":"https://www.youtube.com/c/RobDausterFieldOf68"},
        {"id":"sleepers","label":"YouTube — Sleepers Media","url":"https://www.youtube.com/@SleepersMedia"},
        {"id":"reddit","label":"Reddit — r/Boilermakers","url":"https://www.reddit.com/r/Boilermakers/"},
        {"id":"schedule","label":"Purdue — Schedule","url":"https://purduesports.com/sports/mens-basketball/schedule"},
        {"id":"roster","label":"Purdue — Roster","url":"https://purduesports.com/sports/mens-basketball/roster"},
    ]

def fight_song_src():
    # If you add /static/fight_song.mp3 it will play locally; otherwise it still works via YouTube fallback in JS.
    local = app.static_url_path + "/fight_song.mp3"
    return local

@app.get("/")
def index():
    items = load_items()
    sources = sorted({it["source"] for it in items if it.get("source")})
    try:
        return render_template("index.html", items=items, sources=sources,
                               quick_links=quick_links(), fight_song_src=fight_song_src())
    except TemplateNotFound:
        return render_template_string(INLINE_INDEX_TEMPLATE, items=items, sources=sources,
                                      quick_links=quick_links(), fight_song_src=fight_song_src())

@app.get("/health")
def health():
    return {"ok": True}
