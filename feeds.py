# feeds.py — Purdue Men's Basketball (Purdue MBB) sources
# ------------------------------------------------------------
# Exposes:
#   FEEDS, FEEDS_META, STATIC_LINKS, KEYWORDS_INCLUDE, KEYWORDS_EXCLUDE

KEYWORDS_INCLUDE = [
    "purdue", "boilermakers", "boilerball", "purdue mbb", "purdue men's basketball",
    "mackey arena", "west lafayette", "big ten", "b1g",
    "matt painter", "assistant coach",
    # current roster core (adjust as roster changes)
    "braden smith", "fletcher loyer", "trey kaufman-renn", "camden heide",
    "caleb furst", "myles colvin", "will berg",
    # notable recent alumni to catch retrospectives
    "zach edey", "lance jones", "mason gillis",
    "recruit", "commit", "transfer portal", "ncaa tournament", "march madness",
    "guard", "forward", "center", "three-pointer", "assist", "rebound", "kenpom", "net ranking"
]

KEYWORDS_EXCLUDE = [
    # football
    "football", "nfl", "qb", "quarterback", "running back", "wide receiver",
    "linebacker", "tight end", "touchdown", "field goal", "kickoff", "bowl",
    "draftkings", "fanduel", "fantasy football", "odds", "parlay", "spread",
    # other sports
    "volleyball", "wrestling", "baseball", "softball", "soccer", "hockey",
    "golf", "tennis", "track", "cross country", "swim", "diving", "gymnastics",
]

FEEDS_META = [
    # Aggregators
    {"name": "Google News – Purdue Basketball",
     "url": "https://news.google.com/rss/search?q=Purdue+Basketball&hl=en-US&gl=US&ceid=US:en",
     "category": "news"},
    {"name": "Bing News – Purdue Basketball",
     "url": "https://www.bing.com/news/search?q=Purdue+Basketball&format=RSS",
     "category": "news"},
    {"name": "Yahoo Sports – Purdue (via Bing)",
     "url": "https://www.bing.com/news/search?q=site:sports.yahoo.com+Purdue+Basketball&format=RSS",
     "category": "news"},

    # Reddit
    {"name": "Reddit – r/Boilermakers",
     "url": "https://www.reddit.com/r/Boilermakers/.rss",
     "category": "reddit"},
    {"name": "Reddit – r/CollegeBasketball (Purdue search)",
     "url": "https://www.reddit.com/r/CollegeBasketball/search.rss?q=Purdue&restrict_sr=on&sort=new",
     "category": "reddit"},

    # YouTube channels (RSS by channel_id)
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

    # Media / Blogs
    {"name": "Hammer & Rails (RSS)",
     "url": "https://www.hammerandrails.com/rss/index.xml",
     "category": "media"},
    {"name": "Barstool – Purdue tag",
     "url": "https://www.barstoolsports.com/feed/tag/purdue",
     "category": "media"},
]

FEEDS = [(f["name"], f["url"]) for f in FEEDS_META]

STATIC_LINKS = [
    {"label": "ESPN – Purdue MBB", "url": "https://www.espn.com/mens-college-basketball/team/_/id/2509/purdue-boilermakers"},
    {"label": "CBS – Purdue MBB", "url": "https://www.cbssports.com/college-basketball/teams/PUR/purdue-boilermakers/"},
    {"label": "Hammer & Rails", "url": "https://www.hammerandrails.com/"},
    {"label": "GoldandBlack", "url": "https://purdue.rivals.com/"},
    {"label": "Barstool – Purdue", "url": "https://www.barstoolsports.com/tag/purdue"},
    {"label": "Purdue – Schedule", "url": "https://purduesports.com/sports/mens-basketball/schedule"},
    {"label": "Purdue – Roster", "url": "https://purduesports.com/sports/mens-basketball/roster"},
    {"label": "Reddit – r/Boilermakers", "url": "https://www.reddit.com/r/Boilermakers/"},
    {"label": "YouTube – Field of 68", "url": "https://www.youtube.com/@TheFieldOf68"},
    {"label": "YouTube – Sleepers Media", "url": "https://www.youtube.com/@SleepersMedia"}
]
