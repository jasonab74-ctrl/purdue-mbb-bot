import requests
import feedparser
import datetime

YOUTUBE_API_KEY = "YOUR_YOUTUBE_API_KEY"

CHANNELS = {
    "Field of 68": "UCyLMa1U53d8T7ZM-kO2aS-Q",
    "Sleepers Media": "UCxAQKc_Itu3JR9_MyoaNXKw"
}

FEEDS = [
    # Purdue-specific news RSS feeds
    "https://www.si.com/.rss/full/purdue-boilermakers",
    "https://www.on3.com/feeds/team/purdue-boilermakers/",
]

REDDIT_URL = "https://www.reddit.com/r/Boilermakers/new.json?limit=10"


def fetch_rss():
    articles = []
    for url in FEEDS:
        feed = feedparser.parse(url)
        for entry in feed.entries[:10]:
            articles.append({
                "title": entry.title,
                "url": entry.link,
                "published_at": entry.get("published", str(datetime.datetime.now())),
                "source": "RSS"
            })
    return articles


def fetch_reddit():
    headers = {"User-Agent": "purdue-mbb-bot/0.1"}
    r = requests.get(REDDIT_URL, headers=headers)
    posts = r.json()["data"]["children"]
    results = []
    for p in posts:
        data = p["data"]
        results.append({
            "title": data["title"],
            "url": "https://reddit.com" + data["permalink"],
            "published_at": datetime.datetime.fromtimestamp(data["created_utc"]).isoformat(),
            "source": "Reddit"
        })
    return results


def fetch_youtube(channel_id, label):
    url = (
        "https://www.googleapis.com/youtube/v3/search"
        f"?key={YOUTUBE_API_KEY}"
        "&part=snippet&order=date&type=video&maxResults=5"
        f"&channelId={channel_id}"
    )
    r = requests.get(url)
    items = r.json().get("items", [])
    results = []
    for it in items:
        snippet = it["snippet"]
        results.append({
            "title": snippet["title"],
            "url": f"https://www.youtube.com/watch?v={it['id']['videoId']}",
            "published_at": snippet["publishedAt"],
            "source": label
        })
    return results


def collect_all():
    items = []
    items.extend(fetch_rss())
    items.extend(fetch_reddit())
    for label, cid in CHANNELS.items():
        items.extend(fetch_youtube(cid, label))
    # Sort newest first
    items = sorted(items, key=lambda x: x["published_at"], reverse=True)
    return items


if __name__ == "__main__":
    data = collect_all()
    import json
    print(json.dumps(data, indent=2))
