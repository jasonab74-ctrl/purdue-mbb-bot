# feeds.py — Purdue Men's Basketball sources (used by collect.py)
# FEEDS drives the Sources dropdown. STATIC_LINKS drives the top buttons.

FEEDS = [
    # ===== Broad Purdue MBB aggregators
    {"name": "Google News — Purdue Basketball",
     "url": "https://news.google.com/rss/search?q=Purdue+Men%27s+Basketball+OR+MBB+OR+%22Matt+Painter%22&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Bing News — Purdue Basketball",
     "url": "https://www.bing.com/news/search?q=Purdue+Men%27s+Basketball+OR+MBB+OR+%22Matt+Painter%22&format=RSS"},

    # ===== Major outlets
    {"name": "ESPN — Purdue (MBB search)",
     "url": "https://news.google.com/rss/search?q=site:espn.com+Purdue+Men%27s+Basketball&hl=en-US&gl=US&ceid=US:en"},
    {"name": "CBS Sports — Purdue (MBB search)",
     "url": "https://news.google.com/rss/search?q=site:cbssports.com+Purdue+Men%27s+Basketball&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Yahoo Sports — Purdue (MBB search)",
     "url": "https://news.google.com/rss/search?q=site:sports.yahoo.com+Purdue+Men%27s+Basketball&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Sports Illustrated — Purdue (MBB search)",
     "url": "https://news.google.com/rss/search?q=site:si.com+Purdue+Men%27s+Basketball&hl=en-US&gl=US&ceid=US:en"},

    # ===== Local & beat
    {"name": "Journal & Courier (J&C) — Purdue",
     "url": "https://news.google.com/rss/search?q=site:jconline.com+Purdue+Men%27s+Basketball&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Purdue Exponent — Men’s Basketball",
     "url": "https://news.google.com/rss/search?q=site:purdueexponent.org/sports/mens/basketball/+Purdue&hl=en-US&gl=US&ceid=US:en"},
    {"name": "IndyStar — Purdue (MBB search)",
     "url": "https://news.google.com/rss/search?q=site:indystar.com+Purdue+Men%27s+Basketball&hl=en-US&gl=US&ceid=US:en"},

    # ===== Recruiting / team sites
    {"name": "On3 — Purdue team feed",
     "url": "https://news.google.com/rss/search?q=site:on3.com/teams/purdue-boilermakers/+basketball&hl=en-US&gl=US&ceid=US:en"},
    {"name": "247Sports — Purdue team feed",
     "url": "https://news.google.com/rss/search?q=site:247sports.com/college/purdue/+basketball&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Rivals — GoldandBlack (site)",
     "url": "https://www.bing.com/news/search?q=site:goldandblack.com+Purdue+Basketball&format=RSS"},

    # ===== Blogs / fan
    {"name": "Hammer & Rails (SB Nation)", "url": "https://www.hammerandrails.com/rss/index.xml"},

    # ===== Official
    {"name": "PurdueSports.com — “Men’s Basketball”",
     "url": "https://www.bing.com/news/search?q=site:purduesports.com+%22Men%27s+Basketball%22&format=RSS"},

    # ===== Reddit
    {"name": "Reddit — r/Boilermakers", "url": "https://www.reddit.com/r/Boilermakers/.rss"},
    {"name": "Reddit — r/CollegeBasketball (Purdue search)",
     "url": "https://www.reddit.com/r/CollegeBasketball/search.rss?q=Purdue%20basketball&restrict_sr=on&sort=new"},
    {"name": "Reddit — r/PurdueBasketball", "url": "https://www.reddit.com/r/PurdueBasketball/.rss"},

    # ===== Focus signals (coach/arena)
    {"name": "Matt Painter — news",
     "url": "https://news.google.com/rss/search?q=%22Matt+Painter%22+Purdue+basketball&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Mackey Arena — news",
     "url": "https://news.google.com/rss/search?q=%22Mackey+Arena%22+Purdue+basketball&hl=en-US&gl=US&ceid=US:en"},

    # ===== Player-name bundle
    {"name": "Purdue Player Mentions — bundle",
     "url": (
        "https://news.google.com/rss/search?q="
        "Purdue+basketball+("
        "Braden+Smith+OR+Fletcher+Loyer+OR+Trey+Kaufman-Renn+OR+Jack+Benter+OR+Omer+Mayer+OR+"
        "Gicarri+Harris+OR+Raleigh+Burgess+OR+Daniel+Jacobsen+OR+Oscar+Cluff+OR+Liam+Murphy+OR+"
        "Sam+King+OR+Aaron+Fine+OR+Jace+Rayl+OR+Jack+Lusk+OR+C.J.+Cox)"
        "&hl=en-US&gl=US&ceid=US:en"
     )},
]

# Quick links (top buttons). Order matters on the page.
STATIC_LINKS = [
    {"label": "Game Day",              "url": "https://www.google.com/search?q=Purdue+Men%27s+Basketball+game+today"},
    {"label": "Odds — Purdue",         "url": "https://www.google.com/search?q=Purdue+Boilermakers+basketball+odds"},
    {"label": "Purdue Official",       "url": "https://purduesports.com/sports/mens-basketball"},
    {"label": "Schedule",              "url": "https://purduesports.com/sports/mens-basketball/schedule"},
    {"label": "Roster",                "url": "https://purduesports.com/sports/mens-basketball/roster"},
    {"label": "ESPN",                  "url": "https://www.espn.com/mens-college-basketball/team/_/id/2509/purdue-boilermakers"},
    {"label": "CBS Sports",            "url": "https://www.cbssports.com/college-basketball/teams/PURDUE/purdue-boilermakers/"},
    {"label": "Yahoo Sports",          "url": "https://sports.yahoo.com/ncaab/teams/purdue/"},
    {"label": "Hammer & Rails",        "url": "https://www.hammerandrails.com/"},
    {"label": "G&B",                   "url": "https://goldandblack.com/"},
    {"label": "Barstool Sports",       "url": "https://www.barstoolsports.com/tag/purdue"},
    {"label": "Reddit - Boilermakers", "url": "https://www.reddit.com/r/Boilermakers/"},
    {"label": "J&C",                   "url": "https://www.jconline.com/sports/boilermakers/"},
    {"label": "Exponent",              "url": "https://www.purdueexponent.org/sports/mens/basketball/"},
    {"label": "YouTube - Field of 68", "url": "https://www.youtube.com/@Fieldof68"},
    {"label": "YouTube - Sleepers",    "url": "https://www.youtube.com/@SleepersMedia"},
    {"label": "YouTube - G&B",         "url": "https://www.youtube.com/@Goldandblackcom"}
]
