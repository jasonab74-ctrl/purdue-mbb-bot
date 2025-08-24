from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import sqlite3

app = FastAPI(title="Purdue MBB Bot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def db():
    con = sqlite3.connect("purdue_mbb.db")
    con.row_factory = sqlite3.Row
    return con

@app.get("/healthz")
def healthz():
    con = db()
    row = con.execute("SELECT count(1) AS c FROM articles").fetchone()
    return {"ok": True, "articles": row["c"]}

@app.get("/latest")
def latest(limit: int = 20):
    con = db()
    rows = con.execute(
        "SELECT * FROM articles ORDER BY (published_at IS NULL), published_at DESC, id DESC LIMIT ?",
        (limit,)
    ).fetchall()
    return [dict(r) for r in rows]

@app.get("/search")
def search(q: str = Query(..., min_length=2), limit: int = 20):
    con = db()
    rows = con.execute(
        "SELECT a.* FROM articles_fts f JOIN articles a ON a.id=f.rowid WHERE articles_fts MATCH ? LIMIT ?",
        (q, limit)
    ).fetchall()
    return [dict(r) for r in rows]

@app.get("/chat")
def chat(question: str):
    con = db()
    rows = con.execute(
        "SELECT a.* FROM articles_fts f JOIN articles a ON a.id=f.rowid WHERE articles_fts MATCH ? LIMIT 5",
        (question,)
    ).fetchall()
    if not rows:
        return {"answer": "I don’t have anything on that yet. Try another query or check back shortly.", "sources": []}
    bullets = [f"- {r['title']} ({r['source']}) — {r['url']}" for r in rows]
    return {"answer": "Here’s what I found:\n" + "\n".join(bullets), "sources": bullets}

# Serve the simple UI from /ui
app.mount("/ui", StaticFiles(directory="static", html=True), name="ui")
