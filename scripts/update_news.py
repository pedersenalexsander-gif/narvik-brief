#!/usr/bin/env python3
import hashlib
import html
import json
import math
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "news.json"
IMAGE_DIR = ROOT / "assets" / "news"
IMAGE_DIR.mkdir(parents=True, exist_ok=True)
OSLO = ZoneInfo("Europe/Oslo")
MAX_STORIES = 10
MAX_AGE