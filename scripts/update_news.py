#!/usr/bin/env python3
import hashlib
import html
import json
import os
import re
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "news.json"
OSLO = ZoneInfo("Europe/Oslo")
MAX_STORIES = 10
MAX_AGE_HOURS = 72
MIN_ARTICLE_CHARS = 900
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini").strip()

CATEGORY_QUOTAS = {"Narvik": 2, "Nord-Norge": 1, "Norge": 1, "Verden": 1, "USA": 1, "Økonomi": 2, "AI": 2}
SEARCHES = [
    ("Narvik", "Narvik industry investment municipality railway port defense"),
    ("Nord-Norge", '"Nord-Norge" business defense energy investment politics'),
    ("Norge", "Norway government parliament economy security technology"),
    ("Verden", "world geopolitics war diplomacy security economy technology"),
    ("USA", "United States president congress Federal Reserve economy security technology"),
    ("Økonomi", "markets interest rates central bank stocks oil finance economy"),
    ("AI", "OpenAI Anthropic DeepMind Nvidia artificial intelligence model chips regulation investment"),
    ("AI", "artificial intelligence AI safety regulation datacenter chips model launch"),
]

BLOCKED_TERMS = [
    "arctic race", "alpin vm", "ol-gren", "ol gren", "folkemøte narvik 2029",
    "god morgen narvik", "god dag narvik", "weather", "været i narvik", "vær i narvik",
    "fotball", "håndball", "ishockey", "results", "resultater fra", "quiz", "horoscope",
]
PAYWALL_TERMS = [
    "subscribe to continue", "subscription required", "subscriber only", "members only",
    "logg inn for å lese", "kjøp abonnement", "bli abonnent", "kun for abonnenter",
    "denne saken er for abonnenter", "premium article", "unlock this article",
]
IMPORTANT = {
    "narvik":4,"ofotban":4,"e6":3,"havn":3,"forsvar":3,"regjering":3,"storting":3,
    "norges bank":4,"rente":3,"inflasjon":3,"arbeidsplasser":3,"investering":3,"milliard":3,
    "sikkerhet":3,"krig":3,"børs":3,"aksje":2,"olje":2,"marked":2,"openai":4,"anthropic":4,
    "deepmind":3,"nvidia":3,"artificial intelligence":4,"kunstig intelligens":4,"chip":3,"regulation":3,
}
WHY = {
    "Narvik":"Dette kan få konkrete følger for Narvik, arbeidsplasser, investeringer eller viktige lokale beslutninger.",
    "Nord-Norge":"Saken kan påvirke rammevilkår, investeringer eller utviklingen i Nord-Norge – og dermed også Narvik.",
    "Norge":"Dette er en nasjonal utvikling som kan påvirke økonomi, politikk, sikkerhet eller hverdagen i Norge.",
    "Verden":"Dette er en internasjonal utvikling med mulig betydning for geopolitikk, økonomi eller markeder.",
    "USA":"Utviklingen i USA kan påvirke global politikk, sikkerhet, teknologi og finansmarkeder.",
    "Økonomi":"Dette kan påvirke renter, markeder, bedrifter, investeringer eller privatøkonomien.",
    "AI":"Dette kan endre konkurransebildet i teknologi, arbeidsliv, investeringer, sikkerhet eller regulering globalt.",
}

class ArticleParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_article = 0
        self.in_p = 0
        self.current = []
        self.article_paragraphs = []
        self.all_paragraphs = []
        self.image = ""
        self.canonical = ""
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "article": self.in_article += 1
        if tag == "p": self.in_p += 1; self.current = []
        if tag == "meta":
            prop = (attrs.get("property") or attrs.get("name") or "").lower()
            if prop in ("og:image", "twitter:image", "twitter:image:src") and not self.image:
                self.image = attrs.get("content", "")
        if tag == "link" and (attrs.get("rel") or "").lower() == "canonical":
            self.canonical = attrs.get("href", "")
    def handle_endtag(self, tag):
        if tag == "p" and self.in_p:
            text = " ".join("".join(self.current).split())
            if len(text) >= 40:
                self.all_paragraphs.append(text)
                if self.in_article: self.article_paragraphs.append(text)
            self.in_p = max(0, self.in_p - 1); self.current = []
        if tag == "article" and self.in_article: self.in_article -= 1
    def handle_data(self, data):
        if self.in_p: self.current.append(data)


def clean_text(value):
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()

def is_blocked(title): return any(x in title.lower() for x in BLOCKED_TERMS)
def story_id(title, source): return hashlib.sha1(f"{title.lower()}|{source.lower()}".encode()).hexdigest()[:14]
def normalize_title(title): return re.sub(r"[^a-z0-9æøå]+", " ", title.lower()).strip()

def gdelt_search(query, maxrecords=40):
    params = urllib.parse.urlencode({"query": query, "mode": "ArtList", "maxrecords": maxrecords, "format": "json", "sort": "HybridRel"})
    req = urllib.request.Request("https://api.gdeltproject.org/api/v2/doc/doc?" + params, headers={"User-Agent":"AlexBrief/6.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8", errors="replace"))
    return payload.get("articles", [])

def parse_seen_date(value):
    for fmt in ("%Y%m%dT%H%M%SZ", "%Y%m%dT%H%M%S%z", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            dt = datetime.strptime(value, fmt)
            return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
        except Exception: pass
    return datetime.now(timezone.utc)

def fetch_article(url):
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0 (compatible; AlexBrief/6.0)", "Accept-Language":"nb-NO,nb;q=0.9,en;q=0.8"})
    with urllib.request.urlopen(req, timeout=20) as response:
        final_url = response.geturl()
        raw = response.read(2_000_000)
        content_type = response.headers.get("Content-Type", "")
    if "text/html" not in content_type.lower(): return None
    text = raw.decode("utf-8", errors="replace")
    low = text.lower()
    if any(term in low for term in PAYWALL_TERMS): return None
    parser = ArticleParser()
    try: parser.feed(text)
    except Exception: return None
    paragraphs = parser.article_paragraphs if sum(map(len, parser.article_paragraphs)) >= MIN_ARTICLE_CHARS else parser.all_paragraphs
    # Fjern typisk meny/cookie-/newsletterstøy og gjentakelser.
    cleaned, seen = [], set()
    for p in paragraphs:
        pl = p.lower()
        if any(x in pl for x in ["cookie", "newsletter", "sign up", "meld deg på", "personvern", "privacy policy"]): continue
        key = p[:120]
        if key in seen: continue
        seen.add(key); cleaned.append(p)
    article_text = "\n\n".join(cleaned)
    if len(article_text) < MIN_ARTICLE_CHARS: return None
    image = urllib.parse.urljoin(final_url, parser.image) if parser.image else ""
    canonical = urllib.parse.urljoin(final_url, parser.canonical) if parser.canonical else final_url
    return {"url": canonical, "text": article_text[:12000], "image": image}

def discover():
    now = datetime.now(timezone.utc); items = []
    for category, query in SEARCHES:
        try: articles = gdelt_search(query)
        except Exception as exc:
            print(f"GDELT-feil {category}: {exc}"); continue
        for art in articles:
            title = clean_text(art.get("title", "")); url = art.get("url", ""); source = art.get("domain") or "Nyhetskilde"
            if not title or not url or len(title) < 15 or is_blocked(title): continue
            published = parse_seen_date(art.get("seendate", ""))
            age = (now - published).total_seconds() / 3600
            if age > MAX_AGE_HOURS: continue
            haystack = title.lower(); score = max(0, int(12 - age/5)) + sum(w for k,w in IMPORTANT.items() if k in haystack) + (3 if category == "AI" else 0)
            items.append({"id":story_id(title,source),"category":category,"published_dt":published,"title":title,"url":url,"source":source,"score":score,"social_image":art.get("socialimage") or ""})
    return items

def dedupe(items):
    seen=[]; out=[]
    for item in sorted(items,key=lambda x:(x["score"],x["published_dt"]),reverse=True):
        words=set(normalize_title(item["title"]).split())
        if any(len(words & old) / max(1, min(len(words), len(old))) > .72 for old in seen): continue
        seen.append(words); out.append(item)
    return out

def enrich_accessible(items):
    accessible=[]
    for item in items:
        try: page=fetch_article(item["url"])
        except Exception as exc:
            print(f"Dropper utilgjengelig artikkel: {item['title']} ({exc})"); continue
        if not page:
            print(f"Dropper sak uten nok lesbar artikkeltekst: {item['title']}"); continue
        item["url"]=page["url"]; item["article_text"]=page["text"]; item["image"]=page["image"] or item.get("social_image", "")
        accessible.append(item)
        if len(accessible) >= 35: break
    return accessible

def select_balanced(items):
    chosen, ids=[], set()
    for category,quota in CATEGORY_QUOTAS.items():
        pool=sorted([x for x in items if x["category"]==category and x["id"] not in ids],key=lambda x:(x["score"],x["published_dt"]),reverse=True)
        for item in pool[:quota]: chosen.append(item); ids.add(item["id"])
    if len(chosen)<MAX_STORIES:
        rest=sorted([x for x in items if x["id"] not in ids],key=lambda x:(x["score"],x["published_dt"]),reverse=True)
        chosen.extend(rest[:MAX_STORIES-len(chosen)])
    chosen.sort(key=lambda x:x["published_dt"],reverse=True)
    return chosen[:MAX_STORIES]

def extract_response_text(payload):
    if payload.get("output_text"): return payload["output_text"]
    parts=[]
    for output in payload.get("output",[]):
        for content in output.get("content",[]):
            if content.get("type")=="output_text": parts.append(content.get("text", ""))
    return "".join(parts).strip()

def call_openai(item):
    if not OPENAI_API_KEY: raise RuntimeError("OPENAI_API_KEY mangler")
    prompt=f'''Du er redaktør for Alex Brief. Lag en presis norsk AI-oversikt basert på den tilgjengelige artikkelteksten under. Ikke bruk kun overskriften, og ikke finn på fakta. Oppsummer hva som faktisk har skjedd, de viktigste detaljene og hvorfor saken betyr noe. Svar KUN som gyldig JSON med feltene aiSummary (3-5 informative setninger), keyPoints (3-5 konkrete punkter), whyItMatters (1-2 konkrete setninger).\n\nKategori: {item['category']}\nTittel: {item['title']}\nKilde: {item['source']}\n\nARTIKKELTEKST:\n{item['article_text'][:9000]}'''
    body=json.dumps({"model":OPENAI_MODEL,"input":prompt}).encode("utf-8")
    req=urllib.request.Request("https://api.openai.com/v1/responses",data=body,headers={"Authorization":f"Bearer {OPENAI_API_KEY}","Content-Type":"application/json"},method="POST")
    try:
        with urllib.request.urlopen(req,timeout=60) as response: payload=json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"OpenAI HTTP {exc.code}: {exc.read().decode(errors='replace')[:800]}") from exc
    text=extract_response_text(payload); match=re.search(r"\{.*\}", text, flags=re.S)
    data=json.loads(match.group(0) if match else text)
    summary=clean_text(data.get("aiSummary","")); points=[clean_text(x) for x in data.get("keyPoints",[]) if clean_text(x)][:5]; why=clean_text(data.get("whyItMatters",""))
    if len(summary)<100 or len(points)<2: raise RuntimeError("AI-responsen var for tynn")
    return summary,points,why or WHY[item["category"]]

def main():
    candidates=dedupe(discover())
    accessible=enrich_accessible(candidates)
    selected=select_balanced(accessible)
    if not selected: raise RuntimeError("Fant ingen ferske artikler med tilstrekkelig tilgjengelig artikkeltekst")
    stories=[]; ai_errors=[]
    for item in selected:
        try: summary,points,why=call_openai(item); ai_generated=True
        except Exception as exc:
            # Kilden er fortsatt fullstendig tilgjengelig, men vi skjuler saken hvis AI ikke kan lage ordentlig oversikt.
            ai_errors.append(f"{item['title']}: {exc}"); continue
        published=item["published_dt"].astimezone(OSLO)
        stories.append({"id":item["id"],"category":item["category"],"published":published.strftime("%d.%m. %H:%M"),"publishedISO":published.isoformat(),"title":item["title"],"summary":summary,"keyPoints":points,"whyItMatters":why,"aiGenerated":ai_generated,"url":item["url"],"source":item["source"],"image":item.get("image","")})
    if len(stories)<4: raise RuntimeError(f"For få kvalitetsartikler etter filtrering ({len(stories)}). AI-feil: {'; '.join(ai_errors[:3])}")
    now_oslo=datetime.now(OSLO)
    payload={"updatedAt":now_oslo.strftime("%d.%m.%Y kl. %H:%M"),"updatedISO":now_oslo.isoformat(),"qualityMode":"full-article-only","stories":stories[:MAX_STORIES]}
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Publiserte {len(stories[:MAX_STORIES])} saker. Alle har lesbar artikkeltekst og AI-oppsummering.")
    for error in ai_errors: print("AI-advarsel:",error)

if __name__=="__main__": main()
