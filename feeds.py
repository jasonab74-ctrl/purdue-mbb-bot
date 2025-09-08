"""
Curated Purdue MBB feeds + stable UI links
- FEEDS: Google News queries & site-scoped searches aimed at Purdue MEN'S basketball.
- STATIC_LINKS: the pill buttons — kept stable across runs.
- CURATED_SOURCES: fixed dropdown list — shown even if a source has 0 items in a run.
"""

GOOGLE = "https://news.google.com/rss/search?hl=en-US&gl=US&ceid=US:en&q="

# 30-day window; exclude other sports; bias toward men’s hoops
G_QUERY = (
    '("Purdue"+"men\'s+basketball" OR "Purdue+Boilermakers"+basketball)+when:30d '
    '-football -volleyball -softball -baseball -soccer -hockey -women%27s -wbb'
)

FEEDS = [
    GOOGLE + G_QUERY,

    # Site-focused channels (keeps results relevant even when headlines omit "Purdue")
    GOOGLE + '(site:purduesports.com+"basketball")+when:30d -football -women%27s',
    GOOGLE + '(site:hammerandrails.com+"basketball")+when:30d -football -women%27s',
    GOOGLE + '(site:journalcourier.com+"Purdue"+basketball)+when:30d -football -women%27s',
    GOOGLE + '(site:goldandblack.com+"basketball")+when:30d -football -women%27s',
    GOOGLE + '(site:theathletic.com+"Purdue"+basketball)+when:30d -football -women%27s',
    GOOGLE + '(site:espn.com+"Purdue"+basketball)+when:30d -football -women%27s',
    GOOGLE + '(site:yahoo.com+"Purdue"+basketball)+when:30d -football -women%27s',
    GOOGLE + '(site:si.com+"Purdue"+basketball)+when:30d -football -women%27s',
    GOOGLE + '(site:cbssports.com+"Purdue"+basketball)+when:30d -football -women%27s',
    GOOGLE + '(site:bigtennetwork.com+"Purdue"+basketball)+when:30d -football -women%27s',
]

# Stable quick links (pills)
STATIC_LINKS = [
    {"label":"Schedule","url":"https://purduesports.com/sports/mens-basketball/schedule"},
    {"label":"Roster","url":"https://purduesports.com/sports/mens-basketball/roster"},
    {"label":"Tickets","url":"https://purduesports.com/sports/2024/9/1/tickets.aspx"},
    {"label":"Reddit — r/Boilermakers","url":"https://www.reddit.com/r/Boilermakers/"},
    {"label":"ESPN Team","url":"https://www.espn.com/mens-college-basketball/team/_/id/2509/purdue-boilermakers"},
    {"label":"KenPom","url":"https://kenpom.com/"},
    {"label":"Sports-Reference","url":"https://www.sports-reference.com/cbb/schools/purdue/"},
    {"label":"Big Ten Standings","url":"https://www.espn.com/mens-college-basketball/standings/_/group/7"},
    {"label":"AP Top 25","url":"https://apnews.com/hub/ap-top-25-mens-college-basketball-poll"},
    {"label":"Bracketology","url":"https://www.espn.com/mens-college-basketball/bracketology"},
    {"label":"Highlights","url":"https://www.youtube.com/results?search_query=Purdue+men%27s+basketball+highlights"},
    {"label":"247Sports","url":"https://247sports.com/college/purdue/"},
    {"label":"Rivals","url":"https://purdue.rivals.com/"},
    {"label":"CBS Purdue","url":"https://www.cbssports.com/college-basketball/teams/PUR/purdue-boilermakers/"},
]

# Fixed dropdown list (displayed even if a run yields no items for one)
CURATED_SOURCES = [
    "PurdueSports.com",
    "Journal & Courier",
    "GoldandBlack.com",
    "Hammer & Rails",
    "The Athletic",
    "ESPN",
    "Yahoo Sports",
    "Sports Illustrated",
    "CBS Sports",
    "Big Ten Network",
    "AP News",
]

# Trusted for lenient headline checks (still block negatives)
TRUSTED_DOMAINS = [
    "purduesports.com",
    "journalcourier.com",
    "goldandblack.com",
    "hammerandrails.com",
    "theathletic.com",
    "espn.com",
    "yahoo.com",
    "si.com",
    "cbssports.com",
    "bigtennetwork.com",
    "apnews.com",
]
