#!/usr/bin/env python3
import hashlib
import html
import json
import os
import re
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
MAX_AGE_HOURS = 60
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

# En bevisst miks: lokalt først, men ikke en vegg av små lokale saker.
CATEGORY_QUOTAS = {
    "Narvik": 2,
    "Nord-Norge": 1,
    "Norge": 2,
    "Verden": 2,
    "USA": 1,
    "Økonomi": 2,
}

QUERIES = [
    ("Narvik", 'Narvik (næringsliv OR kommune OR investering OR industri OR Ofotbanen OR E6 OR havn OR forsvar)'),
    ("Nord-Norge", '"Nord-Norge" (næringsliv OR forsvar OR energi OR investering OR politikk)'),
    ("Norge", 'Norge (regjeringen OR Stortinget OR sikkerhet OR næringsliv OR økonomi OR teknologi)'),
    ("Verden", 'verden (krig OR diplomati OR sikkerhet OR økonomi OR teknologi OR klima)'),
    ("USA", 'USA (president OR Kongressen OR Fed OR økonomi OR sikkerhet OR teknologi)'),
    ("Økonomi", 'økonomi (Norges Bank OR renter OR børs OR olje OR krone OR aksjer OR finansmarked)'),
]

BLOCKED = [
    "arctic race", "alpin vm", "ol-gren", "ol gren", "folkemøte narvik 2029",
    "god morgen narvik", "god dag narvik", "været i narvik", "vær i narvik",
    "fotball", "håndball", "ishockey", "resultater fra",
]

IMPORTANT = {
    "regjering": 3, "storting": 3, "norges bank": 4, "rente": 3, "inflasjon": 3,
    "arbeidsplasser": 3, "investering": 3, "milliard": 3, "oppkjøp": 2,
    "forsvar": 3, "sikkerhet": 3, "krig": 3, "fred": 2, "sanksjon": 2,
    "børs": 3, "aksje": 2, "olje": 2, "krone": 2, "marked": 2,
    "kunstig intelligens": 2, "teknologi": 2, "ofotban": 4, "e6": 3, "havn": 3,
}

WHY = {
    "Narvik": "Dette kan få konkrete følger for Narvik, arbeidsplasser, investeringer eller viktige lokale beslutninger.",
    "Nord-Norge": "Saken kan påvirke rammevilkår, investeringer eller utviklingen i Nord-Norge – og dermed også Narvik.",
    "Norge": "Dette er en nasjonal utvikling som kan påvirke økonomi, politikk, sikkerhet eller hverdagen i Norge.",
    "Verden": "Dette er en internasjonal utvikling med mulig betydning for geopolitikk, økonomi eller markeder.",
    "USA": "Utviklingen i USA kan påvirke global politikk, sikkerhet, teknologi og finansmarkeder.",
    "Økonomi": "Dette kan påvirke renter, markeder, bedrifter, investeringer eller privatøkonomien.",
}


def clean_text(value):
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def clean_title(title, source=""):
    title = clean_text(title)
    if source:
        title = re.sub(rf"\s+-\s+{re.escape(source)}\s*$", "", title, flags=re.I)
    # Fjern vanlige portal-/seksjonsprefikser og overflødig feed-støy.
    title = re.sub(r"^(Narvik|Evenes|Harstad|God morgen,? Narvik|God dag Narvik)\s*[|:]\s*", "", title, flags=re.I)
    title = re.sub(r"\s+\|\s+[^|]{1,35}$", "", title)
    return title.strip(" -–—|")


def is_blocked(title):
    low = title.lower()
    return any(term in low for term in BLOCKED)


def google_news_url(query):
    params = urllib.parse.urlencode({"q": query, "hl": "no", "gl": "NO", "ceid": "NO:no"})
    return f"https://news.google.com/rss/search?{params}"


def fetch_feed(query):
    req = urllib.request.Request(google_news_url(query), headers={"User-Agent": "Mozilla/5.0 NarvikBrief/3.0"})
    with urllib.request.urlopen(req, timeout=20) as response:
        return response.read()


def story_id(title, source):
    raw = f"{title.lower()}|{source.lower()}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:14]


def parse_items(xml_bytes, category):
    root = ET.fromstring(xml_bytes)
    now = datetime.now(timezone.utc)
    result = []
    for item in root.findall("./channel/item"):
        source = clean_text(item.findtext("source"))
        title = clean_title(item.findtext("title"), source)
        url = clean_text(item.findtext("link"))
        description = clean_text(item.findtext("description"))
        pub_raw = clean_text(item.findtext("pubDate"))
        if not title or not url or len(title) < 15 or is_blocked(title):
            continue
        try:
            published_dt = parsedate_to_datetime(pub_raw).astimezone(timezone.utc)
        except Exception:
            continue
        age_hours = (now - published_dt).total_seconds() / 3600
        if age_hours > MAX_AGE_HOURS:
            continue
        if source:
            description = re.sub(rf"\s*{re.escape(source)}\s*$", "", description, flags=re.I).strip(" -–—|")
        if title.lower() in description.lower():
            description = description.replace(title, "").strip(" -–—|")
        score = max(0, int(10 - age_hours / 4))
        score += sum(weight for word, weight in IMPORTANT.items() if word in f"{title} {description}".lower())
        result.append({
            "id": story_id(title, source),
            "category": category,
            "published_dt": published_dt,
            "title": title,
            "description": description[:900],
            "url": url,
            "source": source or "Nyhetskilde",
            "score": score,
        })
    return result


def normalize_title(title):
    return re.sub(r"[^a-z0-9æøå]+", " ", title.lower()).strip()


def dedupe(items):
    seen = set()
    out = []
    for item in sorted(items, key=lambda x: (x["score"], x["published_dt"]), reverse=True):
        key = " ".join(normalize_title(item["title"]).split()[:9])
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def select_balanced(items):
    chosen, chosen_ids = [], set()
    for category, quota in CATEGORY_QUOTAS.items():
        pool = [x for x in items if x["category"] == category and x["id"] not in chosen_ids]
        pool.sort(key=lambda x: (x["score"], x["published_dt"]), reverse=True)
        for item in pool[:quota]:
            chosen.append(item)
            chosen_ids.add(item["id"])
    if len(chosen) < MAX_STORIES:
        rest = [x for x in items if x["id"] not in chosen_ids]
        rest.sort(key=lambda x: (x["score"], x["published_dt"]), reverse=True)
        chosen.extend(rest[:MAX_STORIES - len(chosen)])
    chosen.sort(key=lambda x: x["published_dt"], reverse=True)
    return chosen[:MAX_STORIES]


def fallback_ai(item):
    detail = item["description"] or f"{item['source']} omtaler denne utviklingen: {item['title']}."
    detail = detail[:320].strip()
    return {
        "aiSummary": detail,
        "keyPoints": [
            item["title"],
            f"Kilde: {item['source']}",
        ],
        "whyItMatters": WHY[item["category"]],
        "aiGenerated": False,
    }


def call_openai(item):
    if not OPENAI_API_KEY:
        return fallback_ai(item)
    prompt = f"""Du er redaktør for en personlig norsk nyhetsbrief. Lag en nøktern oversikt basert KUN på informasjonen under. Ikke finn på fakta. Hvis kildeinformasjonen er knapp, si det tydelig. Svar kun med gyldig JSON med feltene aiSummary (2-4 korte setninger), keyPoints (array med 2-4 korte punkter), whyItMatters (1-2 setninger).

Kategori: {item['category']}
Tittel: {item['title']}
Kilde: {item['source']}
Kildebeskrivelse: {item['description'] or 'Ingen ekstra beskrivelse tilgjengelig.'}
"""
    body = json.dumps({"model": "gpt-5.6-luna", "input": prompt}).encode("utf-8")
    req = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=body,
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            payload = json.loads(response.read().decode("utf-8"))
        text_parts = []
        for output in payload.get("output", []):
            for content in output.get("content", []):
                if content.get("type") == "output_text":
                    text_parts.append(content.get("text", ""))
        text = "".join(text_parts).strip()
        match = re.search(r"\{.*\}", text, flags=re.S)
        data = json.loads(match.group(0) if match else text)
        return {
            "aiSummary": clean_text(data.get("aiSummary", "")) or fallback_ai(item)["aiSummary"],
            "keyPoints": [clean_text(x) for x in data.get("keyPoints", []) if clean_text(x)][:4],
            "whyItMatters": clean_text(data.get("whyItMatters", "")) or WHY[item["category"]],
            "aiGenerated": True,
        }
    except Exception as exc:
        print(f"AI-oppsummering feilet for {item['id']}: {exc}")
        return fallback_ai(item)


def load_previous():
    try:
        data = json.loads(OUT.read_text(encoding="utf-8"))
        return data, {story.get("id"): story for story in data.get("stories", []) if story.get("id")}
    except Exception:
        return {}, {}


def main():
    all_items, errors = [], []
    for category, query in QUERIES:
        try:
            all_items.extend(parse_items(fetch_feed(query), category))
        except Exception as exc:
            errors.append(f"{category}: {exc}")

    selected = select_balanced(dedupe(all_items))
    if not selected:
        raise RuntimeError("Ingen relevante saker funnet. " + "; ".join(errors))

    previous_data, previous = load_previous()
    stories = []
    for item in selected:
        old = previous.get(item["id"], {})
        ai = {
            "aiSummary": old.get("aiSummary"),
            "keyPoints": old.get("keyPoints"),
            "whyItMatters": old.get("whyItMatters"),
            "aiGenerated": old.get("aiGenerated", False),
        }
        if not ai["aiSummary"]:
            ai = call_openai(item)
        published = item["published_dt"].astimezone(OSLO)
        stories.append({
            "id": item["id"],
            "category": item["category"],
            "published": published.strftime("%d.%m. %H:%M"),
            "publishedISO": published.isoformat(),
            "title": item["title"],
            "summary": ai["aiSummary"],
            "keyPoints": ai["keyPoints"] or [item["title"]],
            "whyItMatters": ai["whyItMatters"],
            "aiGenerated": ai["aiGenerated"],
            "url": item["url"],
            "source": item["source"],
        })

    previous_ids = [x.get("id") for x in previous_data.get("stories", [])]
    current_ids = [x["id"] for x in stories]
    if previous_ids == current_ids and all(previous.get(x["id"], {}).get("summary") == x["summary"] for x in stories):
        print("Ingen endring i topp 10. Lar filen stå urørt.")
        return

    now_oslo = datetime.now(OSLO)
    payload = {
        "updatedAt": now_oslo.strftime("%d.%m.%Y kl. %H:%M"),
        "updatedISO": now_oslo.isoformat(),
        "stories": stories,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Oppdaterte briefen med {len(stories)} kuraterte saker.")
    for error in errors:
        print("Advarsel:", error)


if __name__ == "__main__":
    main()
