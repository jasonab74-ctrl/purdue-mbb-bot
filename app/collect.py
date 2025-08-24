import feedparser
import sqlite3
from datetime import datetime

# --- Define feeds (name, url) ---
FEEDS = [
    ("NCAA", "https://www.ncaa.com/news/basketball-men/rss.xml"),
    ("Hammer & Rails", "https://www.hammerandrails.com/rss/index.xml"),
    ("PurdueSports", "https://purduesports.com/rss.aspx?path=mbball"),
    ("247Sports Purdue", "https://247sports.com/college/purdue/Article/feed/"),
    ("ESPN Purdue Basketball", "https://www.espn.com/espn/rss/ncb/team?teamId=2509"),
    ("Yahoo Purdue Hoops", "https://sports.yahoo.com/ncaab/teams/purdue/rss/"),
]

# --- DB helper ---
def db():
    con = sqlite3.connect("purdue_mbb.db")
    con.row_factory = sqlite3.Row
    return con

# --- Run collectors once ---
def run_collect_once():
    con = db()
    cur = con.cursor()

    for name, url in FEEDS:
        print(f"Fetching {name} ...")
        feed = feedparser.parse(url)
        for entry in feed.entries:
            title = entry.get("title", "")
            link = entry.get("link", "")
            published = entry.get("published", None)
            if published:
                try:
                    published = datetime(*entry.published_parsed[:6])
                except Exception:
                    published = None

            cur.execute(
                "INSERT OR IGNORE INTO articles (title, url, source, published_at) VALUES (?, ?, ?, ?)",
                (title, link, name, published),
            )

    con.commit()
    con.close()
    print("Feeds updated.")
