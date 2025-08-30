# feeds.py — Purdue MBB Live Feed (basketball-only, with roster 2025–26 focus and Bing mirrors)

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

# Helpers to define mirrored news feeds
def GN(q: str) -> dict:
    return {"name": f"Google News — {q}", "url": f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"}

def BN(q: str) -> dict:
    return {"name": f"Bing News — {q}", "url": f"https://www.bing.com/news/search?q={q}&format=rss"}

# Core encoded queries
Q_PU_MBB         = "Purdue%20Basketball"
Q_PU_BOILERS_MBB = "Boilers%20Purdue%20basketball"
Q_PU_BOILERMAKERS_MBB = "%22Purdue%20Boilermakers%22%20%22men%27s%20basketball%22"
Q_PAINTER        = "%22Matt%20Painter%22%20Purdue"
Q_MACKEY         = "%22Mackey%20Arena%22%20Purdue"
Q_B1G_PU         = "%22Big%20Ten%22%20basketball%20Purdue"
Q_NCAA_PU        = "%22NCAA%20Tournament%22%20Purdue%20basketball"

# YouTube mentions via news engines (YouTube has no search RSS)
Q_YT_PU          = "Purdue%20Basketball%20site:youtube.com"
Q_YT_PAINTER     = "%22Matt%20Painter%22%20site:youtube.com"

# Site-scoped
Q_RIVALS_PU      = "site:purdue.rivals.com%20basketball"
Q_ON3_PU         = "site:on3.com/teams/purdue-boilermakers/%20basketball"
Q_247_PU         = "site:247sports.com/college/purdue/%20basketball"
Q_INDYSTAR_PU    = "site:indystar.com%20Purdue%20Basketball"
Q_SI_PU          = "site:si.com%20Purdue%20Basketball"
Q_USATODAY_PU    = "site:usatoday.com%20Purdue%20Basketball"
Q_PURDUE_SPORTS  = "site:purduesports.com%20%22Men%27s%20Basketball%22"

# Roster 2025–26 emphasis (multiple spellings with hyphen/en dash/space)
Q_ROSTER_2526_1  = "Purdue%202025-26%20roster"
Q_ROSTER_2526_2  = "Purdue%202025%E2%80%9326%20roster"   # en dash
Q_ROSTER_2526_3  = "%22Purdue%22%202025%20roster%20basketball"
Q_ROSTER_2526_4  = "%22Purdue%22%202026%20roster%20basketball"
Q_ROSTER_2526_5  = "%22Purdue%22%20men%27s%20basketball%20roster%202025"
Q_RECRUIT_2025   = "%22Purdue%22%20basketball%20recruit%202025"
Q_RECRUIT_2026   = "%22Purdue%22%20basketball%20recruit%202026"
Q_CLASS_2025     = "%22class%20of%202025%22%20Purdue%20basketball"
Q_CLASS_2026     = "%22class%20of%202026%22%20Purdue%20basketball"
Q_PORTAL_PU      = "%22Purdue%22%20basketball%20transfer%20portal"

# Feeds: pair each Google News query with a Bing News mirror; keep direct RSS too
FEEDS = [
    # Broad program coverage
    GN("Purdue Basketball"),                           BN("Purdue Basketball"),
    GN("Boilers Purdue basketball"),                   BN("Boilers Purdue basketball"),
    GN("Purdue Boilermakers men's basketball"),        BN("Purdue Boilermakers men's basketball"),
    GN("Matt Painter Purdue"),                         BN("Matt Painter Purdue"),
    GN("Mackey Arena Purdue"),                         BN("Mackey Arena Purdue"),
    GN("Big Ten basketball Purdue"),                   BN("Big Ten basketball Purdue"),
    GN("NCAA Tournament Purdue basketball"),           BN("NCAA Tournament Purdue basketball"),

    # YouTube mentions
    GN("Purdue Basketball site:youtube.com"),          BN("Purdue Basketball site:youtube.com"),
    GN("Matt Painter site:youtube.com"),               BN("Matt Painter site:youtube.com"),

    # Site-scoped news
    GN("site:purdue.rivals.com basketball"),           BN("site:purdue.rivals.com basketball"),
    GN("site:on3.com/teams/purdue-boilermakers/ basketball"), BN("site:on3.com/teams/purdue-boilermakers/ basketball"),
    GN("site:247sports.com/college/purdue/ basketball"), BN("site:247sports.com/college/purdue/ basketball"),
    GN("site:indystar.com Purdue Basketball"),         BN("site:indystar.com Purdue Basketball"),
    GN("site:si.com Purdue Basketball"),               BN("site:si.com Purdue Basketball"),
    GN("site:usatoday.com Purdue Basketball"),         BN("site:usatoday.com Purdue Basketball"),
    GN("site:purduesports.com \"Men's Basketball\""),  BN("site:purduesports.com \"Men's Basketball\""),

    # Roster 2025–26 emphasis
    GN("Purdue 2025-26 roster"),                       BN("Purdue 2025-26 roster"),
    GN("Purdue 2025–26 roster"),                       BN("Purdue 2025–26 roster"),
    GN("\"Purdue\" 2025 roster basketball"),           BN("\"Purdue\" 2025 roster basketball"),
    GN("\"Purdue\" 2026 roster basketball"),           BN("\"Purdue\" 2026 roster basketball"),
    GN("\"Purdue\" men's basketball roster 2025"),     BN("\"Purdue\" men's basketball roster 2025"),
    GN("\"class of 2025\" Purdue basketball"),         BN("\"class of 2025\" Purdue basketball"),
    GN("\"class of 2026\" Purdue basketball"),         BN("\"class of 2026\" Purdue basketball"),
    GN("\"Purdue\" basketball transfer portal"),       BN("\"Purdue\" basketball transfer portal"),

    # Direct community feeds
    {"name": "Hammer & Rails (SB Nation)", "url": "https://www.hammerandrails.com/rss/index.xml"},
    {"name": "Reddit — r/Boilermakers",    "url": "https://www.reddit.com/r/Boilermakers/.rss"},
    {"name": "Reddit — r/CollegeBasketball","url": "https://www.reddit.com/r/CollegeBasketball/.rss"},
]

# Include terms (broadened: boilers, roster, class years)
KEYWORDS_INCLUDE = [
    # school/program nicknames
    "purdue", "boilers", "boilermakers", "boilermaker", "boilerball",
    # sport & program context
    "men’s basketball", "mens basketball", "men's basketball", "basketball", "college basketball", "ncaa",
    "big ten", "b1g", "mackey arena", "matt painter", "painter",
    # roster & recruiting focus
    "roster", "depth chart", "walk-on",
    "recruit", "commit", "signee", "letter of intent", "transfer portal",
    # explicit years/season spellings
    "2025-26", "2025–26", "2025 — 26", "2025—26", "2025 26",
    "class of 2025", "class of 2026", "2025 class", "2026 class",
    # notable players (non-exhaustive)
    "zach edey", "braden smith", "fletcher loyer", "lance jones",
    "trey kaufman", "mason gillis", "caleb first", "myles colvin",
]

# Exclusions to kill football & other sports
KEYWORDS_EXCLUDE = [
    "football","cfb","gridiron",
    "quarterback","qb","running back","rb","wide receiver","wr","tight end","te",
    "linebacker","lb","cornerback","cb","safety","edge","defensive end","de","nose tackle",
    "offensive line","defensive line",
    "kickoff","punt","field goal","touchdown","two-point conversion","extra point",
    "rushing yards","passing yards","sack","spring game","fall camp","depth chart football",  # keep hoops "depth chart" allowed above
    "nfl","combine","pro day",
    "baseball","softball","volleyball","soccer","wrestling",
    "track and field","cross country","golf","tennis","swimming",
    "women’s basketball","womens basketball","women's basketball",
]

# Collector knobs
MAX_ITEMS_PER_FEED = 120
ALLOW_DUPLICATE_DOMAINS = False
DOMAIN_PER_FEED_LIMIT = 4

SOURCE_ALIASES = {
    "Hammer & Rails (SB Nation)": "Hammer & Rails",
    "Reddit — r/Boilermakers": "Reddit r/Boilermakers",
    "Reddit — r/CollegeBasketball": "Reddit r/CollegeBasketball",
}
