# feeds.py — Purdue Men’s Basketball sources

KEYWORDS_EXCLUDE = [
    # Other sports
    "football","wbb","women","volleyball","wrestling","baseball","softball",
    "soccer","hockey","golf","track","cross country","tennis","swimming","lacrosse",
    # Betting
    "draftkings","fanduel","parlay","odds","fantasy",
]

FEEDS_META = [
    # News
    {"name": "Google News – Purdue Basketball",
     "url": "https://news.google.com/rss/search?q=Purdue+Basketball&hl=en-US&gl=US&ceid=US:en",
     "category": "news"},
    {"name": "Bing News – Purdue Basketball",
     "url": "https://www.bing.com/news/search?q=Purdue+Basketball&format=RSS",
     "category": "news"},
    {"name": "IndyStar Purdue",
     "url": "https://www.bing.com/news/search?q=site:indystar.com+Purdue+Basketball&format=RSS",
     "category": "news"},
    {"name": "Journal & Courier Purdue",
     "url": "https://www.bing.com/news/search?q=site:jconline.com+Purdue+Basketball&format=RSS",
     "category": "news"},
    {"name": "Purdue Exponent",
     "url": "https://www.purdueexponent.org/search/?f=rss&t=article&s=start_time&sd=desc&l=10&c=mens/basketball*",
     "category": "news"},

    # Blogs / Media
    {"name": "Hammer & Rails (SB Nation)",
     "url": "https://www.hammerandrails.com/rss/index.xml", "category": "media"},
    {"name": "GoldandBlack (Rivals)",
     "url": "https://purdue.rivals.com/rss", "category": "media"},
    {"name": "On3 Purdue",
     "url": "https://www.on3.com/teams/purdue-boilermakers/feed/", "category": "media"},

    # Reddit
    {"name": "Reddit – r/Boilermakers",
     "url": "https://www.reddit.com/r/Boilermakers/.rss", "category": "reddit"},
    {"name": "Reddit – r/CollegeBasketball (Purdue search)",
     "url": "https://www.reddit.com/r/CollegeBasketball/search.rss?q=Purdue&restrict_sr=on&sort=new",
     "category": "reddit"},

    # YouTube (replace IDs later if desired)
    {"name": "YouTube – Purdue MBB Playlist",
     "url": "https://www.youtube.com/feeds/videos.xml?playlist_id=PLxxxxxxxxxxxx", "category": "youtube"},
    {"name": "YouTube – Sleepers Media (channel)",
     "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCxxxxxxxxxxxx", "category": "youtube"},
]

FEEDS = [(f["name"], f["url"]) for f in FEEDS_META]

STATIC_LINKS = [
    {"label": "Purdue – Official MBB Page", "url": "https://purduesports.com/sports/mens-basketball"},
    {"label": "Purdue – Schedule", "url": "https://purduesports.com/sports/mens-basketball/schedule"},
    {"label": "Purdue – Roster", "url": "https://purduesports.com/sports/mens-basketball/roster"},
    {"label": "ESPN – Purdue MBB", "url": "https://www.espn.com/mens-college-basketball/team/_/id/2509/purdue-boilermakers"},
    {"label": "CBS Sports – Purdue", "url": "https://www.cbssports.com/college-basketball/teams/PURDUE/purdue-boilermakers/"},
    {"label": "Yahoo Sports – Purdue", "url": "https://sports.yahoo.com/ncaab/teams/purdue/"},
    {"label": "Hammer & Rails (SB Nation)", "url": "https://www.hammerandrails.com/"},
    {"label": "GoldandBlack (Rivals)", "url": "https://purdue.rivals.com/"},
    {"label": "Barstool – Purdue", "url": "https://www.barstoolsports.com/topics/purdue"},
    {"label": "Reddit – r/Boilermakers", "url": "https://www.reddit.com/r/Boilermakers/"},
]
