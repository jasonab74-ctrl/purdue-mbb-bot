# feeds.py
# -------------------------------------------------------------------
# Purdue MBB Live Feed — complete, paste-in file
# Focused on Men's Basketball; excludes football & other sports noise.
# -------------------------------------------------------------------

# 🧭 Quick links (always-visible pills)
STATIC_LINKS = [
    {"label": "Purdue – Official MBB Page", "url": "https://purduesports.com/sports/mens-basketball"},
    {"label": "Purdue – Schedule",          "url": "https://purduesports.com/sports/mens-basketball/schedule"},
    {"label": "Purdue – Roster",            "url": "https://purduesports.com/sports/mens-basketball/roster"},
    {"label": "ESPN – Purdue MBB",          "url": "https://www.espn.com/mens-college-basketball/team/_/id/2509/purdue-boilermakers"},
    {"label": "CBS Sports – Purdue",        "url": "https://www.cbssports.com/college-basketball/teams/PUR/purdue-boilermakers/"},
    {"label": "Yahoo Sports – Purdue",      "url": "https://sports.yahoo.com/ncaab/teams/purdue/"},
    {"label": "Hammer & Rails (SB Nation)", "url": "https://www.hammerandrails.com/"},
    {"label": "GoldandBlack (Rivals)",      "url": "https://purdue.rivals.com/"},
    {"label": "Barstool – Purdue",          "url": "https://www.barstoolsports.com/topics/purdue-boilermakers"},
    {"label": "Reddit – r/Boilermakers",    "url": "https://www.reddit.com/r/Boilermakers/"},
    {"label": "YouTube – Field of 68",      "url": "https://www.youtube.com/@thefieldof68"},
    {"label": "YouTube – Sleepers Media",   "url": "https://www.youtube.com/@SleepersMedia"},
]

# 📰 Feeds to collect (articles + YouTube mentions)
# Notes:
# - YouTube search RSS doesn’t exist; we use Google News scoped to youtube.com.
# - Several site-scoped Google News queries broaden coverage.
FEEDS = [
    # Broad MBB searches
    {"name": "Google News — Purdue Basketball",               "url": "https://news.google.com/rss/search?q=Purdue%20Basketball&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Google News — Purdue Boilermakers MBB",         "url": "https://news.google.com/rss/search?q=%22Purdue%20Boilermakers%22%20%22men%27s%20basketball%22&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Google News — Matt Painter",                    "url": "https://news.google.com/rss/search?q=%22Matt%20Painter%22%20Purdue&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Google News — Mackey Arena",                    "url": "https://news.google.com/rss/search?q=%22Mackey%20Arena%22%20Purdue&hl=en-US&gl=US&ceid=US:en"},

    # YouTube mentions (video links surface via Google News)
    {"name": "YouTube Mentions — Purdue Basketball",          "url": "https://news.google.com/rss/search?q=Purdue%20Basketball%20site:youtube.com&hl=en-US&gl=US&ceid=US:en"},
    {"name": "YouTube Mentions — Matt Painter",               "url": "https://news.google.com/rss/search?q=%22Matt%20Painter%22%20site:youtube.com&hl=en-US&gl=US&ceid=US:en"},

    # Team/community & local/state coverage (via RSS or site-scoped GN)
    {"name": "Hammer & Rails (SB Nation)",                    "url": "https://www.hammerandrails.com/rss/index.xml"},
    {"name": "Google News — GoldandBlack (Rivals)",           "url": "https://news.google.com/rss/search?q=site:purdue.rivals.com%20basketball&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Google News — On3 Purdue",                      "url": "https://news.google.com/rss/search?q=site:on3.com/teams/purdue-boilermakers/%20basketball&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Google News — 247Sports Purdue",                "url": "https://news.google.com/rss/search?q=site:247sports.com/college/purdue/%20basketball&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Google News — IndyStar Purdue",                 "url": "https://news.google.com/rss/search?q=site:indystar.com%20Purdue%20Basketball&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Google News — Sports Illustrated Purdue",       "url": "https://news.google.com/rss/search?q=site:si.com%20Purdue%20Basketball&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Google News — USA Today Purdue",                "url": "https://news.google.com/rss/search?q=site:usatoday.com%20Purdue%20Basketball&hl=en-US&gl=US&ceid=US:en"},

    # Official athletics via GN (since site RSS is inconsistent)
    {"name": "Google News — PurdueSports.com (MBB)",          "url": "https://news.google.com/rss/search?q=site:purduesports.com%20%22Men%27s%20Basketball%22&hl=en-US&gl=US&ceid=US:en"},

    # Reddit (filtered to require Purdue mention in title for r/CollegeBasketball)
    {"name": "Reddit — r/Boilermakers",                       "url": "https://www.reddit.com/r/Boilermakers/.rss"},
    {"name": "Reddit — r/CollegeBasketball",                  "url": "https://www.reddit.com/r/CollegeBasketball/.rss"},
]

# ✅ Include terms (at least one required — case-insensitive)
KEYWORDS_INCLUDE = [
    "purdue", "boilermakers", "boilermaker", "boilerball",
    "men’s basketball", "mens basketball", "men's basketball", "college basketball", "ncaa",
    "mackey arena", "matt painter", "painter",
    # Useful player/program words (harmless if absent)
    "braden smith", "fletcher loyer", "lance jones", "trey kaufman", "mason gillis",
    "zach edey", "caleb first", "myles colvin",
    "tipoff", "big ten", "b1g", "march madness", "ncaa tournament", "recruit", "commit", "transfer portal",
]

# 🚫 Exclude terms (football & non-MBB noise only; avoid generic “defense/offense”)
KEYWORDS_EXCLUDE = [
    # football identifiers/positions/terms
    "football", "cfb", "gridiron", "helmet", "pigskin",
    "quarterback", "qb", "running back", "rb", "wide receiver", "wr", "tight end", "te",
    "linebacker", "lb", "cornerback", "cb", "safety", "edge", "defensive end", "de", "nose tackle",
    "offensive line", "offensive lineman", "defensive line", "defensive lineman",
    "kickoff", "punt", "field goal", "touchdown", "two-point conversion", "extra point",
    "rushing yards", "passing yards", "sack", "scrimmage", "spring game", "fall camp",
    "depth chart", "preseason poll (football)", "pro day", "nfl", "combine",

    # other sports
    "baseball", "softball", "volleyball", "soccer", "wrestling",
    "track and field", "cross country", "golf", "tennis", "swimming",

    # women's team (to keep feed strictly men's; adjust if you want both)
    "women’s basketball", "womens basketball", "women's basketball",
]

# 🔧 Collector knobs
MAX_ITEMS_PER_FEED = 80             # generous per-source cap
ALLOW_DUPLICATE_DOMAINS = False     # use a small per-domain cap instead
DOMAIN_PER_FEED_LIMIT = 3           # allow up to N items per domain per feed pass

# Optional friendly renames
SOURCE_ALIASES = {
    "Hammer & Rails (SB Nation)": "Hammer & Rails",
    "Reddit — r/Boilermakers": "Reddit r/Boilermakers",
    "Reddit — r/CollegeBasketball": "Reddit r/CollegeBasketball",
}
