import feedparser, time, json, os, socket, re, hashlib
from html import unescape

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

# ─────────────────────────────────────────
# SOURCES
SOURCES = [
    {"name": "Hammer & Rails", "url": "https://www.hammerandrails.com/rss/index.xml"},
    {"name": "ESPN CBB",       "url": "https://www.espn.com/espn/rss/ncb/news"},
    {"name": "CBS CBB",        "url": "https://www.cbssports.com/rss/headlines/college-basketball/"},
    {"name": "Bing News",      "url": "https://www.bing.com/news/search?q=Purdue+Boilermakers+men%27s+basketball&format=RSS"},

    {"name": "Google News",    "url": "https://news.google.com/rss/search?q=%22Purdue%22%20%22men%27s%20basketball%22&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Google News",    "url": "https://news.google.com/rss/search?q=%22Purdue%20Boilermakers%22%20basketball&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Google News (ESPN)", "url": "https://news.google.com/rss/search?q=site:espn.com%20Purdue%20basketball&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Google News (Barstool)", "url": "https://news.google.com/rss/search?q=site:barstoolsports.com%20Purdue%20basketball&hl=en-US&gl=US&ceid=US:en"},

    {"name": "YouTube: Field of 68",    "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UC8KEey9Gk_wA_w60Y8xX3Zw"},
    {"name": "YouTube: Sleepers Media", "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCtE2Qt3kFHW2cS7bIMD5zJQ"},
]
# ─────────────────────────────────────────

DATA_FILE = "data.json"

BASKETBALL_TOKENS = [
    "basketball", "mbb", "hoops",
    "ncaa", "tournament", "final four",
    "mackey", "paint crew",
    "matt painter", "painter",
    "guard", "forward", "center",
    "3-pointer", "three-pointer", "assist", "rebound", "double-double",
    "big ten", "b1g",
]
PURDUE_TOKENS = ["purdue", "boiler", "boilers", "boilermaker", "boilermakers", "west lafayette"]
NAME_TOKENS = [
    "zach edey", "braden smith", "fletcher loyer", "mason gillis",
    "trey kaufman", "kaufman-renn", "caleb furst", "myles colvin",
    "camden heide", "lance jones", "omer mayer"
]
ANTI_TOKENS = [
    "football", "cfb", "gridiron", "bowl", "kickoff", "touchdown", "punt", "field goal",
    "quarterback", "qb", "wide receiver", "wr", "running back", "rb",
    "linebacker", "lb", "cornerback", "safety", "defensive back", "db",
    "offensive line", "defensive line", "ol", "dl",
    "ryan walters", "ross-ade",
    "women", "wbb", "volleyball", "softball", "baseball", "soccer",
]

def is_basketball_item(title: str, summary_text: str, link: str, source_name: str) -> bool:
    t = f"{title} {summary_text}".lower()
    url = (link or "").lower()

    if "football" in url:
        return False
    if any(a in t for a in ANTI_TOKENS):
        return False

    has_purdue = any(k in t for k in PURDUE_TOKENS)
    has_ball   = any(k in t for k in BASKETBALL_TOKENS)
    has_name   = any(k in t for k in NAME_TOKENS)

    if ("matt painter" in t) or ("mackey" in t):
        return True

    # Looser for YouTube so Purdue mentions show
    if source_name.lower().startswith("youtube:"):
        return has_purdue or has_name or ("boiler" in t)

    return has_purdue and (has_ball or has_name)

def parse_rss(url):
    return feedparser.parse(url, request_headers=REQ_HEADERS).entries

def key(item):
    base = f"{(item.get('title') or '').strip()}|{(item.get('link') or '').strip()}"
    return hashlib.md5(base.encode("utf-8")).hexdigest()

def collect():
    items, seen = [], set()
    now_ts = int(time.time())

    for src in SOURCES:
        try:
            source_name = (src["name"] or "").strip()
            for e in parse_rss(src["url"])[:50]:
                title = e.get("title", "").strip()
                link = e.get("link", "").strip()

                published = e.get("published_parsed") or e.get("updated_parsed")
                ts = int(time.mktime(published)) if published else now_ts

                summary_raw = (
                    e.get("summary")
                    or e.get("description")
                    or e.get("media_description")
                    or (e.get("content")[0]["value"] if isinstance(e.get("content"), list) and e.get("content") else "")
                    or ""
                )
                summary_text = strip_html(summary_raw)

                if not is_basketball_item(title, summary_text, link, source_name):
                    continue

                item = {
                    "title": title,
                    "link": link,
                    "source": source_name,
                    "published_ts": ts,
                    "summary": summary_raw,
                    "summary_text": summary_text,
                }
                k = key(item)
                if k in seen: 
                    continue
                seen.add(k)
                items.append(item)
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
