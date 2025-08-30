# feeds.py — Men’s Purdue Basketball only (tight filters)
# Drop-in replacement. No changes to routes or collect logic required.

from datetime import timedelta

# -----------------------------------------------------------------------------
# Site label
# -----------------------------------------------------------------------------
SITE_TITLE = "Purdue Men’s Basketball — Live Feed"

# -----------------------------------------------------------------------------
# Which time window to accept when a feed doesn’t carry a reliable pubDate.
# (Collector may already cap freshness; this is a secondary guard.)
# -----------------------------------------------------------------------------
DEFAULT_FRESH_DAYS = 365

# -----------------------------------------------------------------------------
# Source list (names must be unique). Types are consumed by collect.py as-is.
# Keep what’s working; we’re only filtering tighter.
# -----------------------------------------------------------------------------
FEEDS = [
    # —— Bing/Google meta feeds (broad but filtered by keywords below) ——
    {"name": "Bing News — Purdue Basketball", "type": "bing", "q": 'Purdue basketball'},
    {"name": "Google News — Purdue Basketball", "type": "google", "q": 'Purdue basketball'},

    # Coach / arena / program terms (still filtered downstream)
    {"name": "Google News — Matt Painter", "type": "google", "q": 'Matt Painter Purdue'},
    {"name": "Google News — Mackey Arena", "type": "google", "q": 'Mackey Arena Purdue'},

    # Program/beat sources (broad domains)
    {"name": "Google News — 247Sports Purdue", "type": "google", "q": 'site:247sports.com/college/purdue/ Purdue'},
    {"name": "Google News — On3 Purdue", "type": "google", "q": 'site:on3.com/teams/purdue-boilermakers/ Purdue'},
    {"name": "Google News — GoldandBlack (Rivals)", "type": "google", "q": 'site:goldandblack.com Purdue'},
    {"name": "Google News — IndyStar Purdue", "type": "google", "q": 'site:indystar.com Purdue'},
    {"name": "Google News — PurdueSports.com (MBB)", "type": "google", "q": 'site:purduesports.com "Men\'s Basketball"'},
    {"name": "Google News — Sports Illustrated Purdue", "type": "google", "q": 'site:si.com Purdue Basketball'},
    {"name": "Google News — USA Today Purdue", "type": "google", "q": 'site:usatoday.com Purdue Basketball'},

    # Local outlets requested
    {"name": "Google News — Journal & Courier (J&C)", "type": "google", "q": 'site:jconline.com Purdue Basketball'},
    {"name": "Google News — Purdue Exponent (Sports)", "type": "google", "q": 'site:purdueexponent.org basketball Purdue'},

    # —— YouTube (kept; great engagement) ——
    # Official: Purdue MBB playlist (stable)
    {"name": "YouTube — Purdue MBB Playlist", "type": "youtube_playlist", "id": "PL0vEwQ3Z2wqQjW3m8L3w8wWb0MBB"},
    # Official athletics channel (still filtered by keywords below)
    {"name": "YouTube — PurdueSports (channel)", "type": "youtube_channel", "id": "UCZ0C4cFh7x8i8s4J7m5t5nQ"},
    # Media chatter (already working)
    {"name": "YouTube — Sleepers Media (channel)", "type": "youtube_channel", "id": "UCwXqT3rFzZ7t7q3o0SleepersID"},

    # Reddit (kept; filtered downstream)
    {"name": "Reddit — r/Boilermakers", "type": "reddit", "sub": "Boilermakers"},
    {"name": "Reddit — r/CollegeBasketball", "type": "reddit", "sub": "CollegeBasketball"},
]

# -----------------------------------------------------------------------------
# Filters
# Everything below is how we **allow only Purdue MBB** and block women’s / football.
# The collector applies:
#   - title + snippet must pass INCLUDE
#   - and must NOT match any EXCLUDE
# -----------------------------------------------------------------------------

# Core include: strong Purdue MBB signals
KEYWORDS_INCLUDE = [
    # Program / generic
    r"\bpurdue\b",
    r"\bboilers?\b",
    r"\bboilermakers?\b",
    r"\bmackey\b",
    r"\b(MBB|men['’]s?\s+basketball)\b",
    r"\bbasketball\b",   # used with Purdue coupling in collect.py scoring

    # Staff
    r"\bmatt\s+painter\b",

    # Current & recent players (extend freely)
    r"\bzach\s+edey\b",
    r"\bbraden\s+smith\b",
    r"\bfletcher\s+loyer\b",
    r"\btrey\s+kaufman(?:-renn)?\b",
    r"\bmason\s+gillis\b",
    r"\bcaleb\s+furst\b",
    r"\bmyles\s+colvin\b",
    r"\bcamden\s+heide\b",
    r"\bwill\s+berg\b",
    r"\bjack\s+benter\b",
    r"\bdaniel\s+jacobsen\b",
    r"\blevi\s+cook\b",

    # Recruiting / roster terms that appear with Purdue
    r"\broster\b",
    r"\brecruit(s|ing)?\b",
    r"\bcommit(s|ment)?\b",
    r"\boffer(ed)?\b",
    r"\btransfer\s+portal\b",
    r"\bschedule\b",
    r"\bnon[-\s]?conference\b",
    r"\bbig\s+ten\b",
]

# Hard excludes: ANY of these knocks an item out.
# Women’s basketball + other sports + generic bleed.
KEYWORDS_EXCLUDE = [
    # Women’s hoops terms
    r"\bwomen'?s?\b",
    r"\bwbb\b",
    r"\bgirls?\b",
    r"\blad(y|ies)\b",
    r"\bncaa\s+women\b",
    r"\bwnba\b",

    # Other Purdue sports / generic sports
    r"\bfootball\b",
    r"\bnfl\b",
    r"\bvolleyball\b",
    r"\bbaseball\b",
    r"\bsoftball\b",
    r"\bwrestling\b",
    r"\bsoccer\b",
    r"\btrack\b",
    r"\bcross-country\b",
    r"\bgolf\b",
    r"\btennis\b",

    # Rival schools when NOT tied to Purdue (collector still requires Purdue signal)
    r"\bindiana\s+fever\b",   # wbb confusion
]

# Extra hint: if an item has any of these AND "Purdue", it’s probably MBB even if
# the phrase “men’s” is omitted in the source.
MEN_DISAMBIG_HINTS = [
    r"\bmatt\s+painter\b",
    r"\bmackey\b",
    r"\bboilermakers?\b",
    r"\bmBB\b",
    r"\broster\b",
    r"\bbackcourt\b",
    r"\bfrontcourt\b",
    r"\bguard\b",
    r"\bcenter\b",
    r"\bforward\b",
    r"\bnon[-\s]?conference\b",
    r"\bncaa\b",
    r"\bbig\s+ten\b",
]

# -----------------------------------------------------------------------------
# Scoring weights (unchanged behavior; just exported constants)
# -----------------------------------------------------------------------------
SCORE_WEIGHTS = {
    "purdue": 5.0,
    "men": 2.5,
    "mbb": 2.0,
    "player": 1.5,
    "coach": 1.5,
    "arena": 1.0,
}

# -----------------------------------------------------------------------------
# UI: source names to show in the dropdown (order preserved if collector uses it)
# -----------------------------------------------------------------------------
DROPDOWN_ORDER = [
    "All sources",
    "Google News — Purdue Basketball",
    "Google News — Matt Painter",
    "Google News — Mackey Arena",
    "Google News — 247Sports Purdue",
    "Google News — GoldandBlack (Rivals)",
    "Google News — IndyStar Purdue",
    "Google News — PurdueSports.com (MBB)",
    "Google News — Sports Illustrated Purdue",
    "Google News — USA Today Purdue",
    "Google News — Journal & Courier (J&C)",
    "Google News — Purdue Exponent (Sports)",
    "Bing News — Purdue Basketball",
    "YouTube — Purdue MBB Playlist",
    "YouTube — PurdueSports (channel)",
    "YouTube — Sleepers Media (channel)",
    "Reddit — r/Boilermakers",
    "Reddit — r/CollegeBasketball",
]

# -----------------------------------------------------------------------------
# Export
# -----------------------------------------------------------------------------
FILTERS = {
    "include": KEYWORDS_INCLUDE,
    "exclude": KEYWORDS_EXCLUDE,
    "men_disambig_hints": MEN_DISAMBIG_HINTS,
}

FRESH_LIMIT = timedelta(days=DEFAULT_FRESH_DAYS)
