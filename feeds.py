# feeds.py — Purdue Men's Basketball sources (for collect.py that imports FEEDS)
#
# Notes:
# - The "All sources" dropdown is populated from FEEDS below.
# - Each entry is a dict with: name, type ("google" | "bing" | "rss" | "reddit"), url.
# - Optional "trust": True lets items through the lenient allow_item() in collect.py.
# - We use Google/Bing News RSS for many sites to avoid HTML-only pages.
# - Women's / other-sport noise is filtered in collect.py, but we bias names/queries to MBB.

# Keywords we never want (kept here for reference; your collect.py does the filtering)
KEYWORDS_EXCLUDE = [
    "women's basketball", "wbb", "wbk", "lady",
    "football", "volleyball", "baseball", "softball", "soccer",
    "wrestling", "hockey", "golf", "track", "cross country"
]

FEEDS = [
    # ---- Broad Purdue MBB news aggregators
    {
        "name": "Google News – Purdue Basketball",
        "type": "google",
        "url": "https://news.google.com/rss/search?q=Purdue+Men%27s+Basketball+OR+MBB+OR+%22Matt+Painter%22&hl=en-US&gl=US&ceid=US:en",
        "trust": True
    },
    {
        "name": "Bing News – Purdue Basketball",
        "type": "bing",
        "url": "https://www.bing.com/news/search?q=Purdue+Men%27s+Basketball+OR+MBB+OR+%22Matt+Painter%22&format=RSS",
        "trust": True
    },

    # ---- Site-focused feeds via Google/Bing (keeps to MBB context)
    {
        "name": "Google News — ESPN Purdue MBB",
        "type": "google",
        "url": "https://news.google.com/rss/search?q=site:espn.com+Purdue+Men%27s+Basketball&hl=en-US&gl=US&ceid=US:en",
        "trust": True
    },
    {
        "name": "Google News — CBS Sports – Purdue",
        "type": "google",
        "url": "https://news.google.com/rss/search?q=site:cbssports.com+Purdue+Men%27s+Basketball&hl=en-US&gl=US&ceid=US:en",
        "trust": True
    },
    {
        "name": "Google News — Yahoo Sports – Purdue",
        "type": "google",
        "url": "https://news.google.com/rss/search?q=site:sports.yahoo.com+Purdue+Men%27s+Basketball&hl=en-US&gl=US&ceid=US:en",
        "trust": True
    },

    # ---- Local & beat outlets
    # Journal & Courier (jconline) — your requested source
    {
        "name": "Journal & Courier Purdue",
        "type": "google",
        "url": "https://news.google.com/rss/search?q=site:jconline.com+Purdue+Men%27s+Basketball&hl=en-US&gl=US&ceid=US:en"
    },
    # Purdue Exponent — men's basketball path emphasized
    {
        "name": "Purdue Exponent — Men’s Basketball",
        "type": "google",
        "url": "https://news.google.com/rss/search?q=site:purdueexponent.org%2Fsports%2Fmens%2Fbasketball%2F+Purdue+Basketball&hl=en-US&gl=US&ceid=US:en"
    },
    {
        "name": "IndyStar Purdue",
        "type": "google",
        "url": "https://news.google.com/rss/search?q=site:indystar.com+Purdue+Men%27s+Basketball&hl=en-US&gl=US&ceid=US:en"
    },

    # ---- Recruiting / team sites (use site filters to stay on Purdue pages)
    {
        "name": "On3 — Purdue (team feed)",
        "type": "google",
        "url": "https://news.google.com/rss/search?q=site:on3.com%2Fteams%2Fpurdue-boilermakers%2F+basketball&hl=en-US&gl=US&ceid=US:en"
    },
    {
        "name": "247Sports — Purdue (team feed)",
        "type": "google",
        "url": "https://news.google.com/rss/search?q=site:247sports.com%2Fcollege%2Fpurdue%2F+basketball&hl=en-US&gl=US&ceid=US:en"
    },
    {
        "name": "Rivals — GoldandBlack (Purdue)",
        "type": "bing",
        "url": "https://www.bing.com/news/search?q=site:goldandblack.com+Purdue+Basketball&format=RSS"
    },
    {
        "name": "Sports Illustrated — Purdue",
        "type": "google",
        "url": "https://news.google.com/rss/search?q=site:si.com+Purdue+Men%27s+Basketball&hl=en-US&gl=US&ceid=US:en"
    },

    # ---- Blogs / fan sites with working RSS
    {
        "name": "Hammer & Rails (SB Nation)",
        "type": "rss",
        "url": "https://www.hammerandrails.com/rss/index.xml"
    },

    # ---- Official (no reliable RSS for MBB page; use site query)
    {
        "name": "PurdueSports.com — “Men’s Basketball”",
        "type": "bing",
        "url": "https://www.bing.com/news/search?q=site:purduesports.com+%22Men%27s+Basketball%22&format=RSS",
        "trust": True
    },

    # ---- Reddit
    {
        "name": "Reddit — r/Boilermakers",
        "type": "reddit",
        "url": "https://www.reddit.com/r/Boilermakers/.rss"
    },
    {
        "name": "Reddit — r/CollegeBasketball (Purdue search)",
        "type": "rss",
        "url": "https://www.reddit.com/r/CollegeBasketball/search.rss?q=Purdue%20basketball&restrict_sr=on&sort=new"
    },

    # ---- Focused queries (coach / arena / tournament context)
    {
        "name": "Google News — Matt Painter",
        "type": "google",
        "url": "https://news.google.com/rss/search?q=%22Matt+Painter%22+Purdue+basketball&hl=en-US&gl=US&ceid=US:en"
    },
    {
        "name": "Google News — Mackey Arena (MBB context)",
        "type": "google",
        "url": "https://news.google.com/rss/search?q=%22Mackey+Arena%22+Purdue+basketball&hl=en-US&gl=US&ceid=US:en"
    },
    {
        "name": "Google News — NCAA Tournament (Purdue)",
        "type": "google",
        "url": "https://news.google.com/rss/search?q=Purdue+basketball+NCAA+Tournament&hl=en-US&gl=US&ceid=US:en"
    },

    # ---- Player-name signals (helps your filter pass legit MBB items)
    {
        "name": "Google News — Purdue Player Mentions",
        "type": "google",
        "url": "https://news.google.com/rss/search?q="
               "Purdue+basketball+("
               "Braden+Smith+OR+Fletcher+Loyer+OR+Trey+Kaufman-Renn+OR+Jack+Benter+OR+Omer+Mayer+OR+"
               "Gicarri+Harris+OR+Raleigh+Burgess+OR+Daniel+Jacobsen+OR+Oscar+Cluff+OR+Liam+Murphy+OR+"
               "Sam+King+OR+Aaron+Fine+OR+Jace+Rayl+OR+Jack+Lusk+OR+C.J.+Cox)"
               "&hl=en-US&gl=US&ceid=US:en"
    },
]

# Optional: quick links row (if your UI uses these)
STATIC_LINKS = [
    {"label": "Purdue – Official MBB Page", "url": "https://purduesports.com/sports/mens-basketball"},
    {"label": "Purdue – Schedule",          "url": "https://purduesports.com/sports/mens-basketball/schedule"},
    {"label": "Purdue – Roster",            "url": "https://purduesports.com/sports/mens-basketball/roster"},
    {"label": "ESPN – Purdue MBB",          "url": "https://www.espn.com/mens-college-basketball/team/_/id/2509/purdue-boilermakers"},
    {"label": "CBS Sports – Purdue",        "url": "https://www.cbssports.com/college-basketball/teams/PURDUE/purdue-boilermakers/"},
    {"label": "Yahoo Sports – Purdue",      "url": "https://sports.yahoo.com/ncaab/teams/purdue/"},
    {"label": "Hammer & Rails (SB Nation)", "url": "https://www.hammerandrails.com/"},
    {"label": "GoldandBlack (Rivals)",      "url": "https://goldandblack.com/"},
    {"label": "Barstool – Purdue",          "url": "https://www.barstoolsports.com/tag/purdue"},
    {"label": "Reddit – r/Boilermakers",    "url": "https://www.reddit.com/r/Boilermakers/"},
    {"label": "YouTube – Field of 68",      "url": "https://www.youtube.com/@Fieldof68"},
    {"label": "YouTube – Sleepers Media",   "url": "https://www.youtube.com/@SleepersMedia"},
    {"label": "Journal & Courier",          "url": "https://www.jconline.com/sports/boilermakers/"},
    {"label": "Purdue Exponent (MBB)",      "url": "https://www.purdueexponent.org/sports/mens/basketball/"},
]
