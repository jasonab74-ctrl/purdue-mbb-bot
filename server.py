from flask import Flask, jsonify, request
import json, os, time

app = Flask(__name__)

DATA_FILE = "data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return []

def mtime_iso(path):
    try:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(path)))
    except:
        return None

@app.route("/")
def home():
    # Absolute URLs for icons/preview
    base = (request.url_root or "").rstrip("/")
    logo_url = f"{base}/static/logo.png"
    og_local = os.path.join("static", "og.png")
    og_url = f"{base}/static/og.png" if os.path.exists(og_local) else logo_url

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Purdue MBB News</title>

  <!-- Favicons & icons -->
  <link rel="icon" type="image/png" sizes="32x32" href="{logo_url}">
  <link rel="icon" type="image/png" sizes="16x16" href="{logo_url}">
  <link rel="apple-touch-icon" href="{logo_url}">
  <meta name="theme-color" content="#cfb87c" />

  <!-- Social preview -->
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Purdue MBB News">
  <meta property="og:title" content="Purdue MBB News">
  <meta property="og:description" content="Fast, clean Purdue men’s basketball feed.">
  <meta property="og:url" content="{base}">
  <meta property="og:image" content="{og_url}">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="Purdue MBB News">
  <meta name="twitter:description" content="Fast, clean Purdue men’s basketball feed.">
  <meta name="twitter:image" content="{og_url}">

  <style>
    :root{{--bg:#f7f7f9;--card:#fff;--ink:#111;--muted:#666;--border:#e6e6ea;--gold:#cfb87c;
      --pill-bg:#111;--pill-ink:#fff;--btn-bg:#fff;--btn-border:#d9d9df;--btn-ink:#111;--btn-bg-hover:#f2f2f6;
      --shadow:0 1px 2px rgba(0,0,0,.06),0 4px 14px rgba(0,0,0,.04);}}
    *{{box-sizing:border-box}}
    body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial;margin:0;background:var(--bg);color:var(--ink);}}
    .wrap{{max-width:860px;margin:0 auto;padding:20px}}

    /* Header (sticky by default) */
    .header{{display:flex;align-items:center;gap:14px;padding:14px 16px;background:#fff;border:1px solid var(--border);
      border-radius:16px;box-shadow:var(--shadow);position:sticky;top:12px;z-index:10;
      transition:padding .18s ease, box-shadow .18s ease;}}
    .logo{{width:44px;height:44px;border-radius:10px;overflow:hidden;display:grid;place-items:center;
      background:linear-gradient(135deg,var(--gold),#e8d9a6);border:1px solid #d4c79d;}}
    .logo img{{width:38px;height:38px;object-fit:contain;display:block;filter:drop-shadow(0 1px 0 rgba(0,0,0,.12));}}
    .title-wrap{{display:flex;flex-direction:column;gap:6px;flex:1}}
    .title{{font-size:clamp(20px,2.6vw,28px);line-height:1.2;margin:0;}}
    .row{{display
