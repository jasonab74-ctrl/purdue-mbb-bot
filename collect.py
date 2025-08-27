# collect.py — adds focused Sleepers Media feed + strong Purdue MBB filtering
import os
import re
import time
import json
import html
import hashlib
import requests
import feedparser

DATA_FILE = "data.json"
USER_AGENT = "purdue-mbb-bot/1.0 (+https://purdue-mbb-api-2.onrender.com)"
TIMEOUT = 20

# Feeds (keep names short; URLs must be RSS/Atom)
SOURCES = [
    # Core Purdue
    {"name": "Hammer & Rails", "url": "https://www.hammerandrails.com/rss/index.xml"},

    # Broad news
    {"name": "Google News", "url": "https://news.google.com/rss/search?q=%22Purdue%22%20%22men%27s%20basketball%22&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Google News", "url": "https://news.google.com/rss/search?q=%22Purdue%20Boilermakers%22%20basketball&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Bing News",   "url": "https://www.bing.com/news/search?q=Purdue+Boilermakers+men%27s+basketball&format=RSS"},

    # Major CBB wires
    {"name": "ESPN CBB", "url": "https://www.espn.com/espn/rss/ncb/news"},
    {"name": "CBS CBB",  "url": "https://www.cbssports.com/rss/headlines/college-basketball/"},
    {"name": "Yahoo Sports", "url": "https://news.google.com/rss/search?q=site:sports.yahoo.com%20Purdue%20basketball&hl=en-US&gl=US&ceid=US:en"},

    # GoldandBlack / Barstool via site filters
    {"name": "GoldandBlack", "url": "https://news.google.com/rss/search?q=site:on3.com%20Purdue%20basketball&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Barstool",     "url": "https://news.google.com/rss/search?q=site:barstoolsports.com%20Purdue%20basketball&hl=en-US&gl=US&ceid=US:en"},

    # Community
    {"name": "Reddit", "url": "https://www.reddit.com/r/Boilermakers/.rss"},

    # YouTube — channels
    {"name": "YouTube: Field of 68",    "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UC8KEey9Gk_wA_w60Y8xX3Zw"},
    {"name": "YouTube: Sleepers Media", "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCtE2Qt3kFHW2cS7bIMD5zJQ"},

    # YouTube — searches (broad Purdue)
    {"name": "YouTube Search", "url": "https://www.youtube.com/feeds/videos.xml?search_query=Purdue+basketball"},
    {"name": "YouTube Search", "url": "https://www.youtube.com/feeds/videos.xml?search_query=Purdue+Boilermakers+basketball"},

    # YouTube — focused Sleepers Media + Purdue (your request)
    {"name": "YouTube Search: Sleepers Media Purdue", "url": "https://www.youtube.com/feeds/videos.xml?search_query=Sleepers+Media+Purdue"},
]

# Helpers
_re_whitespace = re.compile(r"\s+")
_re_html_tag  = re.compile(r"<[^>]+>")
_re_youtube   = re.compile(r"(youtube\.com|youtu\.be)", re.I)

# Key names/terms to catch Purdue MBB context
NAMES = [
    "matt painter", "zach edey", "edey", "braden smith", "fletcher loyer",
    "trey kaufman", "kaufman-renn", "lance jones", "caleb furst", "mason gillis",
    "myles colvin", "camden heide", "mackey", "b1g", "big ten"
]

ANTI_TOKENS = [
    "football", "cfb", "gridiron", "kickoff", "touchdown", "quarterback", "ryan walters",
    "wbb", "women", "women's basketball", "volleyball", "baseball", "softball", "soccer"
]

def fetch_bytes(url: str) -> bytes:
    r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
    r.raise_for_status()
    return r.content

def norm_text(s: str) -> str:
    if not s:
        return ""
    s = html.unescape(s)
    s = _re_html_tag.sub(" ", s)
    s = _re_whitespace.sub(" ", s)
    return s.strip()

def to_epoch(entry) -> int:
    t = None
    for key in ("published_parsed", "updated_parsed"):
        if getattr(entry, key, None):
            t = getattr(entry, key)
            break
    if t:
        try:
            return int(time.mktime(t))
        except Exception:
            pass
    return int(time.time())

def is_youtube(source_name: str, link: str) -> bool:
    if source_name.lower().startswith("youtube"):
        return True
    return bool(_re_youtube.search(link or ""))

def is_basketball_item(source_name: str, title: str, summary: str, link: str) -> bool:
    t = f"{title} {summary}".lower()

    # Hard drops
    if any(a in t for a in ANTI_TOKENS):
        # allow if explicitly says basketball too
        if "basketball" not in t and "mbb" not in t:
            return False

    has_purdue = ("purdue" in t) or ("boilermaker" in t) or ("boilers" in t)
    has_hoops  = ("basketball" in t) or ("mbb" in t) or ("ncaa" in t)
    has_name   = any(n in t for n in NAMES)

    # Looser for YouTube to catch talk shows & segment titles
    if is_youtube(source_name, link):
        return has_purdue or has_name or ("big ten" in t) or ("b1g" in t)

    # News/wires
    if has_purdue and (has_hoops or has_name or "mackey" in t):
        return True

    # Rankings/awards/etc with Purdue mention
    if has_purdue and any(k in t for k in ["rank", "poll", "award", "preseason"]):
        return True

    return False

def fingerprint(link: str, title: str) -> str:
    base = (link or "").strip() or (title or "").strip()
    return hashlib.sha1(base.encode("utf-8", "ignore")).hexdigest()

def normalize_item(feed_name: str, entry) -> dict:
    title = norm_text(getattr(entry, "title", "") or "")
    link  = getattr(entry, "link", "") or ""

    # prefer content value then summary/description
    summary = ""
    if getattr(entry, "content", None):
        try:
            summary = entry.content[0].value
        except Exception:
            pass
    if not summary:
        summary = getattr(entry, "summary", "") or ""
    summary = norm_text(summary)

    ts = to_epoch(entry)
    src = feed_name or "RSS"

    return {
        "title": title or "(untitled)",
        "link": link,
        "summary_text": summary,
        "published_ts": ts,
        "source": src,
    }

def collect() -> list:
    items = []
    seen = set()

    for src in SOURCES:
        name = src["name"]
        url  = src["url"]
        try:
            raw = fetch_bytes(url)
            parsed = feedparser.parse(raw)
        except Exception:
            continue

        label = name  # keep configured short name

        for e in parsed.entries:
            itm = normalize_item(label, e)
            fp = fingerprint(itm["link"], itm["title"])
            if fp in seen:
                continue
            seen.add(fp)

            if is_basketball_item(label, itm["title"], itm["summary_text"], itm["link"]):
                items.append(itm)

    items.sort(key=lambda x: x.get("published_ts", 0), reverse=True)
    return items

def save(items: list):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False)

if __name__ == "__main__":
    data = collect()
    save(data)
    print(f"Saved {len(data)} items to {DATA_FILE}")
