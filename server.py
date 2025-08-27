# server.py  — Purdue MBB News (clean header, Sites dropdown, search; no "Videos only" button)
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
        except Exception:
            return []

def mtime_iso(path):
    try:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(path)))
    except Exception:
        return None

@app.route("/")
def home():
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

  <!-- Icons & social preview -->
  <link rel="icon" type="image/png" sizes="32x32" href="{logo_url}">
  <link rel="icon" type="image/png" sizes="16x16" href="{logo_url}">
  <link rel="apple-touch-icon" href="{logo_url}">
  <meta name="theme-color" content="#cfb87c" />
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

    /* Header */
    .header{{display:flex;align-items:center;gap:14px;padding:14px 16px;background:#fff;border:1px solid var(--border);
      border-radius:16px;box-shadow:var(--shadow);position:sticky;top:12px;z-index:10;
      transition:padding .22s cubic-bezier(.2,.8,.2,1);}}
    .logo{{width:44px;height:44px;border-radius:10px;overflow:hidden;display:grid;place-items:center;
      background:linear-gradient(135deg,var(--gold),#e8d9a6);border:1px solid #d4c79d;
      transition:width .22s,height .22s;}}
    .logo img{{width:38px;height:38px;object-fit:contain;display:block;filter:drop-shadow(0 1px 0 rgba(0,0,0,.12));
      transition:width .22s,height .22s;}}
    .title-wrap{{display:flex;flex-direction:column;gap:6px;flex:1}}
    .title{{font-size:clamp(20px,2.6vw,28px);line-height:1.2;margin:0;transition:font-size .22s;}}
    .row{{display:flex;gap:10px;align-items:center;flex-wrap:wrap}}
    .pill{{display:inline-flex;align-items:center;gap:8px;font-size:.78rem;font-weight:700;letter-spacing:.3px;
      text-transform:uppercase;padding:6px 10px;border-radius:999px;background:var(--pill-bg);color:var(--pill-ink);}}
    .pill .dot{{width:8px;height:8px;border-radius:50%;background:var(--gold);display:inline-block}}

    /* Sites dropdown */
    .sites{{position:relative;display:inline-block;margin-top:6px}}
    .chipbtn{{display:inline-flex;align-items:center;gap:8px;padding:10px 12px;background:var(--btn-bg);color:var(--btn-ink);
      text-decoration:none;border:1px solid var(--btn-border);border-radius:12px;box-shadow:var(--shadow);
      font-weight:600;font-size:.92rem;}}
    .chipbtn:hover{{background:var(--btn-bg-hover)}}
    .menu{{position:absolute;top:calc(100% + 6px);left:0;background:#fff;border:1px solid var(--border);
      border-radius:12px;box-shadow:var(--shadow);padding:6px;min-width:240px;display:none}}
    .menu.show{{display:block}}
    .menu a{{display:flex;align-items:center;gap:10px;padding:10px;border-radius:10px;color:var(--ink);
      text-decoration:none;font-weight:600}}
    .menu a:hover{{background:var(--btn-bg-hover)}}
    .chip{{width:8px;height:8px;border-radius:50%;background:var(--gold);box-shadow:0 0 0 1px #e6dab0 inset;display:inline-block}}

    /* Search */
    .searchrow{{display:flex;align-items:center;gap:10px;margin-top:10px}}
    .search-input{{flex:1;min-width:200px;padding:10px 12px;border:1px solid var(--btn-border);border-radius:12px;
      background:#fff;box-shadow:var(--shadow);font-size:.96rem}}
    .count{{font-size:.85rem;color:var(--muted)}}

    #list{{margin-top:18px}}
    .card{{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:12px 14px;margin:10px 0;box-shadow:var(--shadow)}}
    .title-link{{font-size:1.02rem;font-weight:800;text-decoration:none;color:var(--ink);display:block;margin:.15rem 0 .35rem}}
    .meta{{font-size:.82rem;color:var(--muted);display:flex;align-items:center;gap:8px;margin-bottom:.15rem}}
    .badge{{font-weight:700;color:#000;background:linear-gradient(135deg,#fff,#f6f6f8);border:1px solid var(--border);
      padding:4px 8px;border-radius:999px}}
    .snippet{{color:#333;margin:.25rem 0 0}}
    .last{{font-size:.78rem;color:#555;margin-left:8px}}
    .videobadge{{font-weight:700;color:#0a0;background:linear-gradient(135deg,#f4fff4,#ecffec);
      border:1px solid #cfe9cf;padding:4px 8px;border-radius:999px}}
    .empty{{text-align:center;color:#666;padding:18px}}

    /* Shrunk state hides the sites button for max space */
    .header.shrink{{ padding:6px 10px; }}
    .header.shrink .logo{{ width:38px; height:38px; }}
    .header.shrink .logo img{{ width:32px; height:32px; }}
    .header.shrink .title{{ font-size:clamp(16px,4.2vw,22px); }}
    .header.shrink .sites{{ display:none; }}

    @media (max-width: 640px){{ 
      .header{{ top:8px; }}
      .card{{ padding:10px 12px; }}
      .title-link{{ font-size:1rem; }}
      .snippet{{ font-size:.95rem; }}
    }}
    @media (prefers-reduced-motion: reduce){{ *{{transition:none !important; animation:none !important;}} }}
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

        <!-- Sites dropdown (compact) -->
        <div class="sites">
          <button id="sitesBtn" class="chipbtn" type="button" aria-haspopup="true" aria-expanded="false">Sites ▾</button>
          <div id="sitesMenu" class="menu" role="menu" aria-hidden="true">
            <a href="https://www.hammerandrails.com/purdue-basketball" target="_blank" rel="noopener"><span class="chip"></span> H&amp;R</a>
            <a href="https://www.espn.com/mens-college-basketball/team/_/id/2509/purdue-boilermakers" target="_blank" rel="noopener"><span class="chip"></span> ESPN</a>
            <a href="https://www.on3.com/teams/purdue-boilermakers/" target="_blank" rel="noopener"><span class="chip"></span> GoldandBlack</a>
            <a href="https://purduesports.com/sports/mens-basketball/schedule" target="_blank" rel="noopener"><span class="chip"></span> Schedule</a>
            <a href="https://purduesports.com/sports/mens-basketball/roster" target="_blank" rel="noopener"><span class="chip"></span> Roster</a>
            <a href="https://www.barstoolsports.com/topics/college-basketball" target="_blank" rel="noopener"><span class="chip"></span> Barstool</a>
            <a href="https://www.reddit.com/r/Boilermakers/" target="_blank" rel="noopener"><span class="chip"></span> Reddit</a>
          </div>
        </div>

        <!-- Search -->
        <div class="searchrow">
          <input id="q" class="search-input" type="search" placeholder="Search news (e.g., Edey, Field of 68)" aria-label="Search news">
          <span id="count" class="count"></span>
        </div>
      </div>
    </header>

    <div id="list"></div>
  </div>

  <script>
    // Smooth shrink on scroll
    const header = document.querySelector('.header');
    const ENTER = 40, EXIT = 10;
    let ticking = false;
    function applyShrink(){{ 
      const y = window.scrollY || 0;
      if (y > ENTER) header.classList.add('shrink');
      else if (y < EXIT) header.classList.remove('shrink');
      ticking = false;
    }}
    window.addEventListener('scroll', () => {{
      if (!ticking) {{ window.requestAnimationFrame(applyShrink); ticking = true; }}
    }});
    applyShrink();

    // Sites dropdown
    const sitesBtn = document.getElementById('sitesBtn');
    const sitesMenu = document.getElementById('sitesMenu');
    function closeMenu(){{ 
      sitesMenu.classList.remove('show');
      sitesBtn.setAttribute('aria-expanded','false');
      sitesMenu.setAttribute('aria-hidden','true');
    }}
    function toggleMenu(){{ 
      const open = !sitesMenu.classList.contains('show');
      if (open) {{
        sitesMenu.classList.add('show');
        sitesBtn.setAttribute('aria-expanded','true');
        sitesMenu.setAttribute('aria-hidden','false');
      }} else {{
        closeMenu();
      }}
    }}
    sitesBtn.addEventListener('click', (e)=>{{ e.stopPropagation(); toggleMenu(); }});
    document.addEventListener('click', (e)=>{{ 
      if (!sitesMenu.contains(e.target) && e.target !== sitesBtn) closeMenu();
    }});
    window.addEventListener('keydown', (e)=>{{ if (e.key === 'Escape') closeMenu(); }});

    // URL param helpers
    function getParam(name){{ 
      const u = new URL(window.location.href);
      return u.searchParams.get(name) || "";
    }}
    function setParam(name, value){{ 
      const u = new URL(window.location.href);
      if (value) u.searchParams.set(name, value);
      else u.searchParams.delete(name);
      history.replaceState(null, "", u.toString());
    }}

    const lastEl = document.getElementById("last");
    function setLast(s){{ lastEl.textContent = s ? "Updated: "+s : ""; }}

    function decodeEntities(s){{ const el=document.createElement("textarea"); el.innerHTML=String(s||""); return el.value; }}
    function clean(input){{ 
      if(!input) return "";
      let s=String(input);
      for(let i=0;i<2;i++){{ let d=decodeEntities(s); if(d===s) break; s=d; }}
      const doc=new DOMParser().parseFromString(s,"text/html");
      s=(doc.body?doc.body.textContent||"":s);
      return s.replace(/\\s+/g," ").trim();
    }}

    const listEl = document.getElementById("list");
    const qEl = document.getElementById("q");
    const countEl = document.getElementById("count");
    let ALL = [];

    function render(items){{ 
      listEl.innerHTML = "";
      if (!items.length) {{
        listEl.innerHTML = '<div class="empty">No results. Try another search.</div>';
        countEl.textContent = "0 results";
        return;
      }}
      countEl.textContent = items.length + (items.length === 1 ? " result" : " results");

      items.forEach(it=>{{
        const card=document.createElement("div"); card.className="card";

        const meta=document.createElement("div"); meta.className="meta";
        const src=document.createElement("span"); src.className="badge"; src.textContent=it.source||"RSS";
        const when=document.createElement("time"); when.textContent=it.published_ts?new Date(it.published_ts*1000).toLocaleString():"";
        meta.append(src,document.createTextNode("•"),when);

        // Badge if this looks like a video (source label OR any YouTube URL)
        const isVideo = (
          (it.source||"").toLowerCase().startsWith("youtube:") ||
          /youtube\\.com|youtu\\.be/i.test(it.link||"")
        );
        if (isVideo){{ 
          const vb = document.createElement("span");
          vb.className = "videobadge";
          vb.textContent = "🎥 Video";
          meta.append(document.createTextNode(" • "), vb);
        }}

        const a=document.createElement("a");
        a.className="title-link"; a.href=it.link||"#"; a.target="_blank"; a.rel="noopener";
        a.textContent=it.title||"(untitled)";

        const raw=it.summary_text||it.summary||"";
        const desc=clean(raw);

        card.append(meta,a);
        if(desc){{ 
          const p=document.createElement("p"); p.className="snippet";
          p.textContent=desc.length>220 ? (desc.slice(0,220)+"…") : desc;
          card.append(p);
        }}
        listEl.append(card);
      }});
    }}

    function filterNow(){{ 
      const q = (qEl.value || "").trim().toLowerCase();
      let items = ALL;

      if (q) {{
        items = items.filter(it => {{
          const t = ((it.title||"") + " " + (it.source||"") + " " + (it.summary_text||it.summary||"")).toLowerCase();
          return t.includes(q);
        }});
      }}

      render(items);
    }}

    // Debounce search input
    let tmr;
    qEl.addEventListener("input", () => {{
      setParam("q", qEl.value.trim());
      clearTimeout(tmr);
      tmr = setTimeout(filterNow, 120);
    }});

    async function load(){{ 
      const r = await fetch("/api/items"); 
      ALL = await r.json(); 
      const m = await fetch("/api/last-mod").then(x=>x.json()).catch(()=>null);
      if(m && m.modified) setLast(m.modified);

      const seedQ = getParam("q"); if (seedQ) qEl.value = seedQ;
      filterNow();
    }}

    load();
    setInterval(load, 5*60*1000);
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

# Allow GET and POST so you can click it
@app.route("/api/refresh-now", methods=["GET","POST"])
def refresh_now():
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
