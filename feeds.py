# feeds.py
# --------------------------------------------------------------------
# 8–10 Purdue MEN'S BASKETBALL–focused sources.
# These are all RSS (either native feeds or Google News RSS with
# site: filters). The collector should read these with feedparser.
#
# Notes
# - Keep this list basketball-first to reduce football bleed.
# - You can comment out any source you don’t want.
# - The collector (collect.py) should already cap to the 50 most
#   recent items overall; leave that logic there.
# --------------------------------------------------------------------

FEEDS = [
    {
        "id": "yahoo",
        "name": "Yahoo Sports",
        "url": "https://news.google.com/rss/search?q=Purdue+Boilermakers+basketball+site%3Asports.yahoo.com&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "id": "googlenews",
        "name": "Google News",
        "url": "https://news.google.com/rss/search?q=%22Purdue%20Boilermakers%22%20basketball%20OR%20%22Purdue%20MBB%22%20OR%20%22Purdue%20men%27s%20basketball%22&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "id": "hammerandrails",
        "name": "Hammer and Rails",
        # native Vox/SB Nation RSS
        "url": "https://www.hammerandrails.com/rss/index.xml",
    },
    {
        "id": "espn",
        "name": "ESPN",
        "url": "https://news.google.com/rss/search?q=Purdue+Boilermakers+basketball+site%3Aespn.com&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "id": "si",
        "name": "Sports Illustrated",
        "url": "https://news.google.com/rss/search?q=Purdue+Boilermakers+basketball+site%3Asi.com&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "id": "jcon",
        "name": "Journal & Courier",
        "url": "https://news.google.com/rss/search?q=Purdue+Boilermakers+basketball+site%3Ajconline.com&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "id": "goldandblack",
        "name": "GoldandBlack",
        "url": "https://news.google.com/rss/search?q=Purdue+Boilermakers+basketball+site%3Agoldandblack.com&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "id": "cbs",
        "name": "CBS Sports",
        "url": "https://news.google.com/rss/search?q=Purdue+Boilermakers+basketball+site%3Acbssports.com&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "id": "btn",
        "name": "Big Ten Network",
        "url": "https://news.google.com/rss/search?q=Purdue+Boilermakers+basketball+site%3Abtn.com&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "id": "usatodaywire",
        "name": "USA Today — Purdue Wire",
        "url": "https://news.google.com/rss/search?q=site%3Apurduewire.usatoday.com+Purdue+basketball&hl=en-US&gl=US&ceid=US:en",
    },
]