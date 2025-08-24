import os, time, sqlite3, requests, hashlib, datetime as dt

DB = "purdue_mbb.db"
UA = os.getenv("REDDIT_USER_AGENT", "PurdueMBBBot/1.0 by your_reddit_username")
TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
SUBS = os.getenv("REDDIT_SUBS", "Boilermakers,Purdue,CollegeBasketball").split(",")

CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
USERNAME = os.getenv("REDDIT_USERNAME")
PASSWORD = os.getenv("REDDIT_PASSWORD")

def token():
    r = requests.post(
        TOKEN_URL,
        auth=(CLIENT_ID, CLIENT_SECRET),
        data={"grant_type":"password","username":USERNAME,"password":PASSWORD},
        headers={"User-Agent": UA},
        timeout=20
    )
    r.raise_for_status()
    return r.json()["access_token"]

def db():
    con = sqlite3.connect(DB); con.execute("PRAGMA journal_mode=WAL;"); return con

def save(conn, a):
    try:
        conn.execute('''INSERT OR IGNORE INTO articles
            (url,url_hash,source,title,author,published_at,fetched_at,summary,content)
            VALUES (?,?,?,?,?,?,?,?,?)''',
            (a["url"], hashlib.sha256(a["url"].encode()).hexdigest()[:32], a["source"],
             a["title"], a.get("author"), a.get("published_at"), dt.datetime.utcnow().isoformat(),
             a.get("summary"), a.get("content")))
        conn.commit()
    except Exception as e:
        print("DB error:", e)

def run():
    if not all([CLIENT_ID, CLIENT_SECRET, USERNAME, PASSWORD]):
        print("Missing Reddit credentials; skipping reddit_collect.")
        return
    conn = db(); tok = token()
    headers = {"Authorization": f"bearer {tok}", "User-Agent": UA}
    for sub in SUBS:
        try:
            r = requests.get(f"https://oauth.reddit.com/r/{sub}/new?limit=25", headers=headers, timeout=20)
            if r.status_code != 200:
                print("Reddit status", r.status_code, "for", sub); 
                continue
            for p in r.json().get("data",{}).get("children",[]):
                d = p["data"]
                title = d.get("title","")
                if sub.lower() == "collegebasketball" and "purdue" not in title.lower():
                    continue
                save(conn, {
                    "url": f"https://www.reddit.com{d.get('permalink','')}",
                    "source": f"reddit/{sub}",
                    "title": title,
                    "author": d.get("author"),
                    "published_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(d.get("created_utc", time.time()))),
                    "summary": (d.get("selftext") or "")[:600],
                    "content": (d.get("selftext") or "")[:5000],
                })
        except Exception as e:
            print("Reddit fetch error on", sub, ":", e)

if __name__ == "__main__":
    run()
