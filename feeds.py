# Curated Purdue MBB sources (10) and quick links
# Feeds use Google News RSS to normalize; source labels are hardened in collect.py

FEEDS = [
    # Team site + local + national (basketball-focused intents)
    {"name": "PurdueSports.com",   "url": "https://news.google.com/rss/search?q=Purdue+Boilermakers+men%27s+basketball+site%3Apurduesports.com&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Journal & Courier",  "url": "https://news.google.com/rss/search?q=Purdue+men%27s+basketball+site%3Ajconline.com&hl=en-US&gl=US&ceid=US:en"},
    {"name": "GoldandBlack.com",   "url": "https://news.google.com/rss/search?q=Purdue+men%27s+basketball+site%3Agoldandblack.com+OR+site%3Aon3.com&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Hammer and Rails",   "url": "https://news.google.com/rss/search?q=Purdue+men%27s+basketball+site%3Ahammerandrails.com&hl=en-US&gl=US&ceid=US:en"},
    {"name": "The Athletic",       "url": "https://news.google.com/rss/search?q=Purdue+men%27s+basketball+site%3Atheathletic.com&hl=en-US&gl=US&ceid=US:en"},
    {"name": "ESPN",               "url": "https://news.google.com/rss/search?q=Purdue+men%27s+basketball+site%3Aespn.com&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Yahoo Sports",       "url": "https://news.google.com/rss/search?q=Purdue+men%27s+basketball+site%3Asports.yahoo.com&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Sports Illustrated", "url": "https://news.google.com/rss/search?q=Purdue+men%27s+basketball+site%3Asi.com&hl=en-US&gl=US&ceid=US:en"},
    {"name": "CBS Sports",         "url": "https://news.google.com/rss/search?q=Purdue+men%27s+basketball+site%3Acbssports.com&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Big Ten Network",    "url": "https://news.google.com/rss/search?q=Purdue+men%27s+basketball+site%3Abtn.com+OR+site%3Abtn.plus&hl=en-US&gl=US&ceid=US:en"},
]

STATIC_LINKS = [
    {"label": "Schedule", "url": "https://purduesports.com/sports/mens-basketball/schedule"},
    {"label": "Roster", "url": "https://purduesports.com/sports/mens-basketball/roster"},
    {"label": "Tickets", "url": "https://purduesports.com/sports/2024/9/1/tickets.aspx"},
    {"label": "Reddit — r/Boilermakers", "url": "https://www.reddit.com/r/Boilermakers/"},
    {"label": "ESPN Team", "url": "https://www.espn.com/mens-college-basketball/team/_/id/2509/purdue-boilermakers"},
    {"label": "KenPom", "url": "https://kenpom.com/"},
    {"label": "Sports-Reference", "url": "https://www.sports-reference.com/cbb/schools/purdue/"},
    {"label": "Big Ten Standings", "url": "https://www.espn.com/mens-college-basketball/standings/_/group/7"}
]
