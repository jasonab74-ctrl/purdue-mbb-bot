import os
import json
import pathlib
import logging
from flask import Flask, render_template, render_template_string
from jinja2 import TemplateNotFound

logging.basicConfig(level=logging.INFO)

BASE_DIR = pathlib.Path(__file__).parent
app = Flask(__name__, static_folder="static", template_folder="templates")

INLINE_INDEX_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Purdue Men’s Basketball — Feed</title>
  <style>
    :root { --card:#e5e7eb; --pad:14px; --radius:12px; } *{box-sizing:border-box;}
    body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:24px;}
    header{margin-bottom:16px;} .row{display:flex;gap:12px;flex-wrap:wrap;align-items:center;}
    .quick{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0 18px;}
    .quick a{border:1px solid var(--card);border-radius:var(--radius);padding:8px 12px;text-decoration:none;}
    .controls{display:flex;gap:12px;align-items:center;margin-bottom:12px;}
    .items{list-style:none;padding:0;margin:0;display:grid;gap:12px;}
    .item{border:1px solid var(--card);border-radius:var(--radius);padding:var(--pad);}
    .item h3{margin:0 0 4px 0;font-size:1.05rem;} .muted{color:#6b7280;font-size:.9rem;}
    .empty{padding:12px;border:1px dashed var(--card);border-radius:var(--radius);}
    select{padding:6px 8px;}
  </style>
</head>
<body>
  <header>
    <div class="row">
      <h1 style="margin:0">Purdue Men’s Basketball — Live Feed</h1>
      <span class="muted">({{ items|length }} dynamic items)</span>
    </div>
    <nav class="quick" aria-label="Quick links">
      {% for q in quick_links %}
        <a href="{{ q.url }}" target="_blank" rel="noopener" data-static="{{ q.id }}">{{ q.label }}</a>
      {% endfor %}
    </nav>
  </header>

  <section class="controls">
    <label for="sourceFilter">Filter by source:</label>
    <select id="sourceFilter">
      <option value="__all__">All dynamic sources</option>
      {% for s in sources %}
        <option value="{{ s }}">{{ s }}</option>
      {% endfor %}
    </select>
    <span class="muted" id="countNote"></span>
  </section>

  <main>
    {% if items and items|length %}
      <ul class="items" id="itemsList">
        {% for it in items %}
          <li class="item" data-source="{{ it.source|e }}">
            <h3>
              {% if it.link %}
                <a href="{{ it.link }}" target="_blank" rel="noopener">{{ it.title }}</a>
              {% else %}{{ it.title }}{% endif %}
            </h3>
            <div class="muted">
              {% if it.source %}<strong>{{ it.source }}</strong>{% endif %}
              {% if it.date %} · {{ it.date }}{% endif %}
            </div>
            {% if it.description %}<p>{{ it.description }}</p>{% endif %}
          </li>
        {% endfor %}
      </ul>
    {% else %}
      <div class="empty">No dynamic items yet. Quick links above are always available.</div>
    {% endif %}
  </main>

  <script>
    (function(){
      const sel=document.getElementById('sourceFilter');
      const list=document.getElementById('itemsList');
      const note=document.getElementById('countNote');
      function applyFilter(){
        if(!list)return; const val=sel.value; let shown=0;
        for(const li of list.querySelectorAll('.item')){
          const src=li.getAttribute('data-source')||'';
          const match=(val==='__all__')||(src===val);
          li.style.display=match?'':'none'; if(match) shown++;
        }
        note.textContent=list?`${shown} shown`:'';
      }
      if(sel){ sel.addEventListener('change',applyFilter); applyFilter(); }
    })();
  </script>
</body>
</html>"""

def load_items():
    """Load items from items.json (list or {'items': [...]}); return [] on error."""
    path = BASE_DIR / "items.json"
    if not path.exists():
        app.logger.warning("items.json not found; proceeding with empty list.")
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        app.logger.exception("Failed to parse items.json; serving empty list.")
        return []
    if isinstance(raw, dict):
        raw_items = raw.get("items", [])
    elif isinstance(raw, list):
        raw_items = raw
    else:
        raw_items = []
    items = []
    for it in raw_items:
        if not isinstance(it, dict): continue
        items.append({
            "title": it.get("title") or it.get("name") or "Untitled",
            "link": it.get("link") or it.get("url") or "",
            "source": (it.get("source") or "").strip(),
            "date": it.get("date") or "",
            "description": it.get("description") or ""
        })
    return items

def quick_links():
    # 10 always-present links
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

@app.route("/")
def index():
    items = load_items()
    sources = sorted({it["source"] for it in items if it.get("source")})
    try:
        return render_template("index.html",
                               items=items, sources=sources, quick_links=quick_links())
    except TemplateNotFound:
        app.logger.warning("templates/index.html not found; using inline fallback template.")
        return render_template_string(INLINE_INDEX_TEMPLATE,
                                      items=items, sources=sources, quick_links=quick_links())
    except Exception:
        app.logger.exception("Template render error; using inline fallback template.")
        return render_template_string(INLINE_INDEX_TEMPLATE,
                                      items=items, sources=sources, quick_links=quick_links())

@app.get("/health")
def health():
    return {"ok": True}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
