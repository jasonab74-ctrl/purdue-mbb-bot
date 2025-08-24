import praw
import sqlite3
from datetime import datetime
import os

# --- DB helper ---
def db():
    con = sqlite3.connect("purdue_mbb.db")
    con.row_factory = sqlite3.Row
    return con

# --- Main runner ---
def run():
    # Grab secrets from environment variables (set in Render)
    reddit = praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        username=os.getenv("REDDIT_USERNAME"),
        password=os.getenv("REDDIT_PASSWORD"),
        user_agent=os.getenv("REDDIT_USER_AGENT", "PurdueMBBBot/1.0"),
    )

    SUBS = os.getenv("REDDIT_SUBS", "Boilermakers,Purdue,CollegeBasketball").split(",")

    con = db()
    cur = con.cursor()

    for sub in SUBS:
        print(f"Fetching from r/{sub} ...")
        for submission in reddit.subreddit(sub).new(limit=25):
            title = submission.title
            url = submission.url
            created = datetime.utcfromtimestamp(submission.created_utc)

            cur.execute(
                "INSERT OR IGNORE INTO articles (title, url, source, published_at) VALUES (?, ?, ?, ?)",
                (title, url, f"Reddit r/{sub}", created),
            )

    con.commit()
    con.close()
    print("Reddit posts updated.")
