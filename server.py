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
    .row{{display:flex;gap:10px;align-items:center;flex-wrap:wrap}}
    .pill{{display:inline-flex;align-items:center;gap:8px;font-size:.78rem;font-weight:700;letter-spacing:.3px;
      text-transform:uppercase;padding:6px 10px;border-radius:999px;background:var(--pill-bg);color:var(--pill-ink);}}
    .pill .dot{{width:8px;height:8px;border-radius:50%;background:var(--gold);display:inline-block}}

    .quicklinks{{display:flex;flex-wrap:wrap;gap:8px;margin:6px 0 0}}
    .chipbtn{{display:inline-flex;align-items:center;gap:8px;padding:10px 12px;background:var(--btn-bg);color:var(--btn-ink);
      text-decoration:none;border:1px solid var(--btn-border);border-radius:12px;box-shadow:var(--shadow);
      font-weight:600;font-size:.92rem;}}
    .chipbtn:hover{{background:var(--btn-bg-hover)}}
    .chip{{width:8px;height:8px;border-radius:50%;background:var(--gold);box-shadow:0 0 0 1px #e6dab0 inset;display:inline-block}}

    #list{{margin-top:18px}}
    .card{{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:12px 14px;margin:10px 0;box-shadow:var(--shadow)}}
    .title-link{{font-size:1.02rem;font-weight:800;text-decoration:none;color:var(--ink);display:block;margin:.15rem 0 .35rem}}
    .meta{{font-size:.82rem;color:var(--muted);display:flex;align-items:center;gap:8px;margin-bottom:.15rem}}
    .badge{{font-weight:700;color:#000;background:linear-gradient(135deg,#fff,#f6f6f8);border:1px solid var(--border);
      padding:4px 8px;border-radius:999px}}
    .snippet{{color:#333;margin:.25rem 0 0}}
    .last{{font-size:.78rem;color:#555;margin-left:8px}}

    /* ===== Option B: shrink header when scrolling ===== */
    .header.shrink{{ padding:6px 10px; }}
    .header.shrink .title{{ font-size:clamp(16px,4.2vw,22px); }}
    .header.shrink .quicklinks{{ display:none; }} /* hide chips when condensed on any screen */

    /* Mobile tweaks */
    @media (max-width: 640px){{
      .header{{ top:8px; }}
      .logo{{ width:38px;height:38px; }}
      .logo img{{ width:32px;height:32px; }}
      .title{{ font-size:20px; }}
      .quicklinks .chipbtn{{ padding:8px 10px; font-size:.86rem; border-radius:10px; }}
      .card{{ padding:10px 12px; }}
      .title-link{{ font-size:1rem; }}
      .snippet{{ font-size:.95rem; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <header class="header">
      <div class="logo"><img src="/static/logo.png" alt="Purdue logo" onerror="this.style.display='none'"></div>
      <div class="title-wrap">
        <h1 class="title">Purdue Men's Basketball News</h1>
        <div class="row">
          <div class="pill"><span class="dot"></span> Curated &amp; de-cluttered</div>
          <span id="last" class="last"></span>
        </div>
        <nav class="quicklinks">
          <a class="chipbtn" href="https://www.hammerandrails.com/purdue-basketball" target="_blank" rel="noopener"><span class="chip"></span> H&amp;R</a>
          <a class="chipbtn" href="https://www.si.com/college/purdue" target="_blank" rel="noopener"><span class="chip"></span> SI Purdue</a>
          <a class="chipbtn" href="https://www.on3.com/teams/purdue-boilermakers/" target="_blank" rel="noopener"><span class="chip"></span> GoldandBlack</a>
          <a class="chipbtn" href="https://purduesports.com/sports/mens-basketball/schedule" target="_blank" rel="noopener"><span class="chip"></span> Schedule</a>
          <a class="chipbtn" href="https://purduesports.com/sports/mens-basketball/roster" target="_blank" rel="noopener"><span class="chip"></span> Roster</a>
          <a class="chipbtn" href="https://www.reddit.com/r/Boilermakers/" target="_blank" rel="noopener"><span class="chip"></span> Reddit</a>
        </nav>
      </div>
    </header>

    <div id="list"></div>
  </div>

  <script>
    // --- Shrink header on scroll (Option B) ---
    const header = document.querySelector('.header');
    window.addEventListener('scroll', () => {{
      const y = window.scrollY || 0;
      if (y > 10) header.classList.add('shrink');
      else header.classList.remove('shrink');
    }});

    const lastEl = document.getElementById("last");
    function setLast(s){{ lastEl.textContent = s ? "Updated: "+s : ""; }}

    function decodeEntities(s){{ const el=document.createElement("textarea"); el.innerHTML=String(s||""); return el.value; }}
    function clean(input){{
      if(!input) return "";
      let s=String(input);
      for(let i=0;i<2;i++){{let d=decodeEntities(s); if(d===s) break; s=d;}}
      const doc=new DOMParser().parseFromString(s,"text/html");
      s=(doc.body?doc.body.textContent||"":s);
      return s.replace(/\\s+/g," ").trim();
    }}
    function render(items){{
      const list=document.querySelector("#list");
      list.innerHTML="";
      items.forEach(it=>{{
        const card=document.createElement("div"); card.className="card";
        const meta=document.createElement("div"); meta.className="meta";
        const src=document.createElement("span"); src.className="badge"; src.textContent=it.source||"RSS";
        const when=document.createElement("time"); when.textContent=it.published_ts?new Date(it.published_ts*1000).toLocaleString():"";
        meta.append(src,document.createTextNode("•"),when);
        const a=document.createElement("a"); a.className="title-link"; a.href=it.link||"#"; a.target="_blank"; a.rel="noopener";
        a.textContent=it.title||"(untitled)";
        const raw=it.summary_text||it.summary||""; const desc=clean(raw);
        card.append(meta,a);
        if(desc){{ const p=document.createElement("p"); p.className="snippet"; p.textContent=desc.length>220 ? (desc.slice(0,220)+"…") : desc; card.append(p);}}
        list.append(card);
      }});
    }}
    async function load(){{
      const r = await fetch("/api/items"); const data = await r.json(); render(data);
      const m = await fetch("/api/last-mod").then(x=>x.json()).catch(()=>null);
      if(m && m.modified) setLast(m.modified);
    }}
    load();
    setInterval(load, 5*60*1000); // UI refetch every 5 min
  </script>
</body>
</html>
    """

@app.route("/api/items")
def api_items():
    return jsonify(load_data())

@app.route("/api/last-mod")
def last_mod():
    return jsonify({"modified": mtime_iso(DATA_FILE)})

@app.route("/api/refresh-now", methods=["POST"])
def refresh_now():
    # Optional simple key: set REFRESH_KEY env var and call ?key=... or header X-Refresh-Key
    need = os.getenv("REFRESH_KEY", "")
    key = request.args.get("key") or request.headers.get("X-Refresh-Key") or ""
    if need and key != need:
        return jsonify({"status":"forbidden"}), 403
    try:
        from collect import collect, save
        items = collect()
        save(items)
        return jsonify({"status":"ok","count":len(items)})
    except Exception as e:
        return jsonify({"status":"error","error":str(e)}), 500

@app.route("/api/health")
def health():
    return jsonify({"status":"ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
