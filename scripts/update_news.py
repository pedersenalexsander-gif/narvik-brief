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
MAX_STORIES = 12
MAX_AGE_HOURS = 36

QUERIES = [
    ("Narvik", 'Narvik OR "Ofoten"'),
    ("Næringsliv", 'Narvik næringsliv OR investering OR arbeidsplasser'),
    ("Industri", 'Narvik industri OR LKAB OR havn OR mineraler'),
    ("Samferdsel", 'Narvik samferdsel OR Ofotbanen OR E6 OR jernbane OR fly'),
    ("Politikk", 'Narvik politikk OR kommune OR regjeringen Nordland'),
    ("Nord-Norge", '"Nord-Norge" næringsliv OR Troms OR Nordland'),
]

WHY = {
    "Narvik": "Lokale endringer kan påvirke innbyggere, arbeidsplasser og utviklingen i Narvik direkte.",
    "Næringsliv": "Dette kan påvirke investeringer, arbeidsplasser eller rammevilkår for næringslivet i regionen.",
    "Industri": "Industrien er sentral for verdiskaping, eksport og arbeidsplasser i Narvik-regionen.",
    "Samferdsel": "Transport og infrastruktur påvirker både folk, godsstrømmer og konkurransekraft i regionen.",
    "Politikk": "Politiske beslutninger kan endre rammevilkår, prioriteringer og investeringer i nord.",
    "Nord-Norge": "Utviklingen i Nord-Norge kan få direkte konsekvenser for Narvik og det regionale næringslivet.",
}

KEYWORDS = {
    "arbeidsplasser": 4,
    "investering": 4,
    "milliard": 4,
    "million": 2,
    "etabler": 3,
    "utbygg": 3,
    "havn": 3,
    "ofotban": 4,
    "jernbane": 3,
    "e6": 3,
    "lkab": 4,
    "narvik": 5,
    "nordland": 2,
    "troms": 2,
    "regjering": 2,
    "kommune": 2,
    "industri": 3,
    "energi": 2,
    "forsvar": 3,
}


def clean_text(value):
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def google_news_url(query):
    params = urllib.parse.urlencode({
        "q": query,
        "hl": "no",
        "gl": "NO",
        "ceid": "NO:no",
    })
    return f"https://news.google.com/rss/search?{params}"


def fetch_feed(query):
    req = urllib.request.Request(
        google_news_url(query),
        headers={"User-Agent": "Mozilla/5.0 NarvikBrief/1.0"},
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        return response.read()


def parse_items(xml_bytes, category):
    root = ET.fromstring(xml_bytes)
    items = []
    now = datetime.now(timezone.utc)

    for item in root.findall("./channel/item"):
        title = clean_text(item.findtext("title"))
        link = clean_text(item.findtext("link"))
        description = clean_text(item.findtext("description"))
        source = clean_text(item.findtext("source"))
        pub_raw = clean_text(item.findtext("pubDate"))

        if not title or not link:
            continue

        try:
            published_dt = parsedate_to_datetime(pub_raw).astimezone(timezone.utc)
        except Exception:
            published_dt = now

        age = now - published_dt
        if age > timedelta(hours=MAX_AGE_HOURS):
            continue

        if " - " in title:
            title_without_source, possible_source = title.rsplit(" - ", 1)
            if len(possible_source) < 80:
                title = title_without_source.strip()
                if not source:
                    source = possible_source.strip()

        summary = description
        if source and summary.endswith(source):
            summary = summary[: -len(source)].strip(" -–—")
        if not summary:
            summary = f"Ny sak fra {source or 'en norsk nyhetskilde'} om {title.lower()}."
        if len(summary) > 280:
            summary = summary[:277].rstrip() + "…"

        haystack = f"{title} {summary}".lower()
        score = max(0, int((MAX_AGE_HOURS - age.total_seconds() / 3600) / 6))
        score += sum(weight for keyword, weight in KEYWORDS.items() if keyword in haystack)
        if category == "Narvik":
            score += 3

        items.append({
            "category": category,
            "published_dt": published_dt,
            "title": title,
            "summary": summary,
            "whyItMatters": WHY[category],
            "url": link,
            "source": source,
            "score": score,
        })

    return items


def normalize_title(title):
    return re.sub(r"[^a-z0-9æøå]+", " ", title.lower()).strip()


def dedupe(items):
    seen = set()
    result = []
    for item in sorted(items, key=lambda x: (x["score"], x["published_dt"]), reverse=True):
        key = normalize_title(item["title"])
        compact = " ".join(key.split()[:8])
        if key in seen or compact in seen:
            continue
        seen.add(key)
        seen.add(compact)
        result.append(item)
    return result


def main():
    all_items = []
    errors = []

    for category, query in QUERIES:
        try:
            all_items.extend(parse_items(fetch_feed(query), category))
        except Exception as exc:
            errors.append(f"{category}: {exc}")

    selected = dedupe(all_items)[:MAX_STORIES]
    now_oslo = datetime.now(OSLO)

    stories = []
    for item in selected:
        published_oslo = item["published_dt"].astimezone(OSLO)
        stories.append({
            "category": item["category"],
            "published": published_oslo.strftime("%H:%M"),
            "title": item["title"],
            "summary": item["summary"],
            "whyItMatters": item["whyItMatters"],
            "url": item["url"],
            "source": item["source"],
        })

    if not stories:
        raise RuntimeError("Ingen ferske nyhetssaker ble funnet. " + "; ".join(errors))

    payload = {
        "updatedAt": now_oslo.strftime("%d.%m.%Y kl. %H:%M"),
        "stories": stories,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Skrev {len(stories)} saker til {OUT}")
    if errors:
        print("Noen søk feilet, men briefen ble likevel laget:")
        for error in errors:
            print("-", error)


if __name__ == "__main__":
    main()
