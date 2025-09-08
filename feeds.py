# Feeds and trusted sources for Purdue MBB

FEEDS = [
    # Purdue-focused
    "https://www.hammerandrails.com/rss/index.xml",
    "https://www.jconline.com/search/?q=Purdue%20basketball&rss=1",
    "https://www.goldandblack.com/rss",
    "https://www.on3.com/college/purdue-boilermakers/feed/",

    # Big outlets filtered by query
    "https://news.google.com/rss/search?q=Purdue%20Boilermakers%20basketball%20OR%20Purdue%20MBB&hl=en-US&gl=US&ceid=US:en",
    "https://sports.yahoo.com/college-basketball/teams/purdue/news/?format=rss",
    "https://www.cbssports.com/college-basketball/teams/PUR/purdue-boilermakers/rss/",
    "https://www.espn.com/espn/rss/ncb/team?teamId=2509",
]

# Any item from these source names passes include check (unless football-y)
TRUSTED_SOURCES = {
    "Hammer and Rails",
    "Journal & Courier",
    "GoldandBlack.com",
    "On3",
    "Yahoo Sports",
    "CBS Sports",
    "ESPN",
}