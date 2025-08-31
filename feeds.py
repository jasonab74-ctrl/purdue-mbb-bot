# feeds.py
# Static + dynamic sources for dropdowns and feed collection

# 🔗 Quick Links (shown as pills in the site UI)
STATIC_LINKS = [
    # Betting odds (DraftKings first)
    {"label": "Betting Odds", "url": "https://sportsbook.draftkings.com/leagues/basketball/1035?category=game-lines"},

    # Official Purdue Athletics
    {"label": "Official Site", "url": "https://purduesports.com/sports/mens-basketball"},
    {"label": "Schedule", "url": "https://purduesports.com/sports/mens-basketball/schedule"},
    {"label": "Roster", "url": "https://purduesports.com/sports/mens-basketball/roster"},

    # National sports sites
    {"label": "ESPN", "url": "https://www.espn.com/mens-college-basketball/team/_/id/2509/purdue-boilermakers"},
    {"label": "CBS Sports", "url": "https://www.cbssports.com/college-basketball/teams/PURDUE/purdue-boilermakers/"},
    {"label": "Yahoo Sports", "url": "https://sports.yahoo.com/ncaab/teams/purdue/"},
]

# 📡 Feeds (Google, Bing, Reddit, YouTube, etc.)
FEEDS = [
    # Example trusted feeds — keep or expand as needed
    {"name": "Purdue Official RSS", "url": "https://purduesports.com/rss?path=mbball", "type": "rss", "trust": True},
    {"name": "ESPN Purdue MBB", "url": "https://www.espn.com/espn/rss/ncb/team?teamId=2509", "type": "rss", "trust": True},

    # Reddit
    {"name": "Reddit /r/CollegeBasketball", "url": "https://www.reddit.com/r/CollegeBasketball/search.json?q=Purdue&restrict_sr=on&sort=new", "type": "reddit"},

    # Google/Bing News (already filtered by query string)
    {"name": "Google News", "url": "https://news.google.com/rss/search?q=Purdue+Men%27s+Basketball&hl=en-US&gl=US&ceid=US:en", "type": "google"},
    {"name": "Bing News",   "url": "https://www.bing.com/news/search?q=Purdue+Men%27s+Basketball&format=RSS", "type": "bing"},
]
