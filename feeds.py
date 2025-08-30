# feeds.py — Purdue MBB sources (basketball-only; adds Journal & Courier + Purdue Exponent site scopes)

# These are just the header pills (unchanged visually). They do NOT affect filtering.
STATIC_LINKS = [
    {"label": "Purdue – Official MBB Page", "url": "https://purduesports.com/sports/mens-basketball"},
    {"label": "Purdue – Schedule",          "url": "https://purduesports.com/sports/mens-basketball/schedule"},
    {"label": "Purdue – Roster",            "url": "https://purduesports.com/sports/mens-basketball/roster"},
    {"label": "ESPN – Purdue MBB",          "url": "https://www.espn.com/mens-college-basketball/team/_/id/2509/purdue-boilermakers"},
    {"label": "CBS Sports – Purdue",        "url": "https://www.cbssports.com/college-basketball/teams/PUR/purdue-boilermakers/"},
    {"label": "Yahoo Sports – Purdue",      "url": "https://sports.yahoo.com/ncaab/teams/purdue/"},
    {"label": "Hammer & Rails (SB Nation)", "url": "https://www.hammerandrails.com/"},
    {"label": "GoldandBlack (Rivals/On3)",  "url": "https://www.on3.com/teams/purdue-boilermakers/"},
    {"label": "Barstool – Purdue",          "url": "https://www.barstoolsports.com/topics/purdue-boilermakers"},
    {"label": "Reddit – r/Boilermakers",    "url": "https://www.reddit.com/r/Boilermakers/"},
    {"label": "YouTube – Field of 68",      "url": "https://www.youtube.com/@TheFieldOf68"},
    {"label": "YouTube – Sleepers Media",   "url": "https://www.youtube.com/@sleepersmedia"},
]

def GN(q: str) -> dict:
    # 60 days to stay fresh but still show enough history; sorted newest first
    q2 = f"{q} when:60d sort:date"
    return {
        "name": f"Google News — {q}",
        "url":  f"https://news.google.com/rss/search?q={q2}&hl=en-US&gl=US&ceid=US:en",
    }

def BN(q: str) -> dict:
    return {
        "name": f"Bing News — {q}",
        "url":  f"https://www.bing.com/news/search?q={q}&qft=sortbydate&setlang=en&setmkt=en-US&format=rss",
    }

FEEDS = [
    # ---- DIRECT, RELIABLE FEEDS (video + native RSS) ----
    {"name": "YouTube — Sleepers Media (channel)", "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCaqPH-Ckzu_pSoO3AKcatNw"},
    # Keep the official MBB playlist (pure hoops)
    {"name": "YouTube — Purdue MBB Playlist",      "url": "https://www.youtube.com/feeds/videos.xml?playlist_id=PLCIT1wYGMWN80GZO_ybcH6vuHeObcOcmh"},
    # H&R RSS (we’ll filter football out in collect.py)
    {"name": "Hammer & Rails (SB Nation)",         "url": "https://www.hammerandrails.com/rss/index.xml"},
    # Reddit communities (also filtered in collect.py)
    {"name": "Reddit — r/Boilermakers",            "url": "https://www.reddit.com/r/Boilermakers/.rss"},
    {"name": "Reddit — r/CollegeBasketball",       "url": "https://www.reddit.com/r/CollegeBasketball/.rss"},

    # ---- Broad Purdue hoops searches (news portals) ----
    GN("Purdue Basketball"),                         BN("Purdue Basketball"),
    GN("Boilers Purdue basketball"),                 BN("Boilers Purdue basketball"),
    GN("Purdue Boilermakers men's basketball"),      BN("Purdue Boilermakers men's basketball"),
    GN("Matt Painter Purdue"),                       BN("Matt Painter Purdue"),
    GN("Mackey Arena Purdue"),                       BN("Mackey Arena Purdue"),
    GN("Big Ten basketball Purdue"),                 BN("Big Ten basketball Purdue"),
    GN("NCAA Tournament Purdue basketball"),         BN("NCAA Tournament Purdue basketball"),

    # YouTube mentions via portals (backup to direct feeds)
    GN("Purdue Basketball site:youtube.com"),        BN("Purdue Basketball site:youtube.com"),
    GN("Matt Painter site:youtube.com"),             BN("Matt Painter site:youtube.com"),

    # ---- Site-scoped sources (add depth; dropdown shows each) ----
    GN("site:indystar.com Purdue Basketball"),             BN("site:indystar.com Purdue Basketball"),
    GN("site:usatoday.com Purdue Basketball"),             BN("site:usatoday.com Purdue Basketball"),
    GN("site:si.com Purdue Basketball"),                   BN("site:si.com Purdue Basketball"),
    GN("site:theathletic.com Purdue Basketball"),          BN("site:theathletic.com Purdue Basketball"),
    GN("site:247sports.com/college/purdue/ basketball"),   BN("site:247sports.com/college/purdue/ basketball"),
    GN("site:on3.com/teams/purdue-boilermakers/ basketball"), BN("site:on3.com/teams/purdue-boilermakers/ basketball"),
    GN("site:goldandblack.com Purdue"),                    BN("site:goldandblack.com Purdue"),
    GN("site:purdue.rivals.com basketball"),               BN("site:purdue.rivals.com basketball"),
    GN("site:purduesports.com \"Men's Basketball\""),       BN("site:purduesports.com \"Men's Basketball\""),

    # NEW — Journal & Courier + Purdue Exponent (site-scoped)
    GN("site:jconline.com Purdue Basketball"),             BN("site:jconline.com Purdue Basketball"),
    GN("site:purdueexponent.org basketball"),              BN("site:purdueexponent.org basketball"),

    # ---- 2025–26 roster emphasis & recruiting (hoops only) ----
    GN("Purdue 2025-26 roster"),                           BN("Purdue 2025-26 roster"),
    GN("Purdue 2025–26 roster"),                           BN("Purdue 2025–26 roster"),
    GN("\"Purdue\" 2025 roster basketball"),               BN("\"Purdue\" 2025 roster basketball"),
    GN("\"Purdue\" 2026 roster basketball"),               BN("\"Purdue\" 2026 roster basketball"),
    GN("\"Purdue\" men's basketball roster 2025"),         BN("\"Purdue\" men's basketball roster 2025"),
    GN("\"class of 2025\" Purdue basketball"),             BN("\"class of 2025\" Purdue basketball"),
    GN("\"class of 2026\" Purdue basketball"),             BN("\"class of 2026\" Purdue basketball"),
    GN("\"Purdue\" basketball transfer portal"),           BN("\"Purdue\" basketball transfer portal"),

    # Brian Neubert (writer) — articles & clips
    GN("Brian Neubert Purdue basketball"),                 BN("Brian Neubert Purdue basketball"),
    GN("site:goldandblack.com Brian Neubert"),             BN("site:goldandblack.com Brian Neubert"),
    GN("site:on3.com Brian Neubert Purdue"),               BN("site:on3.com Brian Neubert Purdue"),
    GN("site:purdue.rivals.com Brian Neubert"),            BN("site:purdue.rivals.com Brian Neubert"),
]

# --------- FILTERS (basketball-only) ----------
KEYWORDS_INCLUDE = [
    # Purdue names/aliases
    "purdue","boiler","boilers","boilermaker","boilermakers",
    # sport context
    "basketball","men’s basketball","mens basketball","men's basketball","college basketball","ncaa",
    "big ten","b1g","mackey arena","purdue arena",
    "matt painter","painter",
    "roster","walk-on","signee","letter of intent","transfer portal",
    "class of 2025","class of 2026","2025-26","2025–26","2025 26",
    # players (recent/returning/core)
    "zach edey","braden smith","fletcher loyer","lance jones",
    "trey kaufman","trey kaufman-renn","mason gillis","caleb furst",
    "myles colvin","camden heide","will berg","jack benter",
    "daniel jacobsen","levi cook","omer mayer","tkr","taylor","luke ertel",
    # media voices
    "brian neubert",
]

KEYWORDS_EXCLUDE = [
    # hard football purge
    "football","cfb","gridiron",
    "quarterback","qb","running back","rb","wide receiver","wr","tight end","te",
    "linebacker","lb","cornerback","cb","safety","edge","defensive end","de","nose tackle",
    "offensive line","defensive line","kickoff","punt","field goal","touchdown",
    "spring game","fall camp","depth chart football","training camp",
    "nfl","combine","pro day",
    # other sports
    "baseball","softball","volleyball","soccer","wrestling",
    "track and field","cross country","golf","tennis","swimming",
    # general campus/world news that leaks in from Exponent
    "presidential lecture","robot dog","gauff","venice","police", "economy","concert","movie","transcript","trial",
]

# Collection behavior
MAX_ITEMS_PER_FEED = 240
ALLOW_DUPLICATE_DOMAINS = True
DOMAIN_PER_FEED_LIMIT = 999

# Feed-level “must contain” rules to keep non-hoops items out (esp. PurdueSports channel, Reddit CBB)
FEED_TITLE_REQUIRE = {
    # If you later re-add the general PurdueSports channel, titles must be hoopsy
    "YouTube — PurdueSports (channel)": ["mbb","basketball","boilermaker","boilermakers"],
    "Reddit — r/CollegeBasketball":    ["purdue","boiler","boilermaker","boilermakers","painter"],
}

SOURCE_ALIASES = {
    "Hammer & Rails (SB Nation)": "Hammer & Rails",
    "Reddit — r/Boilermakers": "Reddit r/Boilermakers",
    "Reddit — r/CollegeBasketball": "Reddit r/CollegeBasketball",
}
