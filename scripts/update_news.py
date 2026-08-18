#!/usr/bin/env python3
import json
import re
import html
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "news.json"
OSLO = ZoneInfo("Europe/Oslo")
MAX_STORIES = 10
MAX_AGE_HOURS = 72

QUERIES = [
    ("Narvik", 'Narvik OR "Ofoten"'),
    ("Næringsliv", 'Narvik næringsliv OR investering OR arbeidsplasser'),
    ("Industri", 'Narvik industri OR LKAB OR havn OR mineraler'),
    ("Samferdsel", 'Narvik samferdsel OR Ofotbanen OR E6 OR jernbane OR Evenes'),
    ("Politikk", 'Narvik politikk OR kommune OR regjeringen Nordland'),
    ("Nord-Norge", '"Nord-Norge" næringsliv OR Troms OR Nordland'),
]

WHY = {
    "Narvik": "Kan påvirke Narvik, lokale arbeidsplasser eller utviklingen i kommunen.",
    "Næringsliv": "Kan påvirke investeringer, arbeidsplasser eller rammevilkår for næringslivet.",
    "Industri": "Relevant for verdiskaping, eksport og industrielle arbeidsplasser i regionen.",
    "Samferdsel": "Transport og infrastruktur påvirker folk, godsstrømmer og konkurransekraft.",
    "Politikk": "Politiske beslutninger kan endre prioriteringer og rammevilkår i nord.",
    "Nord-Norge": "Regional utvikling kan få direkte konsekvenser for Narvik og næringslivet.",
}


def clean_text(value):
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def clean_title(title, source=""):
    title = clean_text(title)
    # Google News legger ofte kilden etter siste bindestrek.
    if source:
        title = re.sub(rf"\s+-\s+{re.escape(source)}\s*$", "", title, flags=re.I)
    # Fjern typiske feed-prefikser som gjør overskriften tung å skanne.
    title = re.sub(r"^(Evenes,\s*Harstad Narvik lufthavn Evenes\s*[|:]\s*)", "", title, flags=re.I)
    title = re.sub(r"^(Narvik\s*[|:]\s*)", "", title, flags=re.I)
    title = re.sub(r"\s*[|]\s*[^|]{1,45}$", "", title) if title.count("|") == 1 else title
    return title.strip(" -–—|")


def clean_summary(description, title, source):
    text = clean_text(description)
    if source:
        text = re.sub(rf"\s*{re.escape(source)}\s*$", "", text, flags=re.I).strip(" -–—|")
    # Mange Google News-beskrivelser er bare overskriften gjentatt.
    if not text or text.lower() == title.lower() or title.lower() in text.lower():
        return f"Ny sak fra {source or 'norsk presse'}. Åpne originalkilden for hele saken."
    if len(text) > 220:
        text = text[:217].rsplit(" ", 1)[0] + "…"
    return text


def google_news_url(query):
    params = urllib.parse.urlencode({"q": query, "hl": "no", "gl": "NO", "ceid": "NO:no"})
    return f"https://news.google.com/rss/search?{params}"


def fetch_feed(query):
    req = urllib.request.Request(google_news_url(query), headers={"User-Agent": "Mozilla/5.0 NarvikBrief/2.0"})
    with urllib.request.urlopen(req, timeout=20) as response:
        return response.read()


def parse_items(xml_bytes, category):
    root = ET.fromstring(xml_bytes)
    items = []
    now = datetime.now(timezone.utc)
    for item in root.findall("./channel/item"):
        raw_title = clean_text(item.findtext("title"))
        link = clean_text(item.findtext("link"))
        source = clean_text(item.findtext("source"))
        pub_raw = clean_text(item.findtext("pubDate"))
        if not raw_title or not link:
            continue
        try:
            published_dt = parsedate_to_datetime(pub_raw).astimezone(timezone.utc)
        except Exception:
            continue
        if now - published_dt > timedelta(hours=MAX_AGE_HOURS):
            continue
        title = clean_title(raw_title, source)
        if len(title) < 12:
            continue
        summary = clean_summary(item.findtext("description"), title, source)
        items.append({
            "category": category,
            "published_dt": published_dt,
            "title": title,
            "summary": summary,
            "whyItMatters": WHY[category],
            "url": link,
            "source": source,
        })
    return items


def normalize_title(title):
    return re.sub(r"[^a-z0-9æøå]+", " ", title.lower()).strip()


def dedupe_latest(items):
    # Hovedregelen er ferskhet: briefen skal alltid være de 10 siste relevante sakene.
    items = sorted(items, key=lambda x: x["published_dt"], reverse=True)
    seen = set()
    result = []
    for item in items:
        words = normalize_title(item["title"]).split()
        key = " ".join(words[:9])
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def main():
    all_items, errors = [], []
    for category, query in QUERIES:
        try:
            all_items.extend(parse_items(fetch_feed(query), category))
        except Exception as exc:
            errors.append(f"{category}: {exc}")

    selected = dedupe_latest(all_items)[:MAX_STORIES]
    if not selected:
        raise RuntimeError("Ingen ferske saker funnet. " + "; ".join(errors))

    now_oslo = datetime.now(OSLO)
    stories = []
    for item in selected:
        published = item["published_dt"].astimezone(OSLO)
        stories.append({
            "category": item["category"],
            "published": published.strftime("%d.%m. %H:%M"),
            "title": item["title"],
            "summary": item["summary"],
            "whyItMatters": item["whyItMatters"],
            "url": item["url"],
            "source": item["source"],
        })

    payload = {"updatedAt": now_oslo.strftime("%d.%m.%Y kl. %H:%M"), "stories": stories}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Publiserte de {len(stories)} siste relevante sakene.")
    for error in errors:
        print("Advarsel:", error)


if __name__ == "__main__":
    main()
