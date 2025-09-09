# Hardened list of Purdue MBB sources (RSS / Atom or Google News query)
# Keep names stable – these appear in the Source dropdown.

FEEDS = [
    ("Hammer and Rails", "https://www.hammerandrails.com/rss/index.xml"),
    ("Journal & Courier", "https://rss.app/feeds/9cK2gK2mR2oQy7iE.xml"),  # Lafayette J&C Purdue MBB (safe RSS proxy)
    ("GoldandBlack.com", "https://www.on3.com/college/purdue-boilermakers/feed/"),
    ("ESPN", "https://www.espn.com/blog/rss/ncb/purdue-boilermakers"),
    ("Yahoo Sports", "https://sports.yahoo.com/ncaab/teams/purdue/rss/"),
    ("Sports Illustrated", "https://www.si.com/college/purdue/.rss"),
    ("CBS Sports", "https://www.cbssports.com/college-basketball/teams/PURDU/purdue-boilermakers/rss/"),
    ("Big Ten Network", "https://btn.com/schools/purdue/feed/"),
    # A focused Google News query (MBB context words included)
    ("Google News",
     "https://news.google.com/rss/search?q=Purdue+Boilermakers+basketball+OR+Purdue+MBB+OR+Mackey+Arena&hl=en-US&gl=US&ceid=US:en"),
    ("The Athletic", "https://theathletic.com/team/purdue-boilermakers/?rss=1"),
]