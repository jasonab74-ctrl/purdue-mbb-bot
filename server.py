from flask import Flask, Response
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route("/ui")
def ui():
    html = """<!doctype html>
<html>
<head><meta charset="utf-8"><title>Purdue Men's Basketball — Live Feed</title></head>
<body>
<h1 style="text-align:center;">Purdue Men's Basketball — Live Feed</h1>
<div id="list" style="max-width:900px;margin:24px auto;font:16px system-ui;"></div>
<script>
(async () => {
  const res = await fetch('/api/news');
  const items = await res.json();
  const list = document.getElementById('list');
  if (!items.length) {
    list.innerHTML = '<p style="text-align:center;color:#666;">No items found. Try again later.</p>';
    return;
  }
  list.innerHTML = items.map(i => (
    `<div style="border:1px solid #e8e8ea;border-radius:8px;padding:12px;margin:8px 0">
       <a href="${i.url}" target="_blank" style="font-weight:600;text-decoration:none">${i.title}</a>
       <div style="color:#666;font-size:14px;margin-top:4px">${new Date(i.published_at).toLocaleString()} • ${i.source || ''}</div>
     </div>`
  )).join('');
})();
</script>
</body>
</html>"""
    return Response(html, mimetype="text/html")
