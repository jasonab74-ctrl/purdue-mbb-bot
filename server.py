# server.py
import os, json, threading, time
from datetime import datetime, timezone, timedelta
from flask import Flask, jsonify, send_from_directory, render_template, abort, Response, request

from feeds import DEFAULT_REFRESH_MIN, STATIC_LINKS, CLIENT_CHECK_SECONDS

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
ITEMS_PATH = os.path.join(APP_ROOT, "items.json")
FIGHT_SONG = os.path.join(APP_ROOT, "fight_song.mp3")

app = Flask(__name__)

def _read_items():
    if not os.path.exists(ITEMS_PATH):
        return {"items":[],"generated_at":0}
    with open(ITEMS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

@app.get("/health")
def health():
    ok = os.path.exists(ITEMS_PATH)
    return jsonify({"ok": True, "has_items": ok})

@app.get("/items.json")
def items_json():
    payload = _read_items()
    resp = jsonify(payload)
    # Allow client cache-busting; include last-modified so the page can poll
    lm = datetime.utcfromtimestamp(payload.get("generated_at", int(time.time()))).replace(tzinfo=timezone.utc)
    resp.headers["Last-Modified"] = lm.strftime("%a, %d %b %Y %H:%M:%S GMT")
    return resp

def _partial_send_mp3(path):
    # Robust Range support for iOS
    if not os.path.exists(path):
        abort(404)
    file_size = os.path.getsize(path)
    range_header = request.headers.get("Range")
    if not range_header:
        rv = send_from_directory(APP_ROOT, os.path.basename(path), mimetype="audio/mpeg", conditional=True)
        rv.headers["Accept-Ranges"] = "bytes"
        return rv

    # Parse "bytes=start-end"
    try:
        _, rng = range_header.split("=")
        start_str, end_str = (rng.split("-") + [""])[:2]
        start = int(start_str) if start_str else 0
        end = int(end_str) if end_str else file_size - 1
        start = max(0, start); end = min(end, file_size - 1)
        if start > end:
            raise ValueError
    except Exception:
        return Response(status=416)

    length = end - start + 1
    with open(path, "rb") as f:
        f.seek(start)
        data = f.read(length)

    resp = Response(data, 206, mimetype="audio/mpeg",
                    content_type="audio/mpeg",
                    direct_passthrough=True)
    resp.headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
    resp.headers["Accept-Ranges"] = "bytes"
    resp.headers["Content-Length"] = str(length)
    return resp

@app.get("/fight_song.mp3")
def fight_song():
    return _partial_send_mp3(FIGHT_SONG)

# ----------- UI -----------
INLINE_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<link rel="manifest" href="/static/manifest.webmanifest">
<link rel="apple-touch-icon" href="/static/apple-touch-icon.png">
<link rel="icon" href="/static/logo.png">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ title }}</title>
<link rel="stylesheet" href="/static/style.css">
</head>
<body>
<header class="site-header">
  <img src="/static/logo.png" alt="logo" class="logo">
  <h1>{{ title }}</h1>
  <div class="links">
    <details>
      <summary>Sites ▾</summary>
      <ul>
        {% for l in static_links %}
        <li><a href="{{ l.url }}" target="_blank" rel="noopener">{{ l.name }}</a></li>
        {% endfor %}
      </ul>
    </details>
    <button id="fightBtn" class="btn">Fight Song</button>
  </div>
</header>

<div id="notice" class="notice" hidden>New items available. <button id="reloadBtn">Refresh</button></div>

<main id="list" class="list"></main>

<script>
const LIST = document.getElementById('list');
const NOTICE = document.getElementById('notice');
const RELOAD = document.getElementById('reloadBtn');
let lastGen = 0;
let audio;

function fmt(ts){
  const d = new Date(ts*1000);
  return d.toLocaleString();
}

async function load(refresh=false){
  const res = await fetch('/items.json' + (refresh ? ('?t=' + Date.now()) : ''));
  const data = await res.json();
  if (data.generated_at && data.generated_at > lastGen && lastGen !== 0 && !refresh) {
    NOTICE.hidden = false;
  }
  if (refresh || lastGen === 0){
    lastGen = data.generated_at || 0;
    NOTICE.hidden = true;
    LIST.innerHTML = '';
    (data.items || []).forEach(it => {
      const div = document.createElement('article');
      div.className = 'card';
      div.innerHTML = `
        <div class="meta">
          <span class="src">${it.source || ''}</span>
          <span class="date">${fmt(it.date_ts || 0)}</span>
        </div>
        <a class="title" href="${it.link}" target="_blank" rel="noopener">${it.title}</a>
        ${it.summary ? `<p class="sum">${it.summary}</p>` : ''}
      `;
      LIST.appendChild(div);
    });
  }
}
load(true);

// poll for updates every 5 minutes
setInterval(async () => {
  const res = await fetch('/items.json', {method:'HEAD'});
  const lm = res.headers.get('Last-Modified');
  if (lm){
    const t = Date.parse(lm)/1000;
    if (t > lastGen){ NOTICE.hidden = false; }
  }
}, 300000);

RELOAD.onclick = () => load(true);

document.getElementById('fightBtn').onclick = async () => {
  try{
    if (!audio){ audio = new Audio('/fight_song.mp3'); }
    await audio.play();
  }catch(e){ alert('Could not play. Make sure fight_song.mp3 exists.'); }
};
</script>
</body>
</html>
"""

@app.get("/")
def home():
    # Use real template if present, else inline fallback
    title = os.environ.get("SITE_TITLE", "Penn State Football Feed")
    if os.path.exists(os.path.join(APP_ROOT, "templates", "index.html")):
        return render_template("index.html", title=title, static_links=STATIC_LINKS)
    from jinja2 import Template
    return Template(INLINE_TEMPLATE).render(title=title, static_links=STATIC_LINKS)

# ----------- Background refresher -----------
def run_collector_every(interval_min: int):
    # Run once at boot to populate quickly
    os.system("python collect.py")
    while True:
        time.sleep(interval_min * 60)
        os.system("python collect.py")

def _start_bg():
    # Allow disabling for debugging
    if os.environ.get("DISABLE_COLLECTOR_THREAD") == "1":
        return
    try:
        interval = int(os.environ.get("FEED_REFRESH_MIN", str(DEFAULT_REFRESH_MIN)))
    except Exception:
        interval = DEFAULT_REFRESH_MIN
    th = threading.Thread(target=run_collector_every, args=(interval,), daemon=True)
    th.start()

_start_bg()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
