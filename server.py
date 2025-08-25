from flask import Flask, jsonify, request, Response, redirect
from flask_cors import CORS
from datetime import datetime, timezone
import json
import threading

# local
from app import collect

app = Flask(__name__)
CORS(app)

# ---------- Minimal UI (inline SVG so the logo never breaks) ----------

HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Purdue Men's Basketball — Live Feed</title>
  <style>
    :root {
      --bg: #fafafa;
      --card: #ffffff;
      --text: #111827;
      --sub: #6b7280;
      --brand: #0f172a;
      --chip: #eef2ff;
      --chip-text: #3730a3;
      --border: #e5e7eb;
      --accent: #cfb991; /* Purdue gold-ish */
    }
    * { box-sizing: border-box; }
    html, body { margin:0; padding:0; background:var(--bg); color:var(--text); font: 16px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, "Apple Color Emoji","Segoe UI Emoji"; }
    .wrap { max-width: 1080px; margin: 24px auto 56px; padding: 0 16px; }
    .header { display:flex; align-items:center; gap:18px; margin-bottom:14px; }
    .logo { width:54px; height:54px; flex:0 0 54px; display:flex; align-items:center; justify-content:center; }
    .logo img { width:100%; height:auto; display:block; }
    h1 { font-size: clamp(22px, 3.6vw, 36px); line-height:1.1; margin:0; font-weight:800; letter-spacing:-0.02em; }
    .right { margin-left:auto; display:flex; gap:12px; align-items:center; }
    .btn { background:#0b1220; color:#fff; border:0; padding:11px 14px; border-radius:10px; font-weight:600; cursor:pointer; }

    .controls { display:flex; gap:10px; flex-wrap:wrap; align-items:center; margin:14px 0 8px; }
    input[type="search"] { flex:1 1 520px; padding:12px 14px; border:1px solid var(--border); border-radius:10px; background:white; }
    select { padding:12px; border:1px solid var(--border); border-radius:10px; background:white; }

    /* Quick links strip */
    .quicklinks { margin: 10px 0 14px; padding: 12px; border:1px solid var(--border); background:#fff; border-radius:12px; }
    .quicklinks .title { font-weight:700; font-size:14px; color:var(--brand); margin:0 0 8px; }
    .quicklinks .links { display:flex; flex-wrap:wrap; gap:10px; }
    .quicklinks a { display:inline-block; text-decoration:none; border:1px solid var(--border); background: #f8fafc; padding:8px 10px; border-radius:999px; font-weight:600; }
    .quicklinks a:hover { background:#eef2ff; border-color:#dbeafe; }

    .meta { color:var(--sub); font-size:13px; margin:4px 0 10px; display:flex; align-items:center; gap:6px; flex-wrap:wrap; }
    .source { background:var(--chip); color:var(--chip-text); padding:2px 8px; border-radius:999px; font-weight:600; }
    .list { display:grid; gap:14px; margin-top:8px; }
    .card { background:var(--card); border:1px solid var(--border); border-radius:14px; padding:14px; }
    .card a.title { font-weight:700; font-size:18px; text-decoration:none; color:var(--brand); display:inline-block; }
    .card a.title:hover { text-decoration:underline; }
    .snippet { color:var(--text); opacity:.85; margin:10px 0 0; }
    .loaded { color:var(--sub); font-size:13px; margin:12px 0; }
    .tools a { color:#1f3aff; text-decoration:none; }
    .tools a:hover { text-decoration:underline; }

    @media (max-width: 520px) {
      .logo { width:46px; height:46px; flex-basis:46px; }
      .btn { padding:10px 12px; }
      .card a.title { font-size:17px; }
      .quicklinks .links { gap:8px; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="header">
      <div class="logo">
        <img alt="Purdue P" src="https://upload.wikimedia.org/wikipedia/commons/thumb/6/68/Purdue_Boilermakers_logo.svg/120px-Purdue_Boilermakers_logo.svg.png" />
      </div>
      <h1>Purdue Men's Basketball — Live Feed</h1>
      <div class="right">
        <button id="refresh" class="btn">Force Refresh</button>
        <span class="tools"><a href="/api/debug" target="_blank" rel="noopener">debug</a></span>
      </div>
    </div>

    <!-- NEW: Static quick links -->
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
    const list = $("#list");
    const q = $("#q");
    const src = $("#src");
    const loaded = $("#loaded");
    const refreshBtn = $("#refresh");

    let DATA = { items: [], updated_ts: null };

    function fmtTime(ts) {
      if (!ts) return "";
      const d = new Date(ts * 1000);
      return d.toLocaleString();
    }

    // Turn HTML string into plain text
    function stripTags(html) {
      if (!html) return "";
      const d = document.createElement("div");
      d.innerHTML = html;
      return (d.textContent || d.innerText || "").replace(/\s+/g," ").trim();
    }

    function render(items) {
      list.innerHTML = "";
      items.forEach(item => {
        const card = document.createElement("div");
        card.className = "card";

        const meta = document.createElement("div");
        meta.className = "meta";
        const chip = document.createElement("span");
        chip.className = "source";
        chip.textContent = item.source || "RSS";
        const dot = document.createElement("span");
        dot.textContent = "•";
        const when = document.createElement("time");
        when.textContent = item.published_ts ? new Date(item.published_ts * 1000).toLocaleString() : (item.published || "");
        meta.append(chip, dot, when);

        const a = document.createElement("a");
        a.className = "title";
        a.href = item.link || "#";
        a.target = "_blank";
        a.rel = "noopener";
        a.textContent = item.title || "(untitled)";

        const descText = stripTags(item.summary_text || item.summary || "");
        if (descText) {
          const snip = document.createElement("p");
          snip.className = "snippet";
          snip.textContent = descText.length > 200 ? (descText.slice(0,200) + "…") : descText;
          card.append(meta, a, snip);
        } else {
          card.append(meta, a);
        }

        list.append(card);
      });
    }

    function applyFilters() {
      const term = q.value.trim().toLowerCase();
      const only = src.value;
      const items = DATA.items.filter(it => {
        const okSrc = !only || (it.source === only);
        const inText = !term || (
          (it.title || "").toLowerCase().includes(term) ||
          stripTags(it.summary_text || it.summary || "").toLowerCase().includes(term)
        );
        return okSrc && inText;
      });
      render(items);
    }

    async function load() {
      const r = await fetch("/api/news", { cache: "no-store" });
      const json = await r.json();
      DATA = json || { items: [] };
      loaded.textContent = "Loaded " + (DATA.updated_ts ? fmtTime(DATA.updated_ts) : "");
      // build sources
      const unique = Array.from(new Set((DATA.items || []).map(i => i.source).filter(Boolean))).sort();
      src.innerHTML = '<option value="">All sources</option>' + unique.map(s => `<option>${s}</option>`).join("");
      applyFilters();
    }

    async function forceRefresh() {
      refreshBtn.disabled = true;
      try {
        await fetch("/api/refresh-now", { method: "POST" });
      } catch {}
      await load();
      refreshBtn.disabled = false;
    }

    q.addEventListener("input", applyFilters);
    src.addEventListener("change", applyFilters);
    refreshBtn.addEventListener("click", forceRefresh);

    document.addEventListener("DOMContentLoaded", load);
  </script>
</body>
</html>"""

# -------------- Routes --------------

@app.route("/")
def ui_root():
    return Response(HTML, mimetype="text/html")

@app.route("/ui")
def ui_alias():
    return redirect("/", code=302)

@app.route("/api/news")
def api_news():
    data = collect.get_cached_or_collect()
    return jsonify(data)

@app.route("/api/news/raw")
def api_news_raw():
    data = collect.get_cached_or_collect(include_raw=True)
    return jsonify(data)

@app.route("/api/refresh-now", methods=["POST"])
def api_refresh_now():
    # refresh in this request
    data = collect.collect_all(force=True)
    return jsonify({"ok": True, "count": len(data["items"])})

@app.route("/api/debug")
def api_debug():
    dbg = collect.collect_debug()
    return Response(json.dumps(dbg, indent=2), mimetype="application/json")


# Run locally (Render uses Gunicorn: `server:app`)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=False)
