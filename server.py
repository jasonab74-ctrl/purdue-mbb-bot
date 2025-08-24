from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import time
import json
from collect import collect_all, collect_debug

app = Flask(__name__, static_url_path="/static", static_folder="static")
CORS(app)

CACHE_SECONDS = 10 * 60
_cache_data = None          # list[dict]
_cache_fetched_at = 0       # epoch secs

HTML = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Purdue Men's Basketball — Live Feed</title>
  <style>
    :root {{ --fg:#0f172a; --muted:#475569; --border:#e2e8f0; --chip:#eef2ff; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font:16px/1.45 system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, Apple Color Emoji, Segoe UI Emoji; color:var(--fg); background:#fff; }}
    header {{ max-width:1000px; margin:28px auto 8px; display:flex; align-items:center; gap:12px; padding:0 16px; }}
    header img {{ height:40px; width:auto; border-radius:6px; background:#fff; }}
    h1 {{ font-size:28px; margin:0; }}
    .controls {{ max-width:1000px; margin:8px auto 24px; padding:0 16px; display:flex; gap:12px; }}
    input[type="search"] {{ flex:1; padding:12px 14px; border:1px solid var(--border); border-radius:10px; }}
    select {{ padding:12px 14px; border:1px solid var(--border); border-radius:10px; }}
    main {{ max-width:1000px; margin:0 auto; padding:0 16px 48px; }}
    .item {{ border:1px solid var(--border); border-radius:14px; padding:14px 16px; margin:12px 0; }}
    .title {{ font-size:18px; font-weight:600; margin:0 0 6px; }}
    .meta {{ font-size:12px; color:var(--muted); display:flex; gap:8px; align-items:center; flex-wrap:wrap; }}
    .chip {{ background:var(--chip); padding:3px 8px; border-radius:999px; font-size:12px; }}
    .empty {{ color:var(--muted); margin:28px 0; }}
    .toolbar {{ max-width:1000px; margin:0 auto 6px; padding:0 16px; display:flex; gap:10px; align-items:center; }}
    button.small {{ font-size:12px; padding:6px 10px; border:1px solid var(--border); background:#fff; border-radius:8px; cursor:pointer; }}
  </style>
</head>
<body>
  <header>
    <img src="/static/logo.png" alt="Purdue" onerror="this.remove()"/>
    <h1>Purdue Men's Basketball — Live Feed</h1>
  </header>

  <div class="toolbar">
    <button class="small" onclick="refreshNow()">Force refresh</button>
    <span id="stamp" class="meta"></span>
    <a class="small" href="/api/debug" target="_blank" style="text-decoration:none;border:1px solid var(--border);padding:6px 10px;border-radius:8px;">debug</a>
  </div>

  <div class="controls">
    <input id="q" type="search" placeholder="Filter by keyword (e.g., 'Painter', 'Braden Smith')" oninput="render()"/>
    <select id="src" onchange="render()">
      <option value="">All sources</option>
      <option>Google News</option>
      <option>Reddit</option>
    </select>
  </div>

  <main id="list"><div class="empty">Loading…</div></main>

<script>
let DATA = [];
let FETCH
