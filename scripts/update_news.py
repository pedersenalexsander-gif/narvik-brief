#!/usr/bin/env python3
import hashlib
import html
import json
import os
import re
import urllib.parse
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "news.json"
OSLO = ZoneInfo("Europe/Oslo")
MAX_STORIES = 10
MAX_AGE_HOURS = 60
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini").strip()

CATEGORY_QUOTAS = {"Narvik": 2, "Nord-Norge": 1, "Norge": 1, "Verden": 1, "USA": 1, "Økonomi": 2, "AI": 2}
QUERIES = [
    ("Narvik", 'Narvik (næringsliv OR kommune OR investering OR industri OR Ofotbanen OR E6 OR havn OR forsvar)'),
    ("Nord-Norge", '"Nord-Norge" (næringsliv OR forsvar OR energi OR investering OR politikk)'),
    ("Norge", 'Norge (regjeringen OR Stortinget OR sikkerhet OR næringsliv OR økonomi OR teknologi)'),
    ("Verden", 'verden (krig OR diplomati OR sikkerhet OR økonomi OR teknologi OR klima)'),
    ("USA", 'USA (president OR Kongressen OR Fed OR økonomi OR sikkerhet OR teknologi)'),
    ("Økonomi", 'økonomi (Norges Bank OR renter OR børs OR olje OR krone OR aksjer OR finansmarked)'),
    ("AI", '(OpenAI OR Anthropic OR "Google DeepMind" OR Nvidia OR Microsoft OR Meta OR xAI) (AI OR "artificial intelligence" OR modell OR chip OR regulering OR investering)'),
    ("AI", '"kunstig intelligens" (modell OR regulering OR sikkerhet OR datasenter OR chip OR investering OR OpenAI OR Anthropic OR Nvidia)'),
]
BLOCKED = ["arctic race", "alpin vm", "ol-gren", "ol gren", "folkemøte narvik 2029", "god morgen narvik", "god dag narvik", "været i narvik", "vær i narvik", "fotball", "håndball", "ishockey", "resultater fra"]
IMPORTANT = {"regjering":3,"storting":3,"norges bank":4,"rente":3,"inflasjon":3,"arbeidsplasser":3,"investering":3,"milliard":3,"oppkjøp":2,"forsvar":3,"sikkerhet":3,"krig":3,"fred":2,"sanksjon":2,"børs":3,"aksje":2,"olje":2,"krone":2,"marked":2,"kunstig intelligens":4,"artificial intelligence":4,"openai":4,"anthropic":4,"deepmind":3,"nvidia":3,"xai":3,"ai model":3,"chip":3,"regulering":3,"teknologi":2,"ofotban":4,"e6":3,"havn":3}
WHY = {
    "Narvik":"Dette kan få konkrete følger for Narvik, arbeidsplasser, investeringer eller viktige lokale beslutninger.",
    "Nord-Norge":"Saken kan påvirke rammevilkår, investeringer eller utviklingen i Nord-Norge – og dermed også Narvik.",
    "Norge":"Dette er en nasjonal utvikling som kan påvirke økonomi, politikk, sikkerhet eller hverdagen i Norge.",
    "Verden":"Dette er en internasjonal utvikling med mulig betydning for geopolitikk, økonomi eller markeder.",
    "USA":"Utviklingen i USA kan påvirke global politikk, sikkerhet, teknologi og finansmarkeder.",
    "Økonomi":"Dette kan påvirke renter, markeder, bedrifter, investeringer eller privatøkonomien.",
    "AI":"Dette kan endre konkurransebildet i teknologi, arbeidsliv, investeringer, sikkerhet eller regulering globalt.",
}

def clean_text(value):
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()

def clean_title(title, source=""):
    title = clean_text(title)
    if source: title = re.sub(rf"\s+-\s+{re.escape(source)}\s*$", "", title, flags=re.I)
    title = re.sub(r"^(Narvik|Evenes|Harstad|God morgen,? Narvik|God dag Narvik)\s*[|:]\s*", "", title, flags=re.I)
    title = re.sub(r"\s+\|\s+[^|]{1,35}$", "", title)
    return title.strip(" -–—|")

def is_blocked(title): return any(term in title.lower() for term in BLOCKED)
def google_news_url(query): return "https://news.google.com/rss/search?" + urllib.parse.urlencode({"q":query,"hl":"no","gl":"NO","ceid":"NO:no"})
def fetch_feed(query):
    req = urllib.request.Request(google_news_url(query), headers={"User-Agent":"Mozilla/5.0 AlexBrief/5.0"})
    with urllib.request.urlopen(req, timeout=20) as response: return response.read()
def story_id(title, source): return hashlib.sha1(f"{title.lower()}|{source.lower()}".encode()).hexdigest()[:14]

def parse_items(xml_bytes, category):
    root, now, result = ET.fromstring(xml_bytes), datetime.now(timezone.utc), []
    for item in root.findall("./channel/item"):
        source = clean_text(item.findtext("source")); title = clean_title(item.findtext("title"), source)
        url = clean_text(item.findtext("link")); description = clean_text(item.findtext("description")); pub_raw = clean_text(item.findtext("pubDate"))
        if not title or not url or len(title) < 15 or is_blocked(title): continue
        try: published_dt = parsedate_to_datetime(pub_raw).astimezone(timezone.utc)
        except Exception: continue
        age_hours = (now-published_dt).total_seconds()/3600
        if age_hours > MAX_AGE_HOURS: continue
        if source: description = re.sub(rf"\s*{re.escape(source)}\s*$", "", description, flags=re.I).strip(" -–—|")
        score = max(0, int(10-age_hours/4)) + sum(w for word,w in IMPORTANT.items() if word in f"{title} {description}".lower()) + (3 if category=="AI" else 0)
        result.append({"id":story_id(title,source),"category":category,"published_dt":published_dt,"title":title,"description":description[:900],"url":url,"source":source or "Nyhetskilde","score":score})
    return result

def normalize_title(title): return re.sub(r"[^a-z0-9æøå]+", " ", title.lower()).strip()
def dedupe(items):
    seen,out=set(),[]
    for item in sorted(items,key=lambda x:(x["score"],x["published_dt"]),reverse=True):
        key=" ".join(normalize_title(item["title"]).split()[:9])
        if key in seen: continue
        seen.add(key); out.append(item)
    return out

def select_balanced(items):
    chosen,ids=[],set()
    for category,quota in CATEGORY_QUOTAS.items():
        pool=sorted([x for x in items if x["category"]==category and x["id"] not in ids],key=lambda x:(x["score"],x["published_dt"]),reverse=True)
        for item in pool[:quota]: chosen.append(item); ids.add(item["id"])
    rest=sorted([x for x in items if x["id"] not in ids],key=lambda x:(x["score"],x["published_dt"]),reverse=True)
    chosen.extend(rest[:MAX_STORIES-len(chosen)]); chosen.sort(key=lambda x:x["published_dt"],reverse=True)
    return chosen[:MAX_STORIES]

def fallback_ai(item):
    detail=item["description"] or f"{item['source']} omtaler denne utviklingen: {item['title']}."
    return {"aiSummary":detail[:320].strip(),"keyPoints":[item["title"],f"Kilde: {item['source']}"],"whyItMatters":WHY[item["category"]],"aiGenerated":False}

def extract_response_text(payload):
    if payload.get("output_text"): return payload["output_text"]
    parts=[]
    for output in payload.get("output",[]):
        for content in output.get("content",[]):
            if content.get("type")=="output_text": parts.append(content.get("text", ""))
    return "".join(parts).strip()

def call_openai(item):
    if not OPENAI_API_KEY: raise RuntimeError("OPENAI_API_KEY mangler i GitHub Actions secrets")
    prompt=f'''Du er redaktør for Alex Brief. Oppsummer saken på norsk basert KUN på informasjonen under. Ikke finn på fakta. Svar kun med JSON: {{"aiSummary":"2-4 korte setninger","keyPoints":["2-4 korte punkter"],"whyItMatters":"1-2 konkrete setninger"}}. Hvis kildeteksten er knapp, si det tydelig.\nKategori: {item['category']}\nTittel: {item['title']}\nKilde: {item['source']}\nKildebeskrivelse: {item['description'] or 'Ingen ekstra beskrivelse tilgjengelig.'}'''
    body=json.dumps({"model":OPENAI_MODEL,"input":prompt,"text":{"format":{"type":"json_object"}}}).encode("utf-8")
    req=urllib.request.Request("https://api.openai.com/v1/responses",data=body,headers={"Authorization":f"Bearer {OPENAI_API_KEY}","Content-Type":"application/json"},method="POST")
    try:
        with urllib.request.urlopen(req,timeout=60) as response: payload=json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        detail=exc.read().decode("utf-8",errors="replace")[:1200]
        raise RuntimeError(f"OpenAI HTTP {exc.code}: {detail}") from exc
    text=extract_response_text(payload)
    if not text: raise RuntimeError("OpenAI returnerte ikke output_text")
    data=json.loads(text)
    summary=clean_text(data.get("aiSummary","")); points=[clean_text(x) for x in data.get("keyPoints",[]) if clean_text(x)][:4]; why=clean_text(data.get("whyItMatters",""))
    if not summary or not points: raise RuntimeError("OpenAI-respons manglet oppsummering eller nøkkelpunkter")
    return {"aiSummary":summary,"keyPoints":points,"whyItMatters":why or WHY[item["category"]],"aiGenerated":True}

def load_previous():
    try:
        data=json.loads(OUT.read_text(encoding="utf-8")); return data,{s.get("id"):s for s in data.get("stories",[]) if s.get("id")}
    except Exception: return {},{}

def main():
    all_items,errors=[],[]
    for category,query in QUERIES:
        try: all_items.extend(parse_items(fetch_feed(query),category))
        except Exception as exc: errors.append(f"{category}: {exc}")
    selected=select_balanced(dedupe(all_items))
    if not selected: raise RuntimeError("Ingen relevante saker funnet. "+"; ".join(errors))
    previous_data,previous=load_previous(); stories=[]; ai_errors=[]
    for item in selected:
        old=previous.get(item["id"],{})
        # Gjenbruk bare ekte AI-oppsummeringer. Gamle fallback-saker prøves på nytt automatisk.
        if old.get("aiGenerated") is True and old.get("summary"):
            ai={"aiSummary":old.get("summary"),"keyPoints":old.get("keyPoints") or [],"whyItMatters":old.get("whyItMatters") or WHY[item["category"]],"aiGenerated":True}
        else:
            try: ai=call_openai(item)
            except Exception as exc:
                ai_errors.append(f"{item['id']} {item['title']}: {exc}"); ai=fallback_ai(item)
        published=item["published_dt"].astimezone(OSLO)
        stories.append({"id":item["id"],"category":item["category"],"published":published.strftime("%d.%m. %H:%M"),"publishedISO":published.isoformat(),"title":item["title"],"summary":ai["aiSummary"],"keyPoints":ai["keyPoints"] or [item["title"]],"whyItMatters":ai["whyItMatters"],"aiGenerated":ai["aiGenerated"],"url":item["url"],"source":item["source"]})
    now_oslo=datetime.now(OSLO)
    payload={"updatedAt":now_oslo.strftime("%d.%m.%Y kl. %H:%M"),"updatedISO":now_oslo.isoformat(),"stories":stories}
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Oppdaterte briefen med {len(stories)} kuraterte saker. AI: {sum(1 for s in stories if s['aiGenerated'])}/{len(stories)}")
    for error in errors: print("Feed-advarsel:",error)
    if ai_errors:
        print("\nAI-FEIL:")
        for error in ai_errors: print(error)
        raise RuntimeError(f"AI-oppsummering feilet for {len(ai_errors)} av {len(stories)} saker. Se loggen over.")

if __name__=="__main__": main()
