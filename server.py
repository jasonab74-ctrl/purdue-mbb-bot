import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, request, Response, send_from_directory

app = Flask(__name__, static_folder="static")

# -------------------------------
# Locations & constants
# -------------------------------
# Your items file (whatever your collect.py writes)
CANDIDATE_FILES = [
    Path("data") / "items.json",   # if you store under data/
    Path("items.json"),            # or repo root
]

REFRESH_KEY = "mbb_refresh_6P7wP9dXr2Jq"  # keep the same key you’ve been using

def items_path() -> Path | None:
    for p in CANDIDATE_FILES:
        if p.exists():
            return p
    return None

def read_items() -> list:
    p = items_path()
    if not p:
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []

def last_modified_iso() -> str:
    p = items_path()
    if not p:
        # fall back to "now" so the page shows something
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    ts = p.stat().st_mtime
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

# -------------------------------
# HTML page
# -------------------------------
HOME_HTML = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Purdue Men's Basketball News</title>
<link rel="icon" href="/static/logo.png" />
<style>
  :root {{
    --bg: #f6f4ef;
    --card: #ffffff;
    --ink: #1a1a1a;
    --muted: #6b7280;
    --pill: #f1eee6;
    --brand: #111111;
    --accent: #ffcc00;
    --shadow: 0 6px 20px rgba(0,0,0,.08);
    --radius: 16px;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Apple Color Emoji", "Segoe UI Emoji";
    color: var(--ink);
    background: var(--bg);
  }}

  /* Header (shrinks on scroll) */
  .header {{
    position: sticky;
    top: 0;
    z-index: 50;
    background: var(--bg);
    padding: 22px 14px;
    transition: padding .22s ease, box-shadow .22s ease, backdrop-filter .22s ease;
    backdrop-filter: blur(0px);
  }}
  .header.shrink {{
    padding: 10px 14px;
    box-shadow: 0 2px 18px rgba(0,0,0,.06);
    backdrop-filter: blur(6px);
  }}
  .shell {{ max-width: 980px; margin: 0 auto; }}

  .hero {{
    background: var(--card);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    padding: 18px 18px 14px;
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 14px;
    align-items: start;
  }}
  .logo {{
    width: 56px; height: 56px;
    border-radius: 14px;
    background: #f7f4e0;
    display: grid; place-items: center;
    overflow: hidden;
  }}
  .logo img {{ width: 42px; height: 42px; }}

  h1 {{ margin: 0; font-size: 28px; line-height: 1.2; }}
  .tag {{ display:inline-flex; gap:8px; align-items:center; background:#111; color:#fff; padding:6px 12px; border-radius:999px; font-size:12px; letter-spacing:.04em; }}
  .dot {{ width:6px; height:6px; background:#a3a3a3; border-radius:999px; display:inline-block; }}
  .updated {{ color: var(--muted); margin-left: 10px; font-size: 13px; }}

  .row {{ margin-top: 12px; display:flex; flex-wrap:wrap; gap:10px; }}
  .btn {{
    background: var(--pill);
    padding: 8px 14px;
    border-radius: 999px;
    font-size: 14px;
    color: #111;
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    gap: 8px;
    border: 1px solid #e7e2d6;
  }}
  .btn:hover {{ filter: brightness(.98); }}

  .site-dropdown {{
    position: relative;
  }}
  summary.btn {{ list-style: none; cursor: pointer; }}
  summary.btn::-webkit-details-marker {{ display:none; }}

  .sites {{
    position: absolute; top: 46px; left: 0;
    background: var(--card);
    border-radius: 12px;
    box-shadow: var(--shadow);
    padding: 8px;
    min-width: 240px;
    border: 1px solid #eee6d8;
  }}
  .sites a {{
    display:block; padding:10px 12px; border-radius:8px; color:#111; text-decoration:none; font-size:14px;
  }}
  .sites a:hover {{ background:#f6f2e8; }}

  .searchRow {{ margin-top: 10px; display:flex; gap:10px; align-items:center; }}
  .search {{
    flex:1;
    background: var(--pill);
    border: 1px solid #e7e2d6;
    border-radius: 999px;
    padding: 10px 14px;
    font-size: 15px;
  }}
  .count { color: var(--muted); font-size: 12px; }

  .list { max-width: 980px; margin: 16px auto; display: grid; gap: 12px; padding: 0 14px 28px; }
  .card {{
    background: var(--card);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    padding: 14px 16px;
  }}
  .meta { color: var(--muted); font-size: 12px; display:flex; gap:10px; align-items:center; }
  .source { font-weight: 600; color:#222; }
  .title { margin: 6px 0 4px; font-size: 17px; font-weight: 700; line-height: 1.3; }
  .desc { color: #444; font-size: 14px; }
  .empty { text-align:center; color: var(--muted); padding: 40px 0; }
  @media (max-width: 560px) {{
    h1 {{ font-size: 24px; }}
  }}
</style>
</head>
<body>
  <header class="header">
    <div class="shell">
      <div class="hero">
        <div class="logo"><img src="/static/logo.png" alt="Purdue"></div>
        <div>
          <h1>Purdue Men's Basketball News</h1>
          <div class="row">
            <span class="tag">CURATED &amp; DE-CLUTTERED</span>
            <span class="updated">Updated: <span id="updated">{last_modified_iso()}</span></span>
          </div>

          <div class="row" style="margin-top:10px">
            <a class="btn" href="https://www.hammerandrails.com/" target="_blank"><span class="dot"></span> H&amp;R</a>
            <a class="btn" href="https://www.espn.com/mens-college-basketball/team/_/id/2509/purdue-boilermakers" target="_blank"><span class="dot"></span> ESPN</a>
            <a class="btn" href="https://goldandblack.com/" target="_blank"><span class="dot"></span> GoldandBlack</a>
            <a class="btn" href="https://purduesports.com/sports/mens-basketball/schedule" target="_blank"><span class="dot"></span> Schedule</a>
            <a class="btn" href="https://purduesports.com/sports/mens-basketball/roster" target="_blank"><span class="dot"></span> Roster</a>
            <a class="btn" href="https://www.reddit.com/r/Boilermakers/" target="_blank"><span class="dot"></span> Reddit</a>

            <details class="site-dropdown">
              <summary class="btn"><span class="dot"></span> Sites</summary>
              <div class="sites">
                <a href="https://www.barstoolsports.com/" target="_blank">Barstool Sports</a>
                <a href="https://sports.yahoo.com/college-basketball/" target="_blank">Yahoo Sports (CBB)</a>
                <a href="https://www.si.com/college/purdue/" target="_blank">SI Purdue</a>
              </div>
            </details>
          </div>

          <div class="searchRow">
            <input id="q" class="search" placeholder="Search news (e.g., Edey, Field of 68)" />
            <span class="count"><span id="n">0</span> results</span>
          </div>
        </div>
      </div>
    </div>
  </header>

  <main class="list" id="list"></main>

<script>
(function() {{
  // Smooth shrink on scroll
  const header = document.querySelector('.header');
  let ticking = false;
  function applyShrink() {{
    const y = window.scrollY || 0;
    if (y > 40) header.classList.add('shrink');
    else if (y < 10) header.classList.remove('shrink');
    ticking = false;
  }}
  window.addEventListener('scroll', () => {{
    if (!ticking) {{
      window.requestAnimationFrame(applyShrink);
      ticking = true;
    }}
  }});

  const listEl = document.getElementById('list');
  const q = document.getElementById('q');
  const n = document.getElementById('n');

  let all = [];

  function render(items) {{
    listEl.innerHTML = '';
    if (!items.length) {{
      listEl.innerHTML = '<div class="empty">No results. Try another search.</div>';
      n.textContent = '0';
      return;
    }}
    n.textContent = String(items.length);
    for (const it of items) {{
      const when = it.published || it.date || '';
      const source = it.source || it.site || '';
      const title = it.title || '';
      const desc = it.summary || it.description || '';
      const url = it.link || '#';

      const card = document.createElement('article');
      card.className = 'card';
      card.innerHTML = `
        <div class="meta"><span class="source">${{source}}</span><span>·</span><span>${{when}}</span></div>
        <a href="${{url}}" target="_blank" rel="noopener" class="title">${{title}}</a>
        <div class="desc">${{desc}}</div>
      `;
      listEl.appendChild(card);
    }}
  }}

  function applyFilter() {{
    const v = q.value.trim().toLowerCase();
    if (!v) return render(all);
    const words = v.split(/\\s+/).filter(Boolean);
    const out = all.filter(it => {{
      const hay = (it.title + ' ' + (it.summary||'') + ' ' + (it.source||'')).toLowerCase();
      return words.every(w => hay.includes(w));
    }});
    render(out);
  }}

  q.addEventListener('input', applyFilter);

  // Load items
  fetch('/api/items').then(r => r.json()).then(items => {{
    all = Array.isArray(items) ? items : [];
    render(all);
  }}).catch(() => {{
    render([]);
  }});

  // Update timestamp
  fetch('/api/last-mod').then(r => r.json()).then(j => {{
    if (j && j.modified) document.getElementById('updated').textContent = j.modified;
  }});
}})();
</script>
</body>
</html>
"""

# -------------------------------
# Routes
# -------------------------------

@app.get("/")
def home():
    return Response(HOME_HTML, mimetype="text/html")

@app.get("/api/items")
def api_items():
    return jsonify(read_items())

@app.get("/api/last-mod")
def api_last_mod():
    return jsonify({"modified": last_modified_iso()})

@app.post("/api/refresh-now")
def api_refresh_now():
    key = request.args.get("key") or request.form.get("key")
    if key != REFRESH_KEY:
        return jsonify({"ok": False, "error": "forbidden"}), 403
    # Fire and forget so the request returns fast
    try:
        subprocess.Popen(["python", "collect.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    return jsonify({"ok": True})

# Serve fight song and other static files
@app.get("/fight.mp3")
def fight_song():
    # file should live at ./static/fight.mp3
    return send_from_directory(app.static_folder, "fight.mp3")

@app.get("/static/<path:filename>")
def static_files(filename: str):
    return send_from_directory(app.static_folder, filename)

# Health
@app.get("/api/health")
def health():
    return jsonify({"ok": True})

if __name__ == "__main__":
    # local dev
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
