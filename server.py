from flask import Flask, render_template

app = Flask(__name__)

@app.get("/")
def home():
    return render_template("index.html")

@app.get("/healthz")
def healthz():
    return "ok", 200

@app.get("/news")
def news():
    # Simple placeholder page so the link works.
    return render_template("news.html", items=[
        {"title": "Purdue opens pre-season camp", "url": "#"},
        {"title": "Home schedule announced", "url": "#"},
    ])
