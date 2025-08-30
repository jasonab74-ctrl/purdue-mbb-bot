# feeds.py — Purdue Men's Basketball sources (buttons + feeds)
# ------------------------------------------------------------
# Exposes:
#   STATIC_LINKS   -> list[{label,url}]
#   FEEDS_META     -> list[{name,url,category}]
#   FEEDS          -> list[(name,url)]  (for collectors expecting a tuple list)
# Optional topic guards (used by some collectors):
KEYWORDS_INCLUDE = [
    "purdue", "boilermakers", "boilerball", "purdue men's basketball", "purdue mbb",
    "mackey arena", "west lafayette", "big ten", "b1g",
    "matt painter", "assistant coach",
    # common hoops terms
    "basketball", "mbb", "guard", "forward", "center", "three-pointer", "assist",
    "rebound", "kenpom", "net ranking", "ncaa tournament", "march madness",
]
KEYWORDS_EXCLUDE = [
    # filter non-hoops noise
    "football", "nfl", "qb", "quarterback", "running back", "wide receiver",
    "linebacker", "tight end", "touchdown", "field goal", "kickoff", "bowl",
    "odds", "parlay", "spread", "fanduel", "draftkings",
    "volleyball", "wrestling", "baseball", "softball", "soccer", "hockey",
    "golf", "tennis", "track", "cross country", "swim", "diving", "gymnastics",
]

# 🔗 Buttons / “Sites” dropdown entries (always visible in UI)
STATIC_LINKS = [
    # --- Official Purdue Athletics ---
    {"label": "Purdue – Official MBB Page", "url": "https://purduesports.com/sports/mens-basketball"},
    {"label": "Purdue – Schedule", "url": "https://purduesports.com/sports/mens-basketball/schedule"},
    {"label": "Purdue – Roster", "url": "https://purduesports.com/sports/mens-basketball/roster"},

    # --- National Sports Sites ---
    {"label": "ESPN – Purdue MBB", "url": "https://www.espn.com/mens-college-basketball/team/_/id/2509/purdue-boilermakers"},
    {"label": "CBS Sports – Purdue", "url": "https://www.cbssports.com/college-basketball/teams/PUR/purdue-boilermakers/"},
    {"label": "Yahoo Sports – Purdue", "url": "https://sports.yahoo.com/ncaab/teams/purdue/"},

    # --- Blogs & Media ---
    {"label": "Hammer & Rails (SB Nation)", "url": "https://www.hammerandrails.com/"},
    {"label": "GoldandBlack (Rivals)", "url": "https://purdue.rivals.com/"},
    {"label": "Barstool – Purdue", "url": "https://www.barstoolsports.com/tag/purdue"},

    # --- Reddit ---
    {"label": "Reddit – r/Boilermakers", "url": "https://www.reddit.com/r/Boilermakers/"},
    {"label": "Reddit – r/CollegeBasketball", "url": "https://www.reddit.com/r/CollegeBasketball/"},

    # --- YouTube Channels ---
    {"label": "YouTube – BoilerBall (Official)", "url": "https://www.youtube.com/@BoilerBall"},
    {"label": "YouTube – Field of 68", "url": "https://www.youtube.com/@TheFieldOf68"},
    {"label": "YouTube – Sleepers Media", "url": "https://www.youtube.com/@SleepersMedia"},
]

# 📰 Dynamic feeds the collector reads (RSS/Atom)
FEEDS_META = [
    # News aggregators
    {"name": "Google News – Purdue Basketball",
     "url": "https://news.google.com/rss/search?q=Purdue+Basketball&hl=en-US&gl=US&ceid=US:en",
     "category": "news"},
    {"name": "Bing News – Purdue Basketball",
     "url": "https://www.bing.com/news/search?q=Purdue+Basketball&format=RSS",
     "category": "news"},

    # Reddit
    {"name": "Reddit – r/Boilermakers",
     "url": "https://www.reddit.com/r/Boilermakers/.rss",
     "category": "reddit"},
    {"name": "Reddit – r/CollegeBasketball (Purdue search)",
     "url": "https://www.reddit.com/r/CollegeBasketball/search.rss?q=Purdue&restrict_sr=on&sort=new",
     "category": "reddit"},

    # YouTube (channel RSS by channel_id)
    {"name": "YouTube – BoilerBall (Official)",
     "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCQzI9QfpbJ9y4CQfA3z0H_g",
     "category": "youtube"},
    {"name": "YouTube – Field of 68",
     "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCs7L0m8JMXwPP0zJX9v3ePQ",
     "category": "youtube"},
    {"name": "YouTube – Sleepers Media",
     "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCUsGjUPB5GQU9H8H1zZX95g",
     "category": "youtube"},

    # Official / team
    {"name": "Purdue Athletics – Men’s Basketball",
     "url": "https://purduesports.com/rss.aspx?path=mbball",
     "category": "official"},

    # Blogs & Media
    {"name": "Barstool – Purdue",
     "url": "https://www.barstoolsports.com/feed/tag/purdue",
     "category": "media"},
]

# Back-compat simple list
FEEDS = [(f["name"], f["url"]) for f in FEEDS_META]
