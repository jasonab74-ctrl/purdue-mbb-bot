# feeds.py — Purdue Men's Basketball sources (cleaned)

# ---------- Quick-link buttons shown on the site ----------
# Order here = order shown (left-to-right, top-to-bottom)
STATIC_LINKS = [
    {"label": "Betting Odds",      "url": "https://sportsbook.draftkings.com/leagues/basketball/1035?category=game-lines"},
    {"label": "Official Site",     "url": "https://purduesports.com/sports/mens-basketball"},
    {"label": "Schedule",          "url": "https://purduesports.com/sports/mens-basketball/schedule"},
    {"label": "Roster",            "url": "https://purduesports.com/sports/mens-basketball/roster"},

    {"label": "ESPN",              "url": "https://www.espn.com/mens-college-basketball/team/_/id/2509/purdue-boilermakers"},
    {"label": "CBS Sports",        "url": "https://www.cbssports.com/college-basketball/teams/PURDUE/purdue-boilermakers/"},
    {"label": "Yahoo Sports",      "url": "https://sports.yahoo.com/ncaab/teams/purdue/"},

    {"label": "Hammer & Rails",    "url": "https://www.hammerandrails.com/"},
    {"label": "Gold and Black",    "url": "https://goldandblack.com/"},
    {"label": "Purdue Exponent",   "url": "https://www.purdueexponent.org/sports/"},
    {"label": "Journal & Courier", "url": "https://www.jconline.com/sports/college/purdue/"},
    {"label": "Barstool",          "url": "https://www.barstoolsports.com/tag/purdue-boilermakers"},
    {"label": "Reddit",            "url": "https://www.reddit.com/r/Boilermakers/"},
    {"label": "YouTube – Field of 68", "url": "https://www.youtube.com/@TheFieldOf68"},
    {"label": "YouTube – Sleepers Media", "url": "https://www.youtube.com/@SleepersMedia"},
]

# ---------- Feeds consumed by collect.py ----------
# type must be one of: "rss" (default), "google", "bing", "reddit"
FEEDS = [
    # Official / trusted (lenient filtering if you choose to add that later)
    {"name": "PurdueSports.com — Men’s Basketball", "type": "rss",
     "url": "https://purduesports.com/rss.aspx?path=mbball", "trust": True},
    {"name": "ESPN Purdue MBB", "type": "rss",
     "url": "https://www.espn.com/espn/rss/ncb/team?teamId=2509", "trust": True},

    # Blogs / media
    {"name": "Hammer & Rails (SB Nation)", "type": "rss",
     "url": "https://www.hammerandrails.com/rss/index.xml", "trust": True},
    {"name": "GoldandBlack (Rivals)", "type": "rss",
     "url": "https://purdue.rivals.com/rss"},

    # Aggregators
    {"name": "Google News — Purdue Basketball", "type": "google",
     "url": "https://news.google.com/rss/search?q=Purdue%20basketball%20OR%20%22Purdue%20Boilermakers%22%20basketball&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Google News — Matt Painter", "type": "google",
     "url": "https://news.google.com/rss/search?q=%22Matt%20Painter%22%20Purdue&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Bing News — Purdue Basketball", "type": "bing",
     "url": "https://www.bing.com/news/search?q=Purdue%20basketball&format=RSS"},
    {"name": "Bing News — Big Ten + Purdue", "type": "bing",
     "url": "https://www.bing.com/news/search?q=Purdue%20basketball%20Big%20Ten&format=RSS"},

    # Local / campus via Bing site filters
    {"name": "Journal & Courier Purdue", "type": "bing",
     "url": "https://www.bing.com/news/search?q=site:jconline.com%20Purdue%20basketball&format=RSS"},
    {"name": "Purdue Exponent — Men’s Basketball", "type": "bing",
     "url": "https://www.bing.com/news/search?q=site:purdueexponent.org%20(Purdue%20men%27s%20basketball%20OR%20MBB)&format=RSS"},
    {"name": "IndyStar Purdue", "type": "bing",
     "url": "https://www.bing.com/news/search?q=site:indystar.com%20Purdue%20basketball&format=RSS"},

    # National sites (site-scoped)
    {"name": "Yahoo Sports — Purdue", "type": "bing",
     "url": "https://www.bing.com/news/search?q=site:sports.yahoo.com%20Purdue%20basketball&format=RSS"},
    {"name": "CBS Sports — Purdue", "type": "bing",
     "url": "https://www.bing.com/news/search?q=site:cbssports.com%20Purdue%20basketball&format=RSS"},
    {"name": "Sports Illustrated — Purdue", "type": "bing",
     "url": "https://www.bing.com/news/search?q=site:si.com%20Purdue%20basketball&format=RSS"},

    # Reddit (JSON endpoints; collect.py supports this)
    {"name": "Reddit — r/Boilermakers", "type": "reddit",
     "url": "https://www.reddit.com/r/Boilermakers/.json?limit=100"},
    {"name": "Reddit — r/CollegeBasketball (Purdue search)", "type": "reddit",
     "url": "https://www.reddit.com/r/CollegeBasketball/search.json?q=Purdue%20basketball&restrict_sr=on&sort=new&t=year"},
]
