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
OSLO = ZoneInfo("Europe/Oslo")
MAX_STORIES = 10
MAX_AGE_HOURS = 72
MIN_ARTICLE_CHARS = 1000

CATEGORY_QUOTAS = {"Narvik": 2, "Nord-Norge": 1, "Norge": 1, "Verden": 1, "USA": 1, "Økonomi": 2, "AI": 2}
RSS_FEEDS = [
    ("Nord-Norge", "https://www.nrk.no/nordland/siste.rss"),
    ("Norge", "https://www.nrk.no/toppsaker.rss"),
    ("Norge", "https://www.nrk.no/norge/toppsaker.rss"),
    ("Norge", "https://www.vg.no/rss/feed/?categories=1069"),
    ("Verden", "https://www.vg.no/rss/feed/?categories=1070"),
    ("Økonomi", "https://e24.no/rss2/"),
    ("Økonomi", "https://e24.no/rss2/?seksjon=boers-og-finans"),
    ("Verden", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("USA", "https://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml"),
    ("Økonomi", "https://feeds.bbci.co.uk/news/business/rss.xml"),
    ("AI", "https://feeds.bbci.co.uk/news/technology/rss.xml"),
]
GOOGLE_QUERIES = [
    ("Narvik", 'Narvik (næringsliv OR kommune OR industri OR Ofotbanen OR E6 OR havn OR forsvar)'),
    ("Nord-Norge", '"Nord-Norge" (næringsliv OR forsvar OR energi OR investering OR politikk)'),
    ("AI", '(OpenAI OR Anthropic OR DeepMind OR Nvidia OR xAI) (AI OR "artificial intelligence" OR model OR chip OR regulation OR investment)'),
]
BLOCKED_TERMS = ["arctic race","alpin vm","ol-gren","ol gren","folkemøte narvik 2029","god morgen narvik","god dag narvik","weather","været i narvik","vær i narvik","fotball","håndball","ishockey","results","resultater fra","quiz","horoscope"]
PAYWALL_TERMS = ["subscribe to continue","subscription required","subscriber only","members only","logg inn for å lese","kjøp abonnement","bli abonnent","kun for abonnenter","denne saken er for abonnenter","premium article","unlock this article"]
IMPORTANT = {"narvik":5,"ofotban":5,"e6":3,"havn":3,"forsvar":3,"regjering":3,"storting":3,"norges bank":4,"rente":3,"inflasjon":3,"arbeidsplasser":3,"investering":3,"milliard":3,"sikkerhet":3,"krig":3,"børs":3,"aksje":2,"olje":2,"marked":2,"openai":4,"anthropic":4,"deepmind":3,"nvidia":3,"artificial intelligence":4,"kunstig intelligens":4,"chip":3,"regulation":3}
WHY = {"Narvik":"Kan få konkrete følger for Narvik, arbeidsplasser, investeringer eller viktige lokale beslutninger.","Nord-Norge":"Kan påvirke rammevilkår, investeringer eller utviklingen i Nord-Norge – og dermed også Narvik.","Norge":"En nasjonal utvikling som kan påvirke økonomi, politikk, sikkerhet eller hverdagen i Norge.","Verden":"En internasjonal utvikling med mulig betydning for geopolitikk, økonomi eller markeder.","USA":"Utviklingen i USA kan påvirke global politikk, sikkerhet, teknologi og finansmarkeder.","Økonomi":"Kan påvirke renter, markeder, bedrifter, investeringer eller privatøkonomien.","AI":"Kan endre konkurransebildet i teknologi, arbeidsliv, investeringer, sikkerhet eller regulering globalt."}
STOPWORDS = set("og i på til for av en et ei som det den de er var blir ble har hadde med om fra ved etter før også men eller ikke sin sine sitt seg dette disse der her kan vil skal må mot over under mellom ut inn når hvor hva hvem hvilken hvilke fordi derfor dersom hvis samt than the and a an of to in on for from with by as is are was were be been being it its this that these those or but not into over under after before about which who what when where how can could will would should may might".split())

class ArticleParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.in_article=0; self.in_p=0; self.current=[]; self.article_paragraphs=[]; self.all_paragraphs=[]; self.image=""; self.canonical=""; self.title=""
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if tag=="article": self.in_article+=1
        if tag=="p": self.in_p+=1; self.current=[]
        if tag=="meta":
            prop=(attrs.get("property") or attrs.get("name") or "").lower(); content=attrs.get("content","")
            if prop in ("og:image","twitter:image","twitter:image:src") and not self.image: self.image=content
            if prop in ("og:title","twitter:title") and not self.title: self.title=content
        if tag=="link" and "canonical" in (attrs.get("rel") or "").lower(): self.canonical=attrs.get("href","")
    def handle_endtag(self, tag):
        if tag=="p" and self.in_p:
            text=" ".join("".join(self.current).split())
            if len(text)>=45:
                self.all_paragraphs.append(text)
                if self.in_article: self.article_paragraphs.append(text)
            self.in_p=max(0,self.in_p-1); self.current=[]
        if tag=="article" and self.in_article: self.in_article-=1
    def handle_data(self,data):
        if self.in_p: self.current.append(data)

def clean_text(value):
    value=html.unescape(value or ""); value=re.sub(r"<[^>]+>"," ",value); return re.sub(r"\s+"," ",value).strip()
def is_blocked(title): return any(x in title.lower() for x in BLOCKED_TERMS)
def normalize_title(title): return re.sub(r"[^a-z0-9æøå]+"," ",title.lower()).strip()
def story_id(title,source): return hashlib.sha1(f"{title.lower()}|{source.lower()}".encode()).hexdigest()[:14]
def fetch_bytes(url,timeout=25):
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; AlexBrief/8.0)","Accept-Language":"nb-NO,nb;q=0.9,en;q=0.8"})
    with urllib.request.urlopen(req,timeout=timeout) as response: return response.read(),response.geturl(),response.headers.get("Content-Type","")
def parse_date(value):
    if not value: return datetime.now(timezone.utc)
    try: return parsedate_to_datetime(value).astimezone(timezone.utc)
    except Exception: pass
    for fmt in ("%Y-%m-%dT%H:%M:%SZ","%Y-%m-%dT%H:%M:%S%z","%Y-%m-%dT%H:%M:%S.%f%z"):
        try:
            dt=datetime.strptime(value,fmt); return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
        except Exception: pass
    return datetime.now(timezone.utc)
def google_news_url(query): return "https://news.google.com/rss/search?"+urllib.parse.urlencode({"q":query,"hl":"no","gl":"NO","ceid":"NO:no"})
def parse_feed(category,url):
    raw,_,_=fetch_bytes(url); root=ET.fromstring(raw); out=[]
    for item in root.findall(".//item"):
        title=clean_text(item.findtext("title")); link=clean_text(item.findtext("link")); desc=clean_text(item.findtext("description")); pub=item.findtext("pubDate") or item.findtext("date") or ""; source_el=item.find("source"); source=clean_text(source_el.text if source_el is not None else "")
        if not source: source=urllib.parse.urlparse(link).netloc.replace("www.","") if link else "Nyhetskilde"
        image=""
        for child in item:
            tag=child.tag.lower()
            if tag.endswith("enclosure") and (child.attrib.get("type","").startswith("image") or child.attrib.get("url","").lower().endswith((".jpg",".jpeg",".png",".webp"))): image=child.attrib.get("url","")
            if tag.endswith("content") and "medium" in tag and child.attrib.get("url"): image=child.attrib.get("url","")
        if title and link: out.append({"category":category,"title":title,"url":link,"description":desc,"source":source,"published_dt":parse_date(pub),"feed_image":image})
    ns={"a":"http://www.w3.org/2005/Atom"}
    for entry in root.findall(".//a:entry",ns):
        title=clean_text(entry.findtext("a:title",default="",namespaces=ns)); link=""
        for link_el in entry.findall("a:link",ns):
            if link_el.attrib.get("rel","alternate")=="alternate": link=link_el.attrib.get("href",""); break
        desc=clean_text(entry.findtext("a:summary",default="",namespaces=ns) or entry.findtext("a:content",default="",namespaces=ns)); pub=entry.findtext("a:published",default="",namespaces=ns) or entry.findtext("a:updated",default="",namespaces=ns); source=urllib.parse.urlparse(link).netloc.replace("www.","") if link else "Nyhetskilde"
        if title and link: out.append({"category":category,"title":title,"url":link,"description":desc,"source":source,"published_dt":parse_date(pub),"feed_image":""})
    return out
def resolve_news_redirect(url):
    host=urllib.parse.urlparse(url).netloc.lower()
    if "news.google.com" not in host: return url
    try:
        raw,final_url,content_type=fetch_bytes(url,timeout=15)
        if "news.google.com" not in urllib.parse.urlparse(final_url).netloc.lower(): return final_url
        if "text/html" in content_type.lower():
            text=raw.decode("utf-8",errors="replace"); links=re.findall(r'href=["\'](https?://[^"\']+)["\']',text)
            for candidate in links:
                h=urllib.parse.urlparse(candidate).netloc.lower()
                if h and "google." not in h and "gstatic." not in h: return html.unescape(candidate)
    except Exception: pass
    return url
def fetch_article(url):
    url=resolve_news_redirect(url); raw,final_url,content_type=fetch_bytes(url,timeout=20)
    if "text/html" not in content_type.lower(): return None
    source_html=raw.decode("utf-8",errors="replace"); low=source_html.lower()
    if any(term in low for term in PAYWALL_TERMS): return None
    parser=ArticleParser()
    try: parser.feed(source_html)
    except Exception: return None
    paragraphs=parser.article_paragraphs if sum(map(len,parser.article_paragraphs))>=MIN_ARTICLE_CHARS else parser.all_paragraphs; cleaned=[]; seen=set(); noise=["cookie","newsletter","sign up","meld deg på","personvern","privacy policy","les også","related article","advertisement"]
    for p in paragraphs:
        pl=p.lower()
        if any(x in pl for x in noise): continue
        key=p[:140]
        if key in seen: continue
        seen.add(key); cleaned.append(p)
    article_text="\n\n".join(cleaned)
    if len(article_text)<MIN_ARTICLE_CHARS: return None
    image=urllib.parse.urljoin(final_url,parser.image) if parser.image else ""; canonical=urllib.parse.urljoin(final_url,parser.canonical) if parser.canonical else final_url
    return {"url":canonical,"text":article_text[:16000],"image":image,"page_title":clean_text(parser.title)}
def discover():
    now=datetime.now(timezone.utc); items=[]; sources=list(RSS_FEEDS)+[(cat,google_news_url(q)) for cat,q in GOOGLE_QUERIES]
    for category,url in sources:
        try: feed_items=parse_feed(category,url)
        except Exception as exc: print(f"Feed-feil {category} {url}: {exc}"); continue
        for item in feed_items:
            title=item["title"]
            if len(title)<15 or is_blocked(title): continue
            age=(now-item["published_dt"]).total_seconds()/3600
            if age>MAX_AGE_HOURS: continue
            score=max(0,int(14-age/5))+sum(w for k,w in IMPORTANT.items() if k in f"{title} {item.get('description','')}".lower())+(3 if category=="AI" else 0); item["score"]=score; item["id"]=story_id(title,item["source"]); items.append(item)
    return items
def dedupe(items):
    seen=[]; out=[]
    for item in sorted(items,key=lambda x:(x["score"],x["published_dt"]),reverse=True):
        ws=set(normalize_title(item["title"]).split())
        if any(len(ws&old)/max(1,min(len(ws),len(old)))>.72 for old in seen): continue
        seen.append(ws); out.append(item)
    return out
def split_sentences(text):
    text=re.sub(r"\s+"," ",text).strip(); return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-ZÆØÅ0-9])",text) if 55<=len(s.strip())<=420]
def words(text): return [w for w in re.findall(r"[a-zA-ZæøåÆØÅ0-9-]{3,}",text.lower()) if w not in STOPWORDS and not w.isdigit()]
def summarize_locally(title,article_text,category):
    sentences=split_sentences(article_text)
    if len(sentences)<4: return None
    freq=Counter(words(article_text))
    if not freq: return None
    maxfreq=max(freq.values()); weights={w:math.log1p(c)/math.log1p(maxfreq) for w,c in freq.items()}; title_terms=set(words(title)); scored=[]
    for idx,s in enumerate(sentences[:80]):
        sw=words(s)
        if not sw: continue
        score=sum(weights.get(w,0) for w in sw)/math.sqrt(len(sw))+sum(1.7 for w in set(sw)&title_terms)+max(0,2.2-idx*.06)+(0.8 if re.search(r"\b\d+[\d.,%]*\b",s) else 0); scored.append((score,idx,s))
    if len(scored)<3: return None
    top=sorted(scored,reverse=True)[:6]; summary=" ".join(s for _,_,s in sorted(top[:3],key=lambda x:x[1])); points=[]
    for _,_,s in top:
        if any(len(set(words(s))&set(words(p)))/max(1,min(len(set(words(s))),len(set(words(p)))))>.7 for p in points): continue
        points.append(s)
        if len(points)==4: break
    if len(summary)<170 or len(points)<2: return None
    return summary,points,WHY[category]
def load_previous():
    try: return json.loads(OUT.read_text(encoding="utf-8"))
    except Exception: return {"stories":[]}
def build_story(item,previous_by_id):
    old=previous_by_id.get(item["id"])
    if old and old.get("summary") and old.get("summaryMethod")=="local-extractive": return old
    try: page=fetch_article(item["url"])
    except Exception as exc: print(f"Dropper utilgjengelig artikkel: {item['title']} ({exc})"); return None
    if not page: print(f"Dropper sak uten nok lesbar artikkeltekst: {item['title']}"); return None
    title=page["page_title"] if page.get("page_title") and len(page["page_title"])>15 else item["title"]; generated=summarize_locally(title,page["text"],item["category"])
    if not generated: print(f"Dropper sak som ikke kan oppsummeres robust: {title}"); return None
    summary,points,why=generated; published=item["published_dt"].astimezone(OSLO)
    return {"id":item["id"],"category":item["category"],"published":published.strftime("%d.%m. %H:%M"),"publishedISO":published.isoformat(),"title":title,"summary":summary,"keyPoints":points,"whyItMatters":why,"summaryMethod":"local-extractive","url":page["url"],"source":item["source"],"image":page["image"] or item.get("feed_image","")}
def select_balanced(stories):
    chosen=[]; ids=set()
    for category,quota in CATEGORY_QUOTAS.items():
        pool=[s for s in stories if s.get("category")==category and s.get("id") not in ids]; pool.sort(key=lambda s:s.get("publishedISO",""),reverse=True)
        for s in pool[:quota]: chosen.append(s); ids.add(s.get("id"))
    rest=[s for s in stories if s.get("id") not in ids]; rest.sort(key=lambda s:s.get("publishedISO",""),reverse=True); chosen.extend(rest[:MAX_STORIES-len(chosen)]); chosen.sort(key=lambda s:s.get("publishedISO",""),reverse=True); return chosen[:MAX_STORIES]
def main():
    previous=load_previous(); previous_by_id={s.get("id"):s for s in previous.get("stories",[]) if s.get("id")}; candidates=dedupe(discover()); built=[]
    for item in candidates:
        story=build_story(item,previous_by_id)
        if story: built.append(story)
        if len(built)>=24: break
    cutoff=datetime.now(timezone.utc)-timedelta(hours=MAX_AGE_HOURS)
    for old in previous.get("stories",[]):
        if old.get("id") in {s.get("id") for s in built}: continue
        try: published=datetime.fromisoformat(old.get("publishedISO","")).astimezone(timezone.utc)
        except Exception: continue
        if published>=cutoff and old.get("summaryMethod")=="local-extractive": built.append(old)
    selected=select_balanced(built)
    if not selected: print("Fant ingen nye kvalitetssaker. Beholder forrige brief uten å feile."); return
    now_oslo=datetime.now(OSLO); payload={"updatedAt":now_oslo.strftime("%d.%m.%Y kl. %H:%M"),"updatedISO":now_oslo.isoformat(),"qualityMode":"multi-rss-full-article-free","stories":selected}; OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); print(f"Publiserte {len(selected)} kvalitetssaker fra flere gratis kilder.")
if __name__=="__main__": main()
