#!/usr/bin/env python3
import os, json
from flask import Flask, Response, request, send_from_directory

app = Flask(__name__, static_url_path="/static", static_folder="static")

# ---------- API ----------
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
    # optional manual refresh; set REFRESH_KEY in Render env
    expected = os.getenv("REFRESH_KEY", "")
    key = request.args.get("key", "")
    if not expected or key != expected:
        return Response(json.dumps({"ok": False}), status=403, mimetype="application/json")
    # run collector
    import subprocess
    try:
        subprocess.check_call(["python", "collect.py"])
        return Response(json.dumps({"ok": True}), mimetype="application/json")
    except Exception as e:
        return Response(json.dumps({"ok": False, "err": str(e)}), status=500, mimetype="application/json")

# ---------- UI ----------
HTML = r"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Purdue Men's Basketball News</title>
<link rel="icon" href="/static/logo.png">
<style>
:root{
  --bg:#f6f3ec; --card:#ffffff; --ink:#1f1f1f; --muted:#767676;
  --pill:#f1ede3; --pill-dot:#c19a00; --border:rgba(0,0,0,.08);
}
*{box-sizing:border-box} body{margin:0;font:16px/1.4 -apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Inter,Helvetica,Arial;
  color:var(--ink);background:var(--bg)}
a{color:inherit;text-decoration:none}
.header{
  position:sticky;top:0;z-index:10;background:var(--bg);
  transition:all .25s ease;border-bottom:1px solid transparent
}
.header.shrink{padding-top:.35rem;padding-bottom:.35rem;box-shadow:0 8px 30px -12px rgba(0,0,0,.25);border-bottom-color:var(--border)}
.wrap{max-width:950px;margin:0 auto;padding:1rem}
.card{background:var(--card);border-radius:16px;box-shadow:0 6px 30px rgba(0,0,0,.06);border:1px solid var(--border)}
.top{display:flex;gap:14px;align-items:center;padding:14px 16px}
.logo{width:40px;height:40px;border-radius:10px;background:#f5d87c url('/static/logo.png') center/70% no-repeat;border:1px solid var(--border)}
.h1{font-weight:800;font-size:22px}
.badge{display:inline-flex;gap:8px;align-items:center;background:#111;color:#fff;border-radius:999px;padding:.3rem .7rem;font-size:.8rem}
.pills{display:flex;flex-wrap:wrap;gap:10px;padding:0 16px 12px 16px}
.pill{display:inline-flex;gap:10px;align-items:center;background:var(--pill);padding:.55rem .9rem;border-radius:999px;border:1px solid var(--border)}
.dot{width:8px;height:8px;border-radius:50%;background:var(--pill-dot)}
.controls{display:flex;gap:10px;align-items:center;padding:0 16px 14px 16px}
.search{flex:1;border:1px solid var(--border);border-radius:10px;background:#fff;padding:.7rem .9rem;font-size:16px}
.btn{border:1px solid var(--border);background:#fff;border-radius:10px;padding:.6rem .8rem;cursor:pointer}
.list{display:flex;flex-direction:column;gap:12px;margin-top:14px}
.item{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:12px 14px}
.meta{display:flex;gap:8px;align-items:center;font-size:.82rem;color:var(--muted);margin-bottom:6px}
.source{font-weight:600;color:#444}
.count{color:var(--muted);font-size:12px}
.title{font-weight:800}
.sum{color:#474747;margin-top:6px}
.tag{margin-left:6px;font-size:.72rem;border:1px solid var(--border);border-radius:999px;padding:.1rem .45rem;background:#eef3ff}
.dd{position:relative}
.menu{position:absolute;left:0;top:110%;background:#fff;border:1px solid var(--border);border-radius:10px;box-shadow:0 10px 26px rgba(0,0,0,.12);padding:8px;display:none;min-width:220px}
.menu a{display:block;padding:.45rem .6rem;border-radius:8px}
.menu a:hover{background:#f5f5f5}
.show{display:block}
.small{font-size:.85rem}
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
      <div style="margin-left:auto" class="small"><span id="updated">Updated: —</span></div>
    </div>

    <div class="pills">
      <div class="dd">
        <button class="pill btn" id="sitesBtn">More Sites ▾</button>
        <div class="menu" id="sitesMenu">
          <a target="_blank" href="https://www.hammerandrails.com/">Hammer &amp; Rails</a>
          <a target="_blank" href="https_
