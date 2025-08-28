# feeds.py — Purdue MBB focused sources & helpers

# 🔎 Include/Exclude helpers for the collector
KEYWORDS_INCLUDE = [
    # Program & staff
    "purdue", "boilermaker", "boilermakers", "purdue basketball", "boilerball",
    "matt painter", "mackey arena", "west lafayette", "big ten",

    # 2025–26 roster (names & common variants)
    "c.j. cox", "cj cox",
    "antione west jr", "antione west",
    "fletcher loyer",
    "braden smith",
    "trey kaufman-renn", "tre kaufman-renn",
    "liam murphy",
    "aaron fine",
    "sam king",
    "jack lusk",
    "daniel jacobsen",
    "jack benter",
    "omer mayer",
    "gicarri harris",
    "jace rayl",
    "raleigh burgess",
    "oscar cluff",
]

KEYWORDS_EXCLUDE = [
    "football", "nfl", "qb", "quarterback",
    "wide receiver", "running back", "linebacker",
    "tailgate", "gridiron",
    "draftkings", "fantasy football",
    "ncaa volleyball", "ncaa baseball", "softball", "soccer", "wrestling",
]

# 📰 Dynamic feeds (RSS/Atom) — BoilerBall remains removed
FEEDS_META = [
    # --- News aggregators (already scoped to Purdue by query) ---
    {"name": "Google News – Purdue Basketball",
     "url": "https://news.google.com/rss/search?q=Purdue+Basketball&hl=en-US&gl=US&ceid=US:en",
     "category": "news"},
    {"name": "Bing News – Purdue Basketball",
     "url": "https://www.bing.com/news/search?q=Purdue+Basketball&format=RSS",
     "category": "news"},

    # --- Reddit ---
    {"name": "Reddit – r/Boilermakers", "url": "https://www.reddit.com/r/Boilermakers/.rss", "category": "reddit"},
    {"name": "Reddit – r/CollegeBasketball (Purdue search)",
     "url": "https://www.reddit.com/r/CollegeBasketball/search.rss?q=Purdue&restrict_sr=on&sort=new", "category": "reddit"},

    # --- YouTube channels (RSS by channel_id) ---
    {"name": "YouTube – Field of 68",
     "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCs7L0m8JMXwPP0zJX9v3ePQ", "category": "youtube"},
    {"name": "YouTube – Sleepers Media",
     "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCUsGjUPB5GQU9H8H1zZX95g", "category": "youtube"},

    # --- Official / Team ---
    {"name": "Purdue Athletics – Men’s Basketball",
     "url": "https://purduesports.com/rss.aspx?path=mbball", "category": "official"},

    # --- Media / Blogs ---
    {"name": "Barstool – Purdue tag",
     "url": "https://www.barstoolsports.com/feed/tag/purdue", "category": "media"},
]

# Simple list for older collectors (name, url)
FEEDS = [(f["name"], f["url"]) for f in FEEDS_META]

# 🔗 Static quick links used by the UI — BoilerBall removed previously
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
