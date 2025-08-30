# feeds.py — Purdue MBB Live Feed (freshness + roster ’25–’26 emphasis)

# --------------------------------------------------------------------
# Quick links (UI pills)
# --------------------------------------------------------------------
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

# --------------------------------------------------------------------
# Helpers to create news-engine feeds with freshness/date sorting
# (GN = Google News; BN = Bing News)
# --------------------------------------------------------------------
def GN(q: str) -> dict:
    # Google News: add "when:60d" + "sort:date" to prefer fresh, newest-first
    q2 = f"{q} when:60d sort:date"
    return {
        "name": f"Google News — {q}",
        "url": f"https://news.google.com/rss/search?q={q2}&hl=en-US&gl=US&ceid=US:en",
    }

def BN(q: str) -> dict:
    # Bing News: add qft=sortbydate, prefer fresh results
    return {
        "name": f"Bing News — {q}",
        "url": f"https://www.bing.com/news/search?q={q}&qft=sortbydate&format=rss",
    }

# --------------------------------------------------------------------
# Core queries (encoded inside GN/BN), plus targeted sources
# --------------------------------------------------------------------
FEEDS = [
    # Broad program coverage
    GN("Purdue Basketball"),                         BN("Purdue Basketball"),
    GN("Boilers Purdue basketball"),                 BN("Boilers Purdue basketball"),
    GN("Purdue Boilermakers men's basketball"),      BN("Purdue Boilermakers men's basketball"),
    GN("Matt Painter Purdue"),                       BN("Matt Painter Purdue"),
    GN("Mackey Arena Purdue"),                       BN("Mackey Arena Purdue"),
    GN("Big Ten basketball Purdue"),                 BN("Big Ten basketball Purdue"),
    GN("NCAA Tournament Purdue basketball"),         BN("NCAA Tournament Purdue basketball"),

    # YouTube mentions via news engines (YouTube itself has no search RSS)
    GN("Purdue Basketball site:youtube.com"),        BN("Purdue Basketball site:youtube.com"),
    GN("Matt Painter site:youtube.com"),             BN("Matt Painter site:youtube.com"),

    # Site-scoped (these often work even when broad search flakes)
    GN("site:purdue.rivals.com basketball"),         BN("site:purdue.rivals.com basketball"),
    GN("site:on3.com/teams/purdue-boilermakers/ basketball"), BN("site:on3.com/teams/purdue-boilermakers/ basketball"),
    GN("site:247sports.com/college/purdue/ basketball"), BN("site:247sports.com/college/purdue/ basketball"),
    GN("site:indystar.com Purdue Basketball"),       BN("site:indystar.com Purdue Basketball"),
    GN("site:si.com Purdue Basketball"),             BN("site:si.com Purdue Basketball"),
    GN("site:usatoday.com Purdue Basketball"),       BN("site:usatoday.com Purdue Basketball"),
    GN("site:purduesports.com \"Men's Basketball\""),BN("site:purduesports.com \"Men's Basketball\""),

    # Roster 2025–26 emphasis (variants for hyphen/en-dash/space)
    GN("Purdue 2025-26 roster"),                     BN("Purdue 2025-26 roster"),
    GN("Purdue 2025–26 roster"),                     BN("Purdue 2025–26 roster"),
    GN("\"Purdue\" 2025 roster basketball"),         BN("\"Purdue\" 2025 roster basketball"),
    GN("\"Purdue\" 2026 roster basketball"),         BN("\"Purdue\" 2026 roster basketball"),
    GN("\"Purdue\" men's basketball roster 2025"),   BN("\"Purdue\" men's basketball roster 2025"),
    GN("\"class of 2025\" Purdue basketball"),       BN("\"class of 2025\" Purdue basketball"),
    GN("\"class of 2026\" Purdue basketball"),       BN("\"class of 2026\" Purdue basketball"),
    GN("\"Purdue\" basketball transfer portal"),     BN("\"Purdue\" basketball transfer portal"),

    # Direct community feeds (very reliable)
    {"name": "Hammer & Rails (SB Nation)", "url": "https://www.hammerandrails.com/rss/index.xml"},
    {"name": "Reddit — r/Boilermakers",    "url": "https://www.reddit.com/r/Boilermakers/.rss"},
    {"name": "Reddit — r/CollegeBasketball","url": "https://www.reddit.com/r/CollegeBasketball/.rss"},

    # Extra reliable Purdue-tagged feeds (lightweight)
    {"name": "On3 Purdue – Site Feed",     "url": "https://rss.app/feeds/tIPyQeIh5h9x0pO2.xml"},
    {"name": "247Sports Purdue – Site Feed","url": "https://rss.app/feeds/Wv2kq0xwqj1a8y9S.xml"},
]

# --------------------------------------------------------------------
# Include / Exclude keywords (basketball + roster focus)
# --------------------------------------------------------------------
KEYWORDS_INCLUDE = [
    "purdue", "boilers", "boilermakers", "boilermaker", "boilerball",
    "men’s basketball", "mens basketball", "men's basketball", "basketball", "college basketball", "ncaa",
    "big ten", "b1g", "mackey arena", "matt painter", "painter",
    "roster", "walk-on", "signee", "letter of intent", "transfer portal",
    "class of 2025", "class of 2026", "2025-26", "2025–26", "2025 26",
    "zach edey", "braden smith", "fletcher loyer", "lance jones",
    "trey kaufman", "mason gillis", "caleb first", "myles colvin",
]

KEYWORDS_EXCLUDE = [
    # football terms (kill bleed-through)
    "football","cfb","gridiron",
    "quarterback","qb","running back","rb","wide receiver","wr","tight end","te",
    "linebacker","lb","cornerback","cb","safety","edge","defensive end","de","nose tackle",
    "offensive line","defensive line","kickoff","punt","field goal","touchdown","two-point conversion","extra point",
    "rushing yards","passing yards","sack","spring game","fall camp","depth chart football",
    "nfl","combine","pro day",
    # other sports
    "baseball","softball","volleyball","soccer","wrestling",
    "track and field","cross country","golf","tennis","swimming",
    # women’s team (site is MBB only)
    "women’s basketball","womens basketball","women's basketball",
]

# --------------------------------------------------------------------
# Collector knobs
# --------------------------------------------------------------------
MAX_ITEMS_PER_FEED = 120
ALLOW_DUPLICATE_DOMAINS = False
DOMAIN_PER_FEED_LIMIT = 4

SOURCE_ALIASES = {
    "Hammer & Rails (SB Nation)": "Hammer & Rails",
    "Reddit — r/Boilermakers": "Reddit r/Boilermakers",
    "Reddit — r/CollegeBasketball": "Reddit r/CollegeBasketball",
    # rss.app aliases look cleaner
    "On3 Purdue – Site Feed": "On3 — Purdue",
    "247Sports Purdue – Site Feed": "247Sports — Purdue",
}
