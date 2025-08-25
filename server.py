from flask import Flask, jsonify, Response
import json
import os
from collect import collect_all

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Purdue MBB News</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 720px; margin: 0 auto; padding: 1rem; background:#fafafa; }
    h1 { font-size: 1.6rem; margin-bottom: .5rem; }
    nav.quicklinks { display:flex; flex-wrap:wrap; gap:.5rem; margin:.25rem 0 1rem; }
    nav.quicklinks a { padding:.25rem .5rem; border:1px solid #ddd; border-radius:6px; text-decoration:none; color:#222; background:#fff; }
    .card { background:#fff; border:1px solid #ddd; border-radius:8px; padding:.75rem; margin:.75rem 0; box-shadow:0 1px 2px rgba(0,0,0,.05); }
    .meta { font-size:.8rem; color:#666; margin-bottom:.25rem; display:flex; gap:.5rem; align-items:center; }
    .title { font-weight:600; font-size:1rem; color:#111; text-decoration:none; }
    .title:hover { text-decoration:underline; }
    .snippet { font-size:.9rem; color:#444; margin-top:.25rem; }
  </style>
</head>
<body>
  <h1>Purdue Men's Basketball News</h1>
  <nav class="quicklinks">
    <a href="https://www.hammerandrails.com/purdue-basketball" target="_blank" rel="noopener">H&R</a>
    <a href="https://www.si.com/college/purdue" target="_blank" rel="noopener">SI Purdue</a>
    <a href="https://www.on3.com/teams/purdue-boilermakers/" target="_blank" rel="noopener">GoldandBlack</a>
    <a href="https://purduesports.com/sports/mens-basketball/schedule" target="_blank" rel="noopener">Schedule</a>
    <a href="https://purduesports.com/sports/mens-basketball/roster" target="_blank" rel="noopener">Roster</a>
    <a href="https://www.reddit.com/r/Boilermakers/" target="_blank" rel="noopener">Reddit</a>
  </nav>
  <div id="list"></div>

<script>
  function decodeEntities(s){
    const el=document.createElement("textarea");
    el.innerHTML=String(s||"");
    return el.value;
  }

  function clean(input){
    if(!input) return "";
    let s=String(input);
    for(let i=0;i<2;i++){
      const d=decodeEntities(s);
      if(d===s) break; s=d;
    }
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
      const chip=document.createElement("span"); chip.className="source"; chip.textContent=it.source||"RSS";
      const dot=document.createElement("span"); dot.textContent="•";
      const when=document.createElement("time"); when.textContent=it.published_ts?new Date(it.published_ts*1000).toLocaleString():"";
      meta.append(chip,dot,when);

      const a=document.createElement("a");
      a.className="title"; a.href=it.link||"#"; a.target="_blank"; a.rel="noopener";
      a.textContent=it.title||"(untitled)";

      const raw=it.summary_text || it.summary || "";
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

  fetch("/api/news").then(r=>r.json()).then(render);
</script>
</body>
</html>
"""

@app.route("/")
def home():
    return Response(HTML, mimetype="text/html")

@app.route("/api/news")
def news():
    try:
        with open("news.json") as f:
            data=json.load(f)
    except:
        data=[]
    return jsonify(data)

@app.route("/api/refresh-now", methods=["POST"])
def refresh_now():
    items=collect_all()
    with open("news.json","w") as f:
        json.dump(items,f)
    return jsonify({"ok":True,"count":len(items)})

@app.route("/api/health")
def health():
    return jsonify({"status":"ok"})

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",5000)))
