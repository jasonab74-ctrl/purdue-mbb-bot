# collect.py
# Purdue MEN'S BASKETBALL–only collector with fast timeouts + Reddit support

from __future__ import annotations
import os
import re
import sys
import time
import html
import json
import math
import urllib.parse as urlparse
from datetime import datetime, timezone
from typing import List, Dict, Any

import requests
import feedparser


# ------------ HTTP settings ------------
HTTP_TIMEOUT = (6, 12)  # (connect, read) seconds
HEADERS = {
    "User-Agent": "purdue-mbb-bot/1.0 (+https://purdue-mbb-api.onrender.com)",
    "Accept": "application/rss+xml, application/xml;q=0.9, text/xml;q=0.8, */*;q=0.5",
}

# ------------ Feeds ------------
# Focus on MBB via Google News queries + Hammer & Rails + Reddit searches.
FEEDS: List[str] = [
    # Google News queries (RSS)
    "https://news.google.com/rss/search?q=%22Purdue%20men%27s%20basketball%22&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=Purdue%20Boilermakers%20men%27s%20basketball&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=Purdue%20basketball%20Matt%20Painter&hl=en-US&gl=US&ceid=US:en",
    # SB Nation – Purdue (has multi-sport; we filter to MBB)
    "https://www.hammerandrails.com/rss/index.xml",
    # Reddit searches (RSS)
    "https://www.reddit.com/r/Boilermakers/search.rss?q=Purdue%20men%27s%20basketball&restrict_sr=on&sort=new&t=month",
    "https://www.reddit.com/r/Boilermakers/search.rss?q=mbb%20OR%20basketball&restrict_sr=on&sort=new&t=month",
    "https://www.reddit.com/r/CollegeBasketball/search.rss?q=Purdue&restrict_sr=on&sort=new&t=month",
]

# ------------ Filtering ------------
NEG_WORDS = {
    # other sports
    "football", "nfl", "ross-ade", "soccer", "volleyball", "baseball", "softball",
    "wrestling", "golf", "swim", "swimming", "tenn
