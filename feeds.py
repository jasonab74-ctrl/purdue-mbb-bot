# feeds.py
# -------------------------------------------------------------------
# Source catalog for Purdue Men's Basketball live feed.
# Only domains/queries are here. All fetching/filtering happens
# in collect.py. Safe to tweak and redeploy without breaking server.
# -------------------------------------------------------------------

TEAM_NAME = "Purdue Men's Basketball"

# How far back to look (days). Collect tries recent first but can look
# back this far to reach your “~75+ items” goal.
DAYS_BACK_DEFAULT = 120  # tweakable via env FRESH_DAYS

# Max items to keep in items.json (sorted newest first)
MAX_ITEMS_DEFAULT = 250  # tweakable via env MAX_ITEMS

# -------------------------------------------------------------------
# Convenience: domains that are *about* Purdue athletics already.
# These get a lighter keyword test (still football-excluded).
PURDUE_HEAVY_DOMAINS = {
    "hammerandrails.com",
    "goldandblack.com",
    "indystar.com",
    "on3.com",
    "247sports.com",
    "purdue.rivals.com",
    "purduesports.com",
    "jconline.com",              # Journal & Courier
    "purdueexponent.org",
}

# -------------------------------------------------------------------
# Google News & Bing News queries
# Each entry becomes its own feed. “label” shows up in the UI dropdown.
NEWS_QUERIES = [
    # Core
    {"label": "Google News — Purdue Basketball", "engine": "google", "q": 'Purdue Basketball OR "Purdue men\'s basketball" OR "Boilermakers men\'s basketball"'},
    {"label": "Bing News — Purdue Basketball",   "engine": "bing",   "q": 'Purdue Basketball OR "Purdue men\'s basketball"'},

    # Coach & arena
    {"label": "Google News — Matt Painter", "engine": "google", "q": '"Matt Painter" (Purdue OR Boilermakers)'},
    {"label": "Google News — Mackey Arena", "engine": "google", "q": '"Mackey Arena" (Purdue OR Boilermakers)'},

    # Roster / seasons
    {"label": "Google News — Purdue 2025–26 roster", "engine": "google", "q": '"Purdue" ("2025-26" OR "2025–26") roster basketball'},
    {"label": "Bing News — Boilers Purdue basketball", "engine": "bing", "q": 'Boilers "Purdue" basketball'},

    # Local / site filters (journal & courier + exponent + IndyStar etc.)
    {"label": "Google News — IndyStar Purdue",        "engine": "google", "q": 'site:indystar.com ("Purdue" OR "Boilermakers") (basketball OR Matt Painter)'},
    {"label": "Google News — Journal & Courier",      "engine": "google", "q": 'site:jconline.com ("Purdue" OR "Boilermakers") (basketball OR "Mackey Arena" OR "Matt Painter")'},
    {"label": "Google News — Purdue Exponent (MBB)",  "engine": "google", "q": 'site:purdueexponent.org ("men\'s basketball" OR "Purdue men\'s basketball" OR "MBB")'},
    {"label": "Google News — Hammer & Rails",         "engine": "google", "q": 'site:hammerandrails.com ("men\'s basketball" OR "Purdue basketball")'},
    {"label": "Google News — GoldandBlack (Rivals)",  "engine": "google", "q": 'site:goldandblack.com (basketball OR "men\'s basketball")'},
    {"label": "Google News — On3 Purdue",             "engine": "google", "q": 'site:on3.com/teams/purdue-boilermakers/ (basketball OR hoops OR "men\'s basketball")'},
    {"label": "Google News — 247Sports Purdue",       "engine": "google", "q": 'site:247sports.com/college/purdue/ (basketball OR hoops OR "men\'s basketball")'},
    {"label": "Google News — USA Today Purdue",       "engine": "google", "q": 'site:usatoday.com Purdue ("men\'s basketball" OR basketball)'},
    {"label": "Google News — Sports Illustrated",     "engine": "google", "q": 'site:si.com Purdue (basketball OR "men\'s basketball")'},
]

# -------------------------------------------------------------------
# YouTube sources
YOUTUBE_SOURCES = [
    # Official playlist and channel
    {"label": "YouTube — Purdue MBB Playlist", "type": "yt_playlist", "id": "PL5oQyF7b7p3bQbXyMb8y6Q5-demo"},  # replace with actual if you have it
    {"label": "YouTube — PurdueSports (channel)", "type": "yt_channel", "id": "UCgGQ2n-demo"},                 # replace with actual if you have it

    # Commentary channels you like
    {"label": "YouTube — Sleepers Media (channel)", "type": "yt_channel", "id": "UCaG3-demo"},
]

# -------------------------------------------------------------------
# Reddit
REDDIT_SOURCES = [
    {"label": "Reddit — r/Boilermakers",     "sub": "Boilermakers"},
    {"label": "Reddit — r/CollegeBasketball","sub": "CollegeBasketball"},
]

# -------------------------------------------------------------------
# UI quick links (optional; server can ignore these safely)
QUICK_LINKS = [
    ("Purdue — Official MBB Page", "https://purduesports.com/sports/mens-basketball"),
    ("Purdue — Schedule",          "https://purduesports.com/sports/mens-basketball/schedule"),
    ("Purdue — Roster",            "https://purduesports.com/sports/mens-basketball/roster"),
    ("ESPN — Purdue MBB",          "https://www.espn.com/mens-college-basketball/team/_/id/2509/purdue-boilermakers"),
    ("CBS Sports — Purdue",        "https://www.cbssports.com/college-basketball/teams/PUR/purdue-boilermakers/"),
    ("Yahoo Sports — Purdue",      "https://sports.yahoo.com/ncaab/teams/purdue/"),
    ("Hammer & Rails (SB Nation)", "https://www.hammerandrails.com/"),
    ("GoldandBlack (Rivals)",      "https://goldandblack.com/"),
    ("Reddit — r/Boilermakers",    "https://www.reddit.com/r/Boilermakers/"),
    ("YouTube — Field of 68",      "https://www.youtube.com/@TheFieldOf68"),
    ("YouTube — Sleepers Media",   "https://www.youtube.com/@SleepersMedia"),
]
