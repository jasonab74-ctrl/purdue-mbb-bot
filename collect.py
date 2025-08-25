import feedparser, time, re, socket
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

SOURCES = [
    {"name":"Hammer & Rails","url":"https://www.hammerandrails.com/rss/current"},
    {"name":"SI Purdue","url":"https://www.si.com/rss/college/purdue"},
    {"name":"GoldandBlack","url":"https://www.on3.com/teams/purdue-boilermakers/feed/"},
    {"name":"Google News","url":"https://news.google.com/rss/search?q=%22Purdue%22%20%22men%27s%20basketball%22&hl=en-US&gl=US&ceid=US:en"},
    {"name":"Google News","url":"https://news.google.com/rss/search?q=%22Purdue%20Boilermakers%22%20basketball&hl=en-US&gl=US&ceid=US:en"},
    {"name":"Bing News","url":"https://www.bing.com/news/search?q=Purdue+Boilermakers+men%27s+basketball&format=RSS"},
    {"name":"ESPN CBB","url":"https://www.espn.com/espn/rss/ncb/news"},
    {"name":"CBS CBB","url":"https://www.cbssports.com/rss/headlines/college-basketball/"},
]

def parse_rss(url, source_name):
    try:
        d=feedparser.parse(url, request_headers=REQ_HEADERS)
    except Exception as e:
        print("ERR feed", url, e)
        return []

    items=[]
    for entry in d.entries[:20]:
        title=entry.get("title","").strip()
        link=entry.get("link","")
        published_ts=0
        if "published_parsed" in entry and entry.published_parsed:
            published_ts=int(time.mktime(entry.published_parsed))
        elif "updated_parsed" in entry and entry.updated_parsed:
            published_ts=int(time.mktime(entry.updated_parsed))

        summary_raw=entry.get("summary") or entry.get("description") or ""
        summary_text=strip_html(summary_raw)

        # Filter: keep only Purdue men's basketball related items
        blob=(title+" "+summary_text).lower()
        if "purdue" not in blob or "basketball" not in blob:
            continue

        items.append({
            "title":title,
            "link":link,
            "source":source_name,
            "published_ts":published_ts,
            "summary":summary_raw,
            "summary_text":summary_text,
        })
    return items

def collect_all():
    all_items=[]
    for s in SOURCES:
        all_items.extend(parse_rss(s["url"], s["name"]))
    all_items.sort(key=lambda x: x["published_ts"], reverse=True)
    return all_items

if __name__=="__main__":
    data=collect_all()
    import json
    with open("news.json","w") as f: json.dump(data,f)
    print("Wrote", len(data), "items")
