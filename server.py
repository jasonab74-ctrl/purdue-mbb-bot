import os
import json
import threading
import time
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, send_file, send_from_directory, Response, jsonify, render_template_string

# ---- Configuration (no hard dependency on feeds.py) -------------------------
# Refresh cadence for the background collector
FEED_REFRESH_MIN = int(os.getenv("FEED_REFRESH_MIN", "30"))

# How often the client checks for fresher items.json
CLIENT_CHECK_SECONDS = int(os.getenv("CLIENT_CHECK_SECONDS", "300"))  # 5 minutes

# Try to import STATIC_LINKS from feeds.py for the UI; fall back to empty
try:
    import feeds as _cfg  # type: ignore
    STATIC_LINKS = getattr(_cfg, "STATIC_LINKS", [])
    SITE_TITLE = getattr(_cfg, "SITE_TITLE", "Purdue Men’s Basketball News")
except Exception:
    STATIC_LINKS = []
    SITE_TITLE = "Purdue Men’s Basketball News"

ITEMS_PATH = Path("items.json")
FIGHT_SONG_PATH = Path("fight_song.mp3")

# Minimal inline template (used unless you add /templates/index.html)
INDEX_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{{ site_title }}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="manifest" href="/static/manifest.webmanifest">
  <link rel="icon" href="/static/logo.png" type="image/png">
  <link rel="apple-touch-icon" href="/static/apple-touch-icon.png">
  <link rel="stylesheet" href="/static/style.css">
</head>
<body>
  <header class="container">
    <div class="brand">
      <img src="/static/logo.png" alt="logo" />
      <h1>{{ site_title }}</h1>
    </div>
    {% if static_links %}
    <nav class="sites">
      <details>
        <summary>Sites ▾</summary>
        <ul>
          {% for link in static_links %}
            <li><a href="{{ link.url }}" target="_blank" rel="noopener">{{ link.name }}</a></li>
          {% endfor %}
        </ul>
      </details>
    </nav>
    {% endif %}
    {% if fight_song %}
      <button id="fightBtn">Fight Song</button>
    {% endif %}
  </header>

  <main class="container">
    <div id="notice" class="notice" hidden>New items available — <button id="reloadBtn">Refresh</button></div>
    <ul id="feed" class="items"></ul>
  </main>

  <script>
    const LIST = document.getElementById('feed');
    const NOTICE = document.getElementById('notice');
    const RELOAD = document.getElementById('reloadBtn');
    let lastSeen = 0;

    function fmtDate(iso) {
      try { return new Date(iso).toLocaleString(); } catch (e) { return iso; }
    }

    async function load(initial=false) {
      const res = await fetch('/items.json', { cache: 'no-cache' });
      if (!res.ok) return;
      const data = await res.json();
      if (!data.items) return;

      // Track "freshness" using mtime header if provided
      const lm = res.headers.get('Last-Modified');
      const ts = lm ? Date.parse(lm) : Date.now();
      if (initial) { lastSeen = ts; }

      LIST.innerHTML = '';
      for (const it of data.items) {
        const li = document.createElement('li');
        li.className = 'item';
        li.innerHTML = `
          <div class="meta">
            <span class="source">${it.source || ''}</span>
            <time>${fmtDate(it.date || '')}</time>
          </div>
          <a class="title" href="${it.link}" target="_blank" rel="noopener">${it.title}</a>
          ${it.description ? `<p class="desc">${it.description}</p>` : ''}
        `;
        LIST.appendChild(li);
      }
    }

    async function check() {
      try {
        const res = await fetch('/items.json', { method:'HEAD', cache:'no-cache' });
        if (!res.ok) return;
        const lm = res.headers.get('Last-Modified');
        const ts = lm ? Date.parse(lm) : 0;
        if (ts > lastSeen) {
          NOTICE.hidden = false;
        }
      } catch(e) {}
    }

    load(true);
    setInterval(check, {{ client_check_seconds|int }} * 1000);
    if (RELOAD) RELOAD.onclick = () => location.reload();

    {% if fight_song %}
    const audio = new Audio('/fight_song.mp3');
    document.getElementById('fightBtn').onclick = () => {
      audio.play().catch(()=>alert('Could not play audio on this device.'));
    };
    {% endif %}
  </script>
</body>
</html>
"""

app = Flask(__name__, static_folder="static", template_folder="templates")


# ------------------------ Helpers -------------------------------------------
def ensure_items_file():
    """Guarantee items.json exists so the app never 404s on first boot."""
    if not ITEMS_PATH.exists():
        ITEMS_PATH.write_text(json.dumps({"items": []}, ensure_ascii=False))


def run_collector_once():
    """Run the feed collector; never raise to the server."""
    try:
        subprocess.run(["python", "collect.py"], check=False)
    except Exception:
        # swallow errors; the next tick will try again
        pass


def collector_loop():
    """Background loop to refresh items on an interval."""
    # Run once on boot so the page has data
    run_collector_once()
    while True:
        time.sleep(FEED_REFRESH_MIN * 60)
        run_collector_once()


# ------------------------ Routes --------------------------------------------
@app.route("/")
def index():
    ensure_items_file()
    # If a real template exists, use it; otherwise fall back to inline
    try:
        return render_template_string(
            INDEX_TEMPLATE,
            static_links=STATIC_LINKS,
            fight_song=FIGHT_SONG_PATH.exists(),
            client_check_seconds=CLIENT_CHECK_SECONDS,
            site_title=SITE_TITLE,
        )
    except Exception:
        # Extremely defensive: still render something
        return "<h1>OK</h1>", 200


@app.route("/health")
def health():
    return jsonify(ok=True)


@app.route("/items.json", methods=["GET", "HEAD"])
def items():
    ensure_items_file()
    # Serve with Last-Modified for client freshness checks
    mtime = datetime.fromtimestamp(ITEMS_PATH.stat().st_mtime, tz=timezone.utc)
    headers = {"Last-Modified": mtime.strftime("%a, %d %b %Y %H:%M:%S GMT")}
    if os.getenv("RAILWAY_ENVIRONMENT"):
        headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    if flask_request_method_head():
        return Response(status=200, headers=headers, mimetype="application/json")
    return send_file(ITEMS_PATH, mimetype="application/json", conditional=True, etag=True, last_modified=mtime)


def flask_request_method_head():
    # small helper to avoid importing request at module import time
    from flask import request  # local import to keep namespace thin
    return request.method == "HEAD"


@app.route("/fight_song.mp3")
def fight_song():
    if not FIGHT_SONG_PATH.exists():
        return ("Not Found", 404)
    resp = send_file(FIGHT_SONG_PATH, mimetype="audio/mpeg", conditional=True)
    resp.headers["Accept-Ranges"] = "bytes"  # allow iOS seeking/streaming
    return resp


@app.route("/static/<path:filename>")
def static_files(filename):
    # Standard static files
    return send_from_directory(app.static_folder, filename)


# ------------------------ Startup -------------------------------------------
def _start_bg_thread():
    t = threading.Thread(target=collector_loop, name="collector", daemon=True)
    t.start()

_start_bg_thread()

if __name__ == "__main__":
    # Local dev only: `python server.py`
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
