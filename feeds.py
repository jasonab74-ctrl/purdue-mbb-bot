# feeds.py — Purdue MBB Live Feed (basketball-only, broadened with "boilers")

# Quick links (UI pills)
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

# Feeds (Google News scoped + direct RSS where possible)
# YouTube search RSS doesn’t exist; use Google News with site:youtube.com.
FEEDS = [
    # Broad Purdue MBB queries
    {"name": "Google News — Purdue Basketball",         "url": "https://news.google.com/rss/search?q=Purdue%20Basketball&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Google News — Purdue Boilermakers MBB",   "url": "https://news.google.com/rss/search?q=%22Purdue%20Boilermakers%22%20%22men%27s%20basketball%22&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Google News — Boilers (Basketball)",      "url": "https://news.google.com/rss/search?q=Boilers%20Purdue%20basketball&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Google News — Matt Painter",              "url": "https://news.google.com/rss/search?q=%22Matt%20Painter%22%20Purdue&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Google News — Mackey Arena",              "url": "https://news.google.com/rss/search?q=%22Mackey%20Arena%22%20Purdue&hl=en-US&gl=US&ceid=US:en"},

    # Wider NCAA/Big Ten context mentioning Purdue (adds volume but stays hoops)
    {"name": "Google News — Big Ten Basketball + Purdue", "url": "https://news.google.com/rss/search?q=%22Big%20Ten%22%20basketball%20Purdue&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Google News — NCAA Tournament + Purdue",     "url": "https://news.google.com/rss/search?q=%22NCAA%20Tournament%22%20Purdue%20basketball&hl=en-US&gl=US&ceid=US:en"},

    # YouTube mentions (video links)
    {"name": "YouTube Mentions — Purdue Basketball",    "url": "https://news.google.com/rss/search?q=Purdue%20Basketball%20site:youtube.com&hl=en-US&gl=US&ceid=US:en"},
    {"name": "YouTube Mentions — Matt Painter",         "url": "https://news.google.com/rss/search?q=%22Matt%20Painter%22%20site:youtube.com&hl=en-US&gl=US&ceid=US:en"},

    # Team/community & local/state via site-scoped Google News
    {"name": "Hammer & Rails (SB Nation)",              "url": "https://www.hammerandrails.com/rss/index.xml"},
    {"name": "Google News — GoldandBlack (Rivals)",     "url": "https://news.google.com/rss/search?q=site:purdue.rivals.com%20basketball&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Google News — On3 Purdue",                "url": "https://news.google.com/rss/search?q=site:on3.com/teams/purdue-boilermakers/%20basketball&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Google News — 247Sports Purdue",          "url": "https://news.google.com/rss/search?q=site:247sports.com/college/purdue/%20basketball&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Google News — IndyStar Purdue",           "url": "https://news.google.com/rss/search?q=site:indystar.com%20Purdue%20Basketball&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Google News — Sports Illustrated Purdue", "url": "https://news.google.com/rss/search?q=site:si.com%20Purdue%20Basketball&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Google News — USA Today Purdue",          "url": "https://news.google.com/rss/search?q=site:usatoday.com%20Purdue%20Basketball&hl=en-US&gl=US&ceid=US:en"},

    # Official athletics (GN-scraped; native RSS inconsistent)
    {"name": "Google News — PurdueSports.com (MBB)",    "url": "https://news.google.com/rss/search?q=site:purduesports.com%20%22Men%27s%20Basketball%22&hl=en-US&gl=US&ceid=US:en"},

    # Reddit (CBB feed requires 'Purdue' in title; enforced in collector)
    {"name": "Reddit — r/Boilermakers",                 "url": "https://www.reddit.com/r/Boilermakers/.rss"},
    {"name": "Reddit — r/CollegeBasketball",            "url": "https://www.reddit.com/r/CollegeBasketball/.rss"},
]

# Include terms (at least one; broadened with “boilers” and variants)
KEYWORDS_INCLUDE = [
    # school/program nicknames
    "purdue", "boilers", "boilermakers", "boilermaker", "boilerball",
    # sport
    "men’s basketball", "mens basketball", "men's basketball", "college basketball", "ncaa",
    # context
    "big ten", "b1g", "mackey arena", "matt painter", "painter",
    "ranked", "preseason", "scrimmage", "exhibition", "tipoff",
    "recruit", "commit", "transfer portal", "bracket", "seed",
    # players (non-exhaustive; harmless if absent)
    "zach edey", "braden smith", "fletcher loyer", "lance jones",
    "trey kaufman", "mason gillis", "caleb first", "myles colvin",
]

# Exclude terms (football & other sports; keep hoops generic words)
KEYWORDS_EXCLUDE = [
    # football identifiers/positions/terms
    "football", "cfb", "gridiron",
    "quarterback", "qb", "running back", "rb", "wide receiver", "wr", "tight end", "te",
    "linebacker", "lb", "cornerback", "cb", "safety", "edge", "defensive end", "de", "nose tackle",
    "offensive line", "defensive line",
    "kickoff", "punt", "field goal", "touchdown", "two-point conversion", "extra point",
    "rushing yards", "passing yards", "sack", "spring game", "fall camp", "depth chart",
    "nfl", "combine", "pro day",

    # other sports
    "baseball", "softball", "volleyball", "soccer", "wrestling",
    "track and field", "cross country", "golf", "tennis", "swimming",

    # women’s team (strict men’s-only site)
    "women’s basketball", "womens basketball", "women's basketball",
]

# Collector knobs
MAX_ITEMS_PER_FEED = 120            # generous cap to reach 80–150 overall
ALLOW_DUPLICATE_DOMAINS = False
DOMAIN_PER_FEED_LIMIT = 4           # avoid floods from a single domain

SOURCE_ALIASES = {
    "Hammer & Rails (SB Nation)": "Hammer & Rails",
    "Reddit — r/Boilermakers": "Reddit r/Boilermakers",
    "Reddit — r/CollegeBasketball": "Reddit r/CollegeBasketball",
}
