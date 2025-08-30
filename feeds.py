# feeds.py — Purdue Men's Basketball sources (expanded)

# Feeds used by the collector. Each dict must have at least: name, url.
# type: "rss" (default), "bing" (RSS), "google" (RSS), or "reddit" (JSON).
# trust: True lets collect.py be more lenient for official/team outlets.

FEEDS = [
    # --- News aggregators (broad) ---
    {
        "name": "Google News — Purdue Basketball",
        "type": "rss",
        "url": "https://news.google.com/rss/search?q=Purdue%20basketball%20OR%20%22Purdue%20Boilermakers%22%20basketball&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "name": "Google News — Matt Painter",
        "type": "rss",
        "url": "https://news.google.com/rss/search?q=%22Matt%20Painter%22%20Purdue&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "name": "Bing News — Purdue Basketball",
        "type": "bing",
        "url": "https://www.bing.com/news/search?q=Purdue%20basketball&format=RSS",
    },
    {
        "name": "Bing News — Big Ten + Purdue",
        "type": "bing",
        "url": "https://www.bing.com/news/search?q=Purdue%20basketball%20Big%20Ten&format=RSS",
    },

    # --- Team/official & core outlets ---
    {
        "name": "PurdueSports.com — Men’s Basketball",
        "type": "rss",
        "url": "https://purduesports.com/rss.aspx?path=mbball",
        "trust": True,
    },
    {
        "name": "On3 — Purdue (site feed)",
        "type": "rss",
        "url": "https://www.on3.com/teams/purdue-boilermakers/feed/",
        "trust": True,
    },
    {
        "name": "247Sports — Purdue (site feed)",
        "type": "rss",
        "url": "https://247sports.com/college/purdue/Feed.rss",
        "trust": True,
    },
    {
        "name": "Hammer & Rails (SB Nation)",
        "type": "rss",
        "url": "https://www.hammerandrails.com/rss/index.xml",
        "trust": True,
    },

    # --- Local/beat & campus outlets (site-scoped via Bing) ---
    {
        "name": "Journal & Courier Purdue",
        "type": "bing",
        "url": "https://www.bing.com/news/search?q=site:jconline.com%20Purdue%20basketball&format=RSS",
    },
    {
        "name": "Purdue Exponent — Men’s Basketball",
        "type": "bing",
        "url": "https://www.bing.com/news/search?q=site:purdueexponent.org%20%28Purdue%20men%27s%20basketball%20OR%20MBB%29&format=RSS",
    },
    {
        "name": "IndyStar Purdue",
        "type": "bing",
        "url": "https://www.bing.com/news/search?q=site:indystar.com%20Purdue%20basketball&format=RSS",
    },

    # --- National sites (site-scoped via Bing to keep it Purdue) ---
    {
        "name": "Yahoo Sports — Purdue",
        "type": "bing",
        "url": "https://www.bing.com/news/search?q=site:sports.yahoo.com%20Purdue%20basketball&format=RSS",
    },
    {
        "name": "CBS Sports — Purdue",
        "type": "bing",
        "url": "https://www.bing.com/news/search?q=site:cbssports.com%20Purdue%20basketball&format=RSS",
    },
    {
        "name": "Sports Illustrated — Purdue",
        "type": "bing",
        "url": "https://www.bing.com/news/search?q=site:si.com%20Purdue%20basketball&format=RSS",
    },

    # --- Reddit (JSON) ---
    { "name": "Reddit — r/Boilermakers", "type": "reddit", "url": "https://www.reddit.com/r/Boilermakers/.json?limit=100" },
    { "name": "Reddit — r/CollegeBasketball (Purdue search)", "type": "reddit",
      "url": "https://www.reddit.com/r/CollegeBasketball/search.json?q=Purdue%20basketball&restrict_sr=on&sort=new&t=year" },
]

# These power the quick-link buttons in the header (front-end reads this)
STATIC_LINKS = [
    {"label": "Purdue — Official MBB Page", "url": "https://purduesports.com/sports/mens-basketball"},
    {"label": "Purdue — Schedule", "url": "https://purduesports.com/sports/mens-basketball/schedule"},
    {"label": "Purdue — Roster", "url": "https://purduesports.com/sports/mens-basketball/roster"},
    {"label": "ESPN — Purdue MBB", "url": "https://www.espn.com/mens-college-basketball/team/_/id/2509/purdue-boilermakers"},
    {"label": "CBS Sports — Purdue", "url": "https://www.cbssports.com/college-basketball/teams/PURDUE/purdue-boilermakers/"},
    {"label": "Yahoo Sports — Purdue", "url": "https://sports.yahoo.com/ncaab/teams/purdue/"},
    {"label": "Hammer & Rails (SB Nation)", "url": "https://www.hammerandrails.com/"},
    {"label": "GoldandBlack (Rivals)", "url": "https://goldandblack.com/"},
    {"label": "Barstool — Purdue", "url": "https://www.barstoolsports.com/topics/purdue-boilermakers"},
    {"label": "Reddit — r/Boilermakers", "url": "https://www.reddit.com/r/Boilermakers/"},
    {"label": "YouTube — Field of 68", "url": "https://www.youtube.com/@TheFieldOf68"},
    {"label": "YouTube — Sleepers Media", "url": "https://www.youtube.com/@SleepersMedia"},
]
