#!/usr/bin/env python3
import hashlib
import html
import json
import math
import re
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "news.json"
OSLO = ZoneInfo("Europe/Oslo")
MAX_STORIES = 10
MAX_AGE_HOURS = 72
MIN_ARTICLE_CHARS = 1200

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
    "Narvik":"Kan få konkrete følger for Narvik, arbeidsplasser, investeringer eller viktige lokale beslutninger.",
    "Nord-Norge":"Kan påvirke rammevilkår, investeringer eller utviklingen i Nord-Norge – og dermed også Narvik.",
    "Norge":"En nasjonal utvikling som kan påvirke økonomi, politikk, sikkerhet eller hverdagen i Norge.",
    "Verden":"En internasjonal utvikling med mulig betydning for geopolitikk, økonomi eller markeder.",
    "USA":"Utviklingen i USA kan påvirke global politikk, sikkerhet, teknologi og finansmarkeder.",
    "Økonomi":"Kan påvirke renter, markeder, bedrifter, investeringer eller privatøkonomien.",
    "AI":"Kan endre konkurransebildet i teknologi, arbeidsliv, investeringer, sikkerhet eller regulering globalt.",
}
STOPWORDS = set("""
og i på til for av en et ei som det den de er var blir ble har hadde med om fra ved etter før også men eller ikke sin sine sitt seg dette disse der her kan vil skal må mot over under mellom ut inn når hvor hva hvem hvilken hvilke fordi derfor dersom hvis samt than the and a an of to in on for from with by as is are was were be been being it its this that these those or but not into over under after before about which who what when where how can could will would should may might""".split())

class ArticleParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_article = 0; self.in_p = 0; self.current = []
        self.article_paragraphs = []; self.all_paragraphs = []
        self.image = ""; self.canonical = ""; self.title = ""
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "article": self.in_article += 1
        if tag == "p": self.in_p += 1; self.current = []
        if tag == "meta":
            prop = (attrs.get("property") or attrs.get("name") or "").lower()
            content = attrs.get("content", "")
            if prop in ("og:image", "twitter:image", "twitter:image:src") and not self.image: self.image = content
            if prop in ("og:title", "twitter:title") and not self.title: self.title = content
        if tag == "link" and "canonical" in (attrs.get("rel") or "").lower(): self.canonical = attrs.get("href", "")
    def handle_endtag(self, tag):
        if tag == "p" and self.in_p:
            text = " ".join("".join(self.current).split())
            if len(text) >= 45:
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

def gdelt_search(query, maxrecords=60):
    params = urllib.parse.urlencode({"query": query, "mode": "ArtList", "maxrecords": maxrecords, "format": "json", "sort": "HybridRel"})
    req = urllib.request.Request("https://api.gdeltproject.org/api/v2/doc/doc?" + params, headers={"User-Agent":"AlexBrief/7.0"})
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
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0 (compatible; AlexBrief/7.0)", "Accept-Language":"nb-NO,nb;q=0.9,en;q=0.8"})
    with urllib.request.urlopen(req, timeout=20) as response:
        final_url = response.geturl(); raw = response.read(2_500_000); content_type = response.headers.get("Content-Type", "")
    if "text/html" not in content_type.lower(): return None
    source_html = raw.decode("utf-8", errors="replace")
    low = source_html.lower()
    if any(term in low for term in PAYWALL_TERMS): return None
    parser = ArticleParser()
    try: parser.feed(source_html)
    except Exception: return None
    paragraphs = parser.article_paragraphs if sum(map(len, parser.article_paragraphs)) >= MIN_ARTICLE_CHARS else parser.all_paragraphs
    cleaned, seen = [], set()
    noise = ["cookie", "newsletter", "sign up", "meld deg på", "personvern", "privacy policy", "les også", "related article", "advertisement"]
    for p in paragraphs:
        pl = p.lower()
        if any(x in pl for x in noise): continue
        key = p[:140]
        if key in seen: continue
        seen.add(key); cleaned.append(p)
    article_text = "\n\n".join(cleaned)
    if len(article_text) < MIN_ARTICLE_CHARS: return None
    image = urllib.parse.urljoin(final_url, parser.image) if parser.image else ""
    canonical = urllib.parse.urljoin(final_url, parser.canonical) if parser.canonical else final_url
    return {"url": canonical, "text": article_text[:16000], "image": image, "page_title": clean_text(parser.title)}

def discover():
    now = datetime.now(timezone.utc); items = []
    for category, query in SEARCHES:
        try: articles = gdelt_search(query)
        except Exception as exc:
            print(f"GDELT-feil {category}: {exc}"); continue
        for art in articles:
            title = clean_text(art.get("title", "")); url = art.get("url", ""); source = art.get("domain") or "Nyhetskilde"
            if not title or not url or len(title) < 15 or is_blocked(title): continue
            published = parse_seen_date(art.get("seendate", "")); age = (now - published).total_seconds() / 3600
            if age > MAX_AGE_HOURS: continue
            score = max(0, int(12 - age/5)) + sum(w for k,w in IMPORTANT.items() if k in title.lower()) + (3 if category == "AI" else 0)
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
        if page.get("page_title") and len(page["page_title"]) > 15: item["title"] = page["page_title"]
        item["url"]=page["url"]; item["article_text"]=page["text"]; item["image"]=page["image"] or item.get("social_image", "")
        accessible.append(item)
        if len(accessible) >= 45: break
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

def split_sentences(text):
    text = re.sub(r"\s+", " ", text).strip()
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-ZÆØÅ0-9])", text)
    return [s.strip() for s in sentences if 55 <= len(s.strip()) <= 420]

def words(text):
    return [w for w in re.findall(r"[a-zA-ZæøåÆØÅ0-9-]{3,}", text.lower()) if w not in STOPWORDS and not w.isdigit()]

def summarize_locally(title, article_text, category):
    sentences = split_sentences(article_text)
    if len(sentences) < 4: return None
    freq = Counter(words(article_text))
    if not freq: return None
    maxfreq = max(freq.values())
    weights = {w: math.log1p(c) / math.log1p(maxfreq) for w,c in freq.items()}
    title_terms = set(words(title))
    scored=[]
    for idx,s in enumerate(sentences[:80]):
        sw=words(s)
        if not sw: continue
        lexical=sum(weights.get(w,0) for w in sw)/math.sqrt(len(sw))
        title_bonus=sum(1.7 for w in set(sw) & title_terms)
        position_bonus=max(0, 2.2 - idx*0.06)
        number_bonus=0.8 if re.search(r"\b\d+[\d.,%]*\b", s) else 0
        scored.append((lexical+title_bonus+position_bonus+number_bonus, idx, s))
    if len(scored)<3: return None
    top=sorted(scored, reverse=True)[:5]
    summary_sentences=[s for _,_,s in sorted(top[:3], key=lambda x:x[1])]
    summary=" ".join(summary_sentences)
    # Key points use additional strong sentences and avoid near-duplicates.
    points=[]
    for _,_,s in top:
        if any(len(set(words(s)) & set(words(p))) / max(1,min(len(set(words(s))),len(set(words(p))))) > .7 for p in points): continue
        points.append(s)
        if len(points)==4: break
    if len(summary)<180 or len(points)<2: return None
    return summary, points, WHY[category]

def main():
    candidates=dedupe(discover())
    accessible=enrich_accessible(candidates)
    selected=select_balanced(accessible)
    stories=[]
    for item in selected:
        generated=summarize_locally(item["title"], item["article_text"], item["category"])
        if not generated:
            print(f"Dropper sak som ikke kan oppsummeres robust: {item['title']}"); continue
        summary,points,why=generated
        published=item["published_dt"].astimezone(OSLO)
        stories.append({
            "id":item["id"],"category":item["category"],"published":published.strftime("%d.%m. %H:%M"),
            "publishedISO":published.isoformat(),"title":item["title"],"summary":summary,"keyPoints":points,
            "whyItMatters":why,"summaryMethod":"local-extractive","url":item["url"],"source":item["source"],"image":item.get("image","")
        })
    if len(stories)<4: raise RuntimeError(f"For få kvalitetsartikler etter fulltekstfiltrering ({len(stories)}). Beholder forrige brief i stedet for å publisere dårlig innhold.")
    now_oslo=datetime.now(OSLO)
    payload={"updatedAt":now_oslo.strftime("%d.%m.%Y kl. %H:%M"),"updatedISO":now_oslo.isoformat(),"qualityMode":"full-article-only-free","stories":stories[:MAX_STORIES]}
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Publiserte {len(stories[:MAX_STORIES])} gratis kvalitetsoppsummeringer fra full artikkeltekst.")

if __name__=="__main__": main()
