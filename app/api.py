from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import sqlite3

# --- FastAPI setup ---
app = FastAPI(title="Purdue MBB Bot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DB helper ---
def db():
    con = sqlite3.connect("purdue_mbb.db")
    con.row_factory = sqlite3.Row
    return con

# --- Health ---
@app.get("/healthz")
def healthz():
    con = db()
    row = con.execute("SELECT count(1) AS c FROM articles").fetchone()
    return {"ok": True, "articles": row["c"]}

# --- Latest ---
@app.get("/latest")
def latest(limit: int = 20):
    con = db()
    rows = con.execute(
        "SELECT * FROM articles "
        "ORDER BY (published_at IS NULL), published_at DESC, id DESC "
        "LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]

# --- Search (full-text) ---
@app.get("/search")
def search(q: str = Query(..., min_length=2), limit: int = 20):
    con = db()
    rows = con.execute(
        "SELECT a.* FROM articles_fts f "
        "JOIN articles a ON a.id = f.rowid "
        "WHERE articles_fts MATCH ? "
        "LIMIT ?",
        (q, limit),
    ).fetchall()
    return [dict(r) for r in rows]

# --- Simple chat-style answer from top matches ---
@app.get("/chat")
def chat(question: str):
    con = db()
    rows = con.execute(
        "SELECT a.* FROM articles_fts f "
        "JOIN articles a ON a.id = f.rowid "
        "WHERE articles_fts MATCH ? "
        "LIMIT 5",
        (question,),
    ).fetchall()
    if not rows:
        return {
            "answer": "I don’t have anything on that yet. Try another query or check back shortly.",
            "sources": [],
        }
    bullets = [f"- {r['title']} ({r['source']}) — {r['url']}" for r in rows]
    return {"answer": "Here’s what I found:\n" + "\n".join(bullets), "sources": bullets}

# --- Secure refresh endpoint for cron job ---
REFRESH_KEY = os.getenv("REFRESH_KEY", "")

@app.post("/refresh")
def refresh(key: str):
    if not REFRESH_KEY or key != REFRESH_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    # Run collectors INSIDE this web container so it updates the same SQLite DB
    try:
        from app.collect import run_collect_once
        from app.reddit_collect import run as run_reddit
        run_collect_once()
        run_reddit()
        return {"ok": True, "message": "Collectors ran"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Serve the simple web UI at /ui ---
app.mount("/ui", StaticFiles(directory="static", html=True), name="ui")
