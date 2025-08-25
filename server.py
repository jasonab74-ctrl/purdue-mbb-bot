from flask import Flask, jsonify
import json, os

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

@app.route("/")
def home():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Purdue MBB News</title>
  <style>
    :root{
      --bg:#f7f7f9;
      --card:#ffffff;
      --ink:#111;
      --muted:#666;
      --border:#e6e6ea;
      --gold:#cfb87c;      /* Purdue gold tone */
      --gold-ink:#2b2b2b;
      --pill-bg:#111;      /* header pill background */
      --pill-ink:#fff;
      --btn-bg:#fff;
      --btn-border:#d9d9df;
      --btn-ink:#111;
      --btn-bg-hover:#f2f2f6;
      --shadow: 0 1px 2px rgba(0,0,0,.06), 0 4px 14px rgba(0,0,0,.04);
    }
    *{box-sizing:border-box}
    body{
      font-family: system-ui, -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial, "Apple Color Emoji","Segoe UI Emoji";
      margin:0; padding:0; background:var(--bg); color:var(--ink);
    }
    .wrap{max-width:860px;margin:0 auto;padding:20px}
    /* Header */
    .header{
      display:flex; align-items:center; gap:14px; padding:14px 16px;
      background:#fff; border:1px solid var(--border); border-radius:16px; box-shadow:var(--shadow);
      position:sticky; top:12px; z-index:10; backdrop-filter:saturate(180%) blur(6px);
    }
    .logo{
      width:44px; height:44px; border-radius:10px; overflow:hidden; flex:0 0 44px;
      display:grid; place-items:center; background:linear-gradient(135deg,var(--gold),#e8d9a6);
      border:1px solid #d4c79d;
    }
    .logo img{width:38px; height:38px; object-fit:contain; display:block; filter: drop-shadow(0 1px 0 rgba(0,0,0,.12));}
    .title-wrap{display:flex; flex-direction:column; gap:6px; flex:1}
    .title{
      font-size: clamp(20px,2.6vw,28px);
      line-height:1.2; margin:0;
      letter-spacing:.2px;
    }
    .pill{
      display:inline-flex; align-items:center; gap:8px;
      font-size:.78rem; font-weight:600; letter-spacing:.3px; text-transform:uppercase;
      padding:6px 10px; border-radius:999px; background:var(--pill-bg); color:var(--pill-ink);
      width:fit-content;
    }
    .pill .dot{width:8px;height:8px;border-radius:50%;background:var(--gold);display:inline-block}
    /* Quick links */
    .quicklinks{
      display:flex; flex-wrap:wrap; gap:8px; margin:14px 0 0 0;
    }
    .quicklinks a{
      --pad-x:12px;
      display:inline-flex; align-items:center; gap:8px;
      padding:10px var(--pad-x);
      background:var(--btn-bg); color:var(--btn-ink);
      text-decoration:none; border:1px solid var(--btn-border); border-radius:12px;
      box-shadow:var(--shadow);
      transition:transform .06s ease, background .12s ease;
      font-weight:600; font-size:.92rem;
    }
    .quicklinks a:hover{ background:var(--btn-bg-hover); transform:translateY(-1px); }
    .quicklinks a:active{ transform:translateY(0); }
    .quicklinks a .chip{
      display:inline-block; width:8px; height:8px; border-radius:50%; background:var(--gold);
      box-shadow:0 0 0 1px #e6dab0 inset;
    }
    /* List + cards */
    #list{ margin-top:18px; }
    .card{
      background:var(--card); border:1px solid var(--border); border-radius:14px;
      padding:12px 14px; margin:10px 0; box-shadow:var(--shadow);
    }
    .title-link{
      font-size:1.02rem; font-weight:800; text-decoration:none; color:var(--ink); display:block; margin:.15rem 0 .35rem;
    }
    .meta{ font-size:.82rem; color:var(--muted); display:flex; align-items:center; gap:8px; margin-bottom:.15rem;}
    .badge{ font-weight:700; color:#000; background:linear-gradient(135deg,#fff,#f6f6f8); border:1px solid var(--border); padding:4px 8px; border-radius:999px;}
    .snippet{ color:#333; margin:.25rem 0 0 0; }
    @media (max-width:520px){
      .header{ border-radius:12px; }
      .quicklinks a{ --pad-x:10px; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <header class="header">
      <div class="logo">
        <img src="/static/logo.png" alt="Purdue logo" onerror="this.style.display='none'">
      </div>
      <div class="title-wrap">
        <h1 class="title">Purdue Men's Basketball News</h1>
        <div class="pill"><span class="dot"></span> Curated &amp; de-cluttered feed</div>
        <nav class="quicklinks">
          <a href="https://www.hammerandrails.com/purdue-basketball" target="_blank" rel="noopener">
            <span class="chip"></span> H&amp;R
          </a>
          <a href="https://www.si.com/college/purdue" target="_blank" rel="noopener">
            <span class="chip"></span> SI Purdue
          </a>
          <a href="https://www.on3.com/teams/purdue-boilermakers/" target="_blank" rel="noopener">
            <span class="chip"></span> GoldandBlack
          </a>
          <a href="https://purduesports.com/sports/mens-basketball/schedule" target="_blank" rel="noopener">
            <span class="chip"></span> Schedule
          </a>
          <a href="https://purduesports.com/sports/mens-basketball/roster" target="_blank" rel="noopener">
            <span class="chip"></span> Roster
          </a>
          <a href="https://www.reddit.com/r/Boilermakers/" target="_blank" rel="noopener">
            <span class="chip"></span> Reddit
          </a>
        </nav>
      </div>
    </header>

    <div id="list"></div>
  </div>

  <script>
    function decodeEntities(s){
      const el=document.createElement("textarea");
      el.innerHTML=String(s||"");
      return el.value;
    }
    function clean(input){
      if(!input) return "";
      let s=String(input);
      for(let i=0;i<2;i++){let d=decodeEntities(s);if(d===s) break;s=d;}
      const doc=new DOMParser().parseFromString(s,"text/html");
      s=(doc.body?doc.body.textContent||"":s);
      return s.replace(/\\s+/g," ").trim();
    }
    function render(items){
      const list=document.querySelector("#list");
      list.innerHTML="";
      items.forEach(it=>{
        const card=document.createElement("div"); card.className="card";

        const meta=document.createElement("div"); meta.className="meta";
        const src=document.createElement("span"); src.className="badge"; src.textContent=it.source||"RSS";
        const when=document.createElement("time");
        when.textContent=it.published_ts?new Date(it.published_ts*1000).toLocaleString():"";
        meta.append(src,document.createTextNode("•"),when);

        const a=document.createElement("a");
        a.className="title-link"; a.href=it.link||"#"; a.target="_blank"; a.rel="noopener";
        a.textContent=it.title||"(untitled)";

        const raw=it.summary_text||it.summary||"";
        const desc=clean(raw);

        card.append(meta,a);
        if(desc){
          const p=document.createElement("p"); p.className="snippet";
          p.textContent=desc.length>220 ? (desc.slice(0,220)+"…") : desc;
          card.append(p);
        }
        list.append(card);
      });
    }
    fetch("/api/items").then(r=>r.json()).then(render);
  </script>
</body>
</html>
    """

@app.route("/api/items")
def api_items():
    return jsonify(load_data())

@app.route("/api/refresh-now", methods=["POST"])
def refresh_now():
    return jsonify({"status":"ok","msg":"manual refresh placeholder"})

@app.route("/api/health")
def health():
    return jsonify({"status":"ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
