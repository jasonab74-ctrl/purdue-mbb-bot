# feeds.py
# -------------------------------------------------------------------
# Purdue MBB Live Feed — complete, paste-in file
# Layout-agnostic. Safe to drop in without touching server/collector.
# -------------------------------------------------------------------

# 🧭 Quick links (always-visible pill buttons in the UI)
STATIC_LINKS = [
    # --- Official Purdue Athletics ---
    {"label": "Purdue – Official MBB Page", "url": "https://purduesports.com/sports/mens-basketball"},
    {"label": "Purdue – Schedule",          "url": "https://purduesports.com/sports/mens-basketball/schedule"},
    {"label": "Purdue – Roster",            "url": "https://purduesports.com/sports/mens-basketball/roster"},

    # --- Major Sports Sites ---
    {"label": "ESPN – Purdue MBB",          "url": "https://www.espn.com/mens-college-basketball/team/_/id/2509/purdue-boilermakers"},
    {"label": "CBS Sports – Purdue",        "url": "https://www.cbssports.com/college-basketball/teams/PUR/purdue-boilermakers/"},
    {"label": "Yahoo Sports – Purdue",      "url": "https://sports.yahoo.com/ncaab/teams/purdue/"},

    # --- Community / Coverage ---
    {"label": "Hammer & Rails (SB Nation)", "url": "https://www.hammerandrails.com/"},
    {"label": "GoldandBlack (Rivals)",      "url": "https://purdue.rivals.com/"},
    {"label": "Barstool – Purdue",          "url": "https://www.barstoolsports.com/topics/purdue-boilermakers"},

    # --- Social / Video ---
    {"label": "Reddit – r/Boilermakers",    "url": "https://www.reddit.com/r/Boilermakers/"},
    {"label": "Reddit – r/CollegeBasketball","url": "https://www.reddit.com/r/CollegeBasketball/"},
    {"label": "YouTube – BoilerBall (Official)", "url": "https://www.youtube.com/@BoilerBall"},
    {"label": "YouTube – Field of 68",      "url": "https://www.youtube.com/@thefieldof68"},
    {"label": "YouTube – Sleepers Media",   "url": "https://www.youtube.com/@SleepersMedia"},
]

# 📰 Feeds to collect (articles + video mentions)
# Notes:
# - YouTube search RSS does not exist; we use Google News RSS scoped to youtube.com.
# - Collector should use the "name" for source badges and the "url" to fetch.
FEEDS = [
    # ------ Google News scoped searches (broad but relevant) ------
    {"name": "Google News — Purdue Basketball", "url": "https://news.google.com/rss/search?q=Purdue%20Basketball&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Google News — Matt Painter",      "url": "https://news.google.com/rss/search?q=%22Matt%20Painter%22%20Purdue&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Google News — Mackey Arena",      "url": "https://news.google.com/rss/search?q=%22Mackey%20Arena%22%20Purdue&hl=en-US&gl=US&ceid=US:en"},

    # ------ Google News → YouTube mentions (video-first without channel IDs) ------
    {"name": "YouTube Mentions — Purdue Basketball", "url": "https://news.google.com/rss/search?q=Purdue%20Basketball%20site:youtube.com&hl=en-US&gl=US&ceid=US:en"},
    {"name": "YouTube Mentions — Matt Painter",      "url": "https://news.google.com/rss/search?q=%22Matt%20Painter%22%20site:youtube.com&hl=en-US&gl=US&ceid=US:en"},

    # ------ Team/community sites ------
    {"name": "Hammer & Rails (SB Nation)",     "url": "https://www.hammerandrails.com/rss/index.xml"},
    # Rivals/On3 often lack public RSS; catch them via Google News:
    {"name": "Google News — GoldandBlack (Rivals)", "url": "https://news.google.com/rss/search?q=site:purdue.rivals.com%20Purdue%20Basketball&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Google News — On3 Purdue",             "url": "https://news.google.com/rss/search?q=site:on3.com/teams/purdue-boilermakers/%20basketball&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Google News — 247Sports Purdue",       "url": "https://news.google.com/rss/search?q=site:247sports.com/college/purdue/%20basketball&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Google News — IndyStar Purdue",        "url": "https://news.google.com/rss/search?q=site:indystar.com%20Purdue%20Basketball&hl=en-US&gl=US&ceid=US:en"},

    # ------ Official athletics domain (captured via Google News) ------
    {"name": "Google News — PurdueSports.com (MBB)", "url": "https://news.google.com/rss/search?q=site:purduesports.com%20%22Men%27s%20Basketball%22&hl=en-US&gl=US&ceid=US:en"},

    # ------ Reddit (broad; will be filtered by include keywords) ------
    {"name": "Reddit — r/Boilermakers",        "url": "https://www.reddit.com/r/Boilermakers/.rss"},
    {"name": "Reddit — r/CollegeBasketball",   "url": "https://www.reddit.com/r/CollegeBasketball/.rss"},
]

# ✅ Include terms (must match at least one — case-insensitive)
# Keep this generous for basketball while excluding football below.
KEYWORDS_INCLUDE = [
    # program
    "purdue", "boilermakers", "boilermaker", "boilerball",
    "men’s basketball", "mens basketball", "men's basketball", "college basketball", "ncaa",
    # venue / coach
    "mackey arena", "matt painter", "painter",
    # players / common roster names (past & present; harmless if absent)
    "braden smith", "fletcher loyer", "lance jones", "trey kaufman", "mason gillis",
    "zach edey", "caleb first", "myles colvin", "purdue guard", "purdue forward", "purdue center",
    # game terms
    "tipoff", "big ten", "b1g", "march madness", "ncaa tournament", "nonconference",
    "preseason", "exhibition", "scrimmage", "recruit", "commit", "transfer portal",
]

# 🚫 Exclude terms (remove football and other sports noise)
KEYWORDS_EXCLUDE = [
    # football
    "football", "cfb", "quarterback", "qb", "running back", "wide receiver", "tight end",
    "linebacker", "offensive line", "defensive line", "kickoff return", "punt return",
    "nfl", "draft combine", "spring game",
    # other sports
    "baseball", "softball", "volleyball", "soccer", "golf", "tennis", "wrestling",
    "track and field", "swim", "swimming", "cross country",
    # obvious unrelated
    "women’s", "womens", "women's soccer", "women's volleyball",
]

# 🔧 Optional knobs used by some collectors (safe defaults)
MAX_ITEMS_PER_FEED = 50           # soft cap per source before sorting/merge
ALLOW_DUPLICATE_DOMAINS = False   # if collector supports domain-based dedupe

# Some collectors map friendly source names; harmless if unused.
SOURCE_ALIASES = {
    "Google News — Purdue Basketball": "Google News – Purdue Basketball",
    "YouTube Mentions — Purdue Basketball": "YouTube (mentions)",
    "YouTube Mentions — Matt Painter": "YouTube (mentions)",
    "Reddit — r/Boilermakers": "Reddit r/Boilermakers",
    "Reddit — r/CollegeBasketball": "Reddit r/CollegeBasketball",
    "Hammer & Rails (SB Nation)": "Hammer & Rails",
}
