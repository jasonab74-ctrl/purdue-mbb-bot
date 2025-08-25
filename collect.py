import feedparser, time, json, os, socket, re, hashlib
from html import unescape

# Faster failures on slow feeds
socket.setdefaulttimeout(8)

REQ_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

_TAGS = re.compile(r"<[^>]+>")

def strip_html(s: str) -> str:
    s = unescape(s or "")
    s = _TAGS.sub(" ", s)
    return " ".join(s.split())

# ─────────────────────────────────────────────────────────────
# 🔧 EDIT ONLY THIS LIST to add/remove sources (RSS/ATOM URLs)
SOURCES = [
    {"name": "Hammer & Rails", "url": "https://www.hammerandrails.com/rss/index.xml"},
    {"name": "Google News", "url": "https://news.google.com/rss/search?q=%22Purdue%22%20%22men%27s%20basketball%22&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Google News", "url": "https://news.google.com/rss/search?q=%22Purdue%20Boilermakers%22%20basketball&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Bing News",   "url": "https://www.bing.com/news/search?q=Purdue+Boilermakers+men%27s+basketball&format=RSS"},
    {"name": "ESPN CBB",    "url": "https://www.espn.com/espn/rss/ncb/news"},
    {"name": "CBS CBB",     "url": "https://www.cbssports.com/rss/headlines/college-basketball/"},
    {"name": "SI College",  "url": "https://www.si.com/rss/college"},
    {"name": "USA Today CBB", "url": "http://rssfeeds.usatoday.com/usatodaycomcollegebasketball-topstories&x=1"},
    # YouTube (videos). Replace channel_id as you like:
    {"name": "YouTube: Field of 68", "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UC8KEey9Gk_wA_w60Y8xX3Zw"},
    {"name": "YouTube: Sleepers Media", "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCtE2Qt3kFHW2cS7bIMD5zJQ"},
]
# ─────────────────────────────────────────────────────────────

DATA_FILE = "data.json"

def parse_rss(url):
    return feedparser.parse(url, request_headers=REQ_HEADERS).entries

def is_purdue_mbb(text: str) -> bool:
    t = (text or "").lower()
    keys_any = ["purdue", "boilermaker", "matt painter", "mackey", "boilers"]
    anti = ["women", "wbb", "volleyball", "football", "softball", "baseball"]
    return (any(k in t for k in keys_any) and not any(a in t for a in anti))

def key(item):
    base = f"{(item.get('title') or '').strip()}|{(item.get('link') or '').strip()}"
    return hashlib.md5(base.encode("utf-8")).hexdigest()

def collect():
    items = []
    seen = set()
    now_ts = int(time.time())

    for src in SOURCES:
        try:
            for e in parse_rss(src["url"])[:50]:
                title = e.get("title", "").strip()
                link = e.get("link", "").strip()
                published = e.get("published_parsed") or e.get("updated_parsed")
                ts = int(time.mktime(published)) if published else now_ts
                # Pull text from multiple places (YouTube often uses media/content)
                summary_raw = (
                    e.get("summary")
                    or e.get("description")
                    or e.get("media_description")
                    or (e.get("content")[0]["value"] if isinstance(e.get("content"), list) and e.get("content") else "")
                    or ""
                )
                summary_text = strip_html(summary_raw)

                candidate = {
                    "title": title,
                    "link": link,
                    "source": src["name"],
                    "published_ts": ts,
                    "summary": summary_raw,
                    "summary_text": summary_text,
                }

                # Filter for Purdue MBB relevance
                hay = " ".join([title, summary_text])
                if not is_purdue_mbb(hay):
                    continue

                k = key(candidate)
                if k in seen:
                    continue
                seen.add(k)
                items.append(candidate)
        except Exception as ex:
            print("Error fetching", src["url"], ex)

    items.sort(key=lambda x: x["published_ts"], reverse=True)
    return items

def save(items):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2)

if __name__ == "__main__":
    data = collect()
    save(data)
    print("Saved", len(data), "items")
