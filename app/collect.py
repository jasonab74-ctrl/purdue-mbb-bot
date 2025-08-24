import hashlib, datetime as dt, asyncio, sqlite3
import feedparser, httpx
from bs4 import BeautifulSoup

DB = "purdue_mbb.db"
HEADERS = {"User-Agent": "PurdueMBBBot/1.0 (+contact@example.com)"}

RSS_FEEDS = [
    "https://www.ncaa.com/news/basketball-men/d1/rss.xml",
    "https://www.hammerandrails.com/rss/index.xml",
]

HTML_SOURCES = [
    ("Purdue MBB Schedule", "https://purduesports.com/sports/mens-basketball/schedule"),
    ("Purdue MBB Hub", "https://purduesports.com/sports/mens-basketball"),
]

def db():
    con = sqlite3.connect(DB)
    con.execute("PRAGMA journal_mode=WAL;")
    return con

def url_hash(u: str) -> str:
    return hashlib.sha256(u.encode("utf-8")).hexdigest()[:32]

def upsert_article(conn, a):
    try:
        conn.execute(
            '''INSERT OR IGNORE INTO articles(url,url_hash,source,title,author,published_at,fetched_at,summary,content)
               VALUES (?,?,?,?,?,?,?,?,?)''',
            (a["url"], url_hash(a["url"]), a["source"], a["title"], a.get("author"),
             a.get("published_at"), dt.datetime.utcnow().isoformat(), a.get("summary"), a.get("content"))
        )
        conn.commit()
    except Exception as e:
        print("DB error:", e)

def fetch_rss():
    items = []
    for feed in RSS_FEEDS:
        d = feedparser.parse(feed)
        src = d.feed.get("title", feed) if getattr(d, "feed", None) else feed
        for e in d.entries:
            summary_html = getattr(e, "summary", "") or ""
            soup = BeautifulSoup(summary_html, "html.parser")
            items.append({
                "url": e.link,
                "source": src,
                "title": e.title,
                "author": getattr(e, "author", None),
                "published_at": getattr(e, "published", None),
                "summary": soup.get_text(" ").strip()[:600],
                "content": None,
            })
    return items

async def fetch_html_pages():
    out = []
    async with httpx.AsyncClient(headers=HEADERS, timeout=20) as client:
        for name, url in HTML_SOURCES:
            r = await client.get(url)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            title = soup.title.get_text(strip=True) if soup.title else name
            parts = []
            for sel in ["h1", "h2", "article p", ".article__body p", ".story-body p", "p"]:
                for tag in soup.select(sel)[:50]:
                    t = tag.get_text(" ", strip=True)
                    if t and t not in parts:
                        parts.append(t)
                if len(parts) >= 60:
                    break
            text = " ".join(parts)
            out.append({
                "url": url,
                "source": name,
                "title": title,
                "author": None,
                "published_at": None,
                "summary": text[:600],
                "content": text[:5000],
            })
    return out

def run_collect_once():
    conn = db()
    for a in fetch_rss():
        upsert_article(conn, a)
    try:
        html_items = asyncio.run(fetch_html_pages())
        for a in html_items:
            upsert_article(conn, a)
    except Exception as e:
        print("HTML fetch error:", e)

if __name__ == "__main__":
    run_collect_once()
