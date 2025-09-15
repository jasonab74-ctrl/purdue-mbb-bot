# feeds.py
# ----------------------------------------------------------------------
# Drop-in source list for the Purdue MBB site. Safe expansion only.
# Works with the existing collect.py (feedparser) setup.
#
# FEEDS: list of (label, url) – label is what you’ll see in the UI,
# url is the RSS feed to fetch.
#
# FILTERS: tiny guardrails so football posts don’t slip in.
# ----------------------------------------------------------------------

FEEDS = [
    # Core, broad catch-all for Purdue MBB
    ("Google News",
     "https://news.google.com/rss/search?q=%28%22Purdue%20Boilermakers%22%20OR%20Purdue%29%20%28basketball%20OR%20MBB%29&hl=en-US&gl=US&ceid=US:en"),

    # Site-focused feeds via Google News (more stable than scraping sites directly)
    ("Yahoo Sports",
     "https://news.google.com/rss/search?q=site:sports.yahoo.com%20%28Purdue%20basketball%20OR%20Purdue%20MBB%29&hl=en-US&gl=US&ceid=US:en"),

    ("Hammer and Rails",  # direct RSS, reliable
     "https://www.hammerandrails.com/rss/index.xml"),

    ("ESPN",
     "https://news.google.com/rss/search?q=site:espn.com%20Purdue%20basketball&hl=en-US&gl=US&ceid=US:en"),

    ("Sports Illustrated",
     "https://news.google.com/rss/search?q=site:si.com%20Purdue%20basketball&hl=en-US&gl=US&ceid=US:en"),

    ("Journal & Courier",
     "https://news.google.com/rss/search?q=site:jconline.com%20Purdue%20basketball&hl=en-US&gl=US&ceid=US:en"),

    ("GoldandBlack",
     "https://news.google.com/rss/search?q=site:goldandblack.com%20basketball%20Purdue&hl=en-US&gl=US&ceid=US:en"),

    ("The Athletic",
     "https://news.google.com/rss/search?q=site:theathletic.com%20Purdue%20basketball&hl=en-US&gl=US&ceid=US:en"),

    ("CBS Sports",
     "https://news.google.com/rss/search?q=site:cbssports.com%20Purdue%20basketball&hl=en-US&gl=US&ceid=US:en"),

    ("Big Ten Network",
     "https://news.google.com/rss/search?q=site:btn.com%20Purdue%20basketball&hl=en-US&gl=US&ceid=US:en"),

    # Optional depth (these two keep the total within the 8–12 range you wanted)
    ("247Sports",
     "https://news.google.com/rss/search?q=site:247sports.com%20Purdue%20basketball&hl=en-US&gl=US&ceid=US:en"),

    ("Rivals",
     "https://news.google.com/rss/search?q=site:rivals.com%20Purdue%20basketball&hl=en-US&gl=US&ceid=US:en"),
]

# Title/content guards – your collector can use these if present.
INCLUDE_KEYWORDS = [
    "purdue", "boilermaker", "boilermakers", "mbb", "basketball", "matt painter", "mackey"
]

EXCLUDE_KEYWORDS = [
    "football", "cfb", "nfl", "gridiron"
]

def should_keep(title: str, summary: str = "") -> bool:
    """
    Conservative filter to favor Purdue men's basketball.
    If your collect.py already filters, it can ignore this function.
    """
    t = f"{title or ''} {summary or ''}".lower()
    if any(x in t for x in EXCLUDE_KEYWORDS):
        return False
    # Require at least one Purdue/MBB keyword
    return any(x in t for x in INCLUDE_KEYWORDS)
