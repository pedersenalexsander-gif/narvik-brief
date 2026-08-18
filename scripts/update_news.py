#!/usr/bin/env python3
import hashlib, html, json, math, re, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/"data"/"news.json"; IMAGE_DIR=ROOT/"assets"/"news"; IMAGE_DIR.mkdir(parents=True,exist_ok=True)
OSLO=ZoneInfo("Europe/Oslo"); MAX_STORIES=10; MAX_AGE_HOURS=72; MIN_ARTICLE_CHARS=1000; MIN_SCORE=12
CATEGORY_QUOTAS={"Narvik":2,"Nord-Norge":1,"Norge":1,"Verden":1,"USA":1,"Økonomi":2,"AI":2}
RSS_FEEDS=[("Nord-Norge","https://www.nrk.no/nordland/siste.rss"),("Norge","https://www.nrk.no/toppsaker.rss"),("Norge","https://www.nrk.no/norge/toppsaker.rss"),("Norge","https://www.vg.no/rss/feed/?categories=1069"),("Verden","https://www.vg.no/rss/feed/?categories=1070"),("Økonomi","https://e24.no/rss2/"),("Økonomi","https://e24.no/rss2/?seksjon=boers-og-finans"),("Verden","https://feeds.bbci.co.uk/news/world/rss.xml"),("USA","https://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml"),("Økonomi","https://feeds.bbci.co.uk/news/business/rss.xml"),("AI","https://feeds.bbci.co.uk/news/technology/rss.xml")]
GOOGLE_QUERIES=[("Narvik",'Narvik (næringsliv OR kommune OR industri OR Ofotbanen OR E6 OR havn OR forsvar)'),("Nord-Norge",'"Nord-Norge" (næringsliv OR forsvar OR energi OR investering OR politikk)'),("AI",'(OpenAI OR Anthropic OR DeepMind OR Nvidia OR xAI) (AI OR artificial intelligence OR model OR chip OR regulation OR investment)')]
BLOCKED_TERMS=["arctic race","alpin vm","ol-gren","ol gren","folkemøte narvik 2029","god morgen narvik","god dag narvik","weather","været i narvik","vær i narvik","fotball","håndball","ishockey","results","resultater fra","quiz","horoscope","wetherspoon","school uniform","uniform bank","tohodet slange","to-headed snake","utstilling","konsertplakat","kjendis","celebrity","restaurant review","festival","pubs","music from phones"]
PAYWALL_TERMS=["subscribe to continue","subscription required","subscriber only","members only","logg inn for å lese","kjøp abonnement","bli abonnent","kun for abonnenter","denne saken er for abonnenter","premium article","unlock this article"]
IMPORTANT={"narvik":7,"ofotban":6,"e6":4,"havn":4,"forsvar":4,"regjering":4,"storting":4,"norges bank":5,"rente":4,"inflasjon":4,"arbeidsplasser":4,"investering":4,"milliard":4,"sikkerhet":4,"krig":4,"børs":4,"aksje":3,"olje":3,"marked":3,"openai":5,"anthropic":5,"deepmind":4,"nvidia":4,"artificial intelligence":5,"kunstig intelligens":5,"chip":4,"regulation":4,"regulering":4,"trump":4,"ukraine":4,"ukraina":4,"nato":4,"kina":4,"china":4}
WHY={"Narvik":"Kan få konkrete følger for Narvik, arbeidsplasser, investeringer eller viktige lokale beslutninger.","Nord-Norge":"Kan påvirke rammevilkår, investeringer eller utviklingen i Nord-Norge – og dermed også Narvik.","Norge":"En nasjonal utvikling som kan påvirke økonomi, politikk, sikkerhet eller hverdagen i Norge.","Verden":"En internasjonal utvikling med mulig betydning for geopolitikk, økonomi eller markeder.","USA":"Utviklingen i USA kan påvirke global politikk, sikkerhet, teknologi og finansmarkeder.","Økonomi":"Kan påvirke renter, markeder, bedrifter, investeringer eller privatøkonomien.","AI":"Kan endre konkurransebildet i teknologi, arbeidsliv, investeringer, sikkerhet eller regulering globalt."}
STOPWORDS=set("og i på til for av en et ei som det den de er var blir ble har hadde med om fra ved etter før også men eller ikke sin sine sitt seg dette disse der her kan vil skal må mot over under mellom ut inn når hvor hva hvem hvilken hvilke fordi derfor dersom hvis samt than the and a an of to in on for from with by as is are was were be been being it its this that these those or but not into over under after before about which who what when where how can could will would should may might".split())

class ArticleParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.in_article=0; self.in_p=0; self.current=[]; self.article_paragraphs=[]; self.all_paragraphs=[]; self.image=""; self.first_image=""; self.canonical=""; self.title=""
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=="article": self.in_article+=1
        if tag=="p": self.in_p+=1; self.current=[]
        if tag=="meta":
            prop=(a.get("property") or a.get("name") or "").lower(); content=a.get("content","")
            if prop in ("og:image","twitter:image","twitter:image:src") and not self.image:self.image=content
            if prop in ("og:title","twitter:title") and not self.title:self.title=content
        if tag=="img" and not self.first_image:
            src=a.get("src") or a.get("data-src") or a.get("data-lazy-src") or ""
            if src and not any(x in src.lower() for x in ("logo","icon","avatar","pixel","tracking")):self.first_image=src
        if tag=="link" and "canonical" in (a.get("rel") or "").lower():self.canonical=a.get("href","")
    def handle_endtag(self,tag):
        if tag=="p" and self.in_p:
            t=" ".join("".join(self.current).split())
            if len(t)>=45:
                self.all_paragraphs.append(t)
                if self.in_article:self.article_paragraphs.append(t)
            self.in_p=max(0,self.in_p-1); self.current=[]
        if tag=="article" and self.in_article:self.in_article-=1
    def handle_data(self,data):
        if self.in_p:self.current.append(data)

def clean_text(v):return re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",html.unescape(v or ""))).strip()
def is_blocked(t):return any(x in t.lower() for x in BLOCKED_TERMS)
def normalize_title(t):return re.sub(r"[^a-z0-9æøå]+"," ",t.lower()).strip()
def story_id(t,s):return hashlib.sha1(f"{t.lower()}|{s.lower()}".encode()).hexdigest()[:14]
def fetch_bytes(url,timeout=25,accept="*/*"):
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; AlexBrief/10.0)","Accept-Language":"nb-NO,nb;q=0.9,en;q=0.8","Accept":accept})
    with urllib.request.urlopen(req,timeout=timeout) as r:return r.read(),r.geturl(),r.headers.get("Content-Type","")
def parse_date(v):
    if not v:return datetime.now(timezone.utc)
    try:return parsedate_to_datetime(v).astimezone(timezone.utc)
    except Exception:pass
    for f in ("%Y-%m-%dT%H:%M:%SZ","%Y-%m-%dT%H:%M:%S%z","%Y-%m-%dT%H:%M:%S.%f%z"):
        try:
            d=datetime.strptime(v,f); return d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d.astimezone(timezone.utc)
        except Exception:pass
    return datetime.now(timezone.utc)
def google_news_url(q):return "https://news.google.com/rss/search?"+urllib.parse.urlencode({"q":q,"hl":"no","gl":"NO","ceid":"NO:no"})
def parse_feed(category,url):
    raw,_,_=fetch_bytes(url); root=ET.fromstring(raw); out=[]
    for item in root.findall(".//item"):
        title=clean_text(item.findtext("title")); link=clean_text(item.findtext("link")); desc=clean_text(item.findtext("description")); pub=item.findtext("pubDate") or item.findtext("date") or ""; se=item.find("source"); source=clean_text(se.text if se is not None else "") or (urllib.parse.urlparse(link).netloc.replace("www.","") if link else "Nyhetskilde"); image=""
        for child in item:
            tag=child.tag.lower(); u=child.attrib.get("url","")
            if tag.endswith("enclosure") and (child.attrib.get("type","").startswith("image") or u.lower().endswith((".jpg",".jpeg",".png",".webp"))):image=u
            if tag.endswith("content") and "medium" in tag and u:image=u
        if title and link:out.append({"category":category,"title":title,"url":link,"description":desc,"source":source,"published_dt":parse_date(pub),"feed_image":image})
    return out
def resolve_news_redirect(url):
    if "news.google.com" not in urllib.parse.urlparse(url).netloc.lower():return url
    try:
        raw,final,ct=fetch_bytes(url,15)
        if "news.google.com" not in urllib.parse.urlparse(final).netloc.lower():return final
        for c in re.findall(r'href=["\'](https?://[^"\']+)["\']',raw.decode("utf-8",errors="replace")):
            h=urllib.parse.urlparse(c).netloc.lower()
            if h and "google." not in h and "gstatic." not in h:return html.unescape(c)
    except Exception:pass
    return url
def fetch_article(url):
    url=resolve_news_redirect(url); raw,final,ct=fetch_bytes(url,20,"text/html,*/*")
    if "text/html" not in ct.lower():return None
    src=raw.decode("utf-8",errors="replace"); low=src.lower()
    if any(x in low for x in PAYWALL_TERMS):return None
    p=ArticleParser()
    try:p.feed(src)
    except Exception:return None
    paras=p.article_paragraphs if sum(map(len,p.article_paragraphs))>=MIN_ARTICLE_CHARS else p.all_paragraphs; cleaned=[]; seen=set()
    for x in paras:
        if any(n in x.lower() for n in ("cookie","newsletter","sign up","meld deg på","personvern","privacy policy","les også","related article","advertisement")):continue
        k=x[:140]
        if k in seen:continue
        seen.add(k); cleaned.append(x)
    text="\n\n".join(cleaned)
    if len(text)<MIN_ARTICLE_CHARS:return None
    raw_image=p.image or p.first_image; image=urllib.parse.urljoin(final,raw_image) if raw_image else ""; canonical=urllib.parse.urljoin(final,p.canonical) if p.canonical else final
    return {"url":canonical,"text":text[:16000],"image":image,"page_title":clean_text(p.title)}
def discover():
    now=datetime.now(timezone.utc); items=[]
    for category,url in list(RSS_FEEDS)+[(c,google_news_url(q)) for c,q in GOOGLE_QUERIES]:
        try:feed=parse_feed(category,url)
        except Exception as e:print(f"Feed-feil {category}: {e}");continue
        for item in feed:
            title=item["title"]; combined=f"{title} {item.get('description','')}"
            if len(title)<15 or is_blocked(combined):continue
            age=(now-item["published_dt"]).total_seconds()/3600
            if age>MAX_AGE_HOURS:continue
            item["score"]=max(0,int(14-age/5))+sum(w for k,w in IMPORTANT.items() if k in combined.lower())+(4 if category in ("Narvik","AI") else 0)
            if item["score"]<MIN_SCORE:continue
            item["id"]=story_id(title,item["source"]);items.append(item)
    return items
def dedupe(items):
    seen=[];out=[]
    for i in sorted(items,key=lambda x:(x["score"],x["published_dt"]),reverse=True):
        ws=set(normalize_title(i["title"]).split())
        if any(len(ws&o)/max(1,min(len(ws),len(o)))>.72 for o in seen):continue
        seen.append(ws);out.append(i)
    return out
def split_sentences(t):return[s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-ZÆØÅ0-9])",re.sub(r"\s+"," ",t).strip()) if 55<=len(s.strip())<=420]
def words(t):return[w for w in re.findall(r"[a-zA-ZæøåÆØÅ0-9-]{3,}",t.lower()) if w not in STOPWORDS and not w.isdigit()]
def summarize_locally(title,text,category):
    ss=split_sentences(text);freq=Counter(words(text))
    if len(ss)<4 or not freq:return None
    mf=max(freq.values());weights={w:math.log1p(c)/math.log1p(mf) for w,c in freq.items()};tt=set(words(title));scored=[]
    for idx,s in enumerate(ss[:80]):
        sw=words(s)
        if sw:scored.append((sum(weights.get(w,0) for w in sw)/math.sqrt(len(sw))+sum(1.7 for w in set(sw)&tt)+max(0,2.2-idx*.06)+(0.8 if re.search(r"\b\d+[\d.,%]*\b",s) else 0),idx,s))
    if len(scored)<3:return None
    top=sorted(scored,reverse=True)[:6];summary=" ".join(s for _,_,s in sorted(top[:3],key=lambda x:x[1]));points=[]
    for _,_,s in top:
        if any(len(set(words(s))&set(words(p)))/max(1,min(len(set(words(s))),len(set(words(p)))))>.7 for p in points):continue
        points.append(s)
        if len(points)==4:break
    return(summary,points,WHY[category]) if len(summary)>=170 and len(points)>=2 else None
def looks_english(t):
    low=f" {t.lower()} ";hits=sum(low.count(f" {w} ") for w in ("the","and","with","from","said","has","have","will","after","for","this","that","new","company","market","people"));return hits>=2
def translate_no(t):
    if not t or not looks_english(t):return t
    try:
        q=urllib.parse.urlencode({"client":"gtx","sl":"auto","tl":"no","dt":"t","q":t[:3500]});raw,_,_=fetch_bytes("https://translate.googleapis.com/translate_a/single?"+q,20);data=json.loads(raw.decode());result="".join(x[0] for x in data[0] if x and x[0]);return clean_text(result) or t
    except Exception as e:print(f"Oversettelse feilet: {e}");return t
def ext_from_ct(ct,url):
    c=ct.lower()
    if "png" in c:return ".png"
    if "webp" in c:return ".webp"
    if "jpeg" in c or "jpg" in c:return ".jpg"
    ext=Path(urllib.parse.urlparse(url).path).suffix.lower();return ext if ext in (".jpg",".jpeg",".png",".webp") else ".jpg"
def localize_image(url,sid):
    if not url:return ""
    for ext in (".jpg",".jpeg",".png",".webp"):
        p=IMAGE_DIR/f"{sid}{ext}"
        if p.exists():return f"assets/news/{p.name}"
    try:
        raw,_,ct=fetch_bytes(url,20,"image/avif,image/webp,image/apng,image/*,*/*;q=0.8")
        if not ct.lower().startswith("image/") or len(raw)<5000:return ""
        ext=ext_from_ct(ct,url);p=IMAGE_DIR/f"{sid}{ext}";p.write_bytes(raw);return f"assets/news/{p.name}"
    except Exception as e:print(f"Bilde feilet {sid}: {e}");return ""
def translate_story(story):
    story=dict(story)
    story["title"]=translate_no(story.get("title",""));story["summary"]=translate_no(story.get("summary",""));story["keyPoints"]=[translate_no(x) for x in story.get("keyPoints",[])]
    if looks_english(story.get("title","")+" "+story.get("summary","")):return None
    return story
def build_story(item):
    try:page=fetch_article(item["url"])
    except Exception as e:print(f"Dropper utilgjengelig artikkel: {item['title']} ({e})");return None
    if not page:return None
    title=page["page_title"] if page.get("page_title") and len(page["page_title"])>15 else item["title"]
    if is_blocked(title+" "+page["text"][:1200]):return None
    generated=summarize_locally(title,page["text"],item["category"])
    if not generated:return None
    summary,points,why=generated;published=item["published_dt"].astimezone(OSLO);image=page["image"] or item.get("feed_image","");local=localize_image(image,item["id"])
    if not local:return None
    story={"id":item["id"],"category":item["category"],"published":published.strftime("%d.%m. %H:%M"),"publishedISO":published.isoformat(),"title":title,"summary":summary,"keyPoints":points,"whyItMatters":why,"summaryMethod":"local-extractive","url":page["url"],"source":item["source"],"image":image,"localImage":local,"score":item["score"]}
    return translate_story(story)
def select_balanced(stories):
    chosen=[];ids=set()
    for c,q in CATEGORY_QUOTAS.items():
        pool=sorted([s for s in stories if s.get("category")==c and s.get("id") not in ids],key=lambda s:(s.get("score",0),s.get("publishedISO","")),reverse=True)
        for s in pool[:q]:chosen.append(s);ids.add(s.get("id"))
    rest=sorted([s for s in stories if s.get("id") not in ids],key=lambda s:(s.get("score",0),s.get("publishedISO","")),reverse=True);chosen.extend(rest[:MAX_STORIES-len(chosen)]);return chosen[:MAX_STORIES]
def main():
    built=[]
    for item in dedupe(discover()):
        s=build_story(item)
        if s:built.append(s)
        if len(built)>=28:break
    selected=select_balanced(built)
    if not selected:
        print("Ingen saker møtte kvalitetskravene denne runden. Beholder forrige brief.");return
    now=datetime.now(OSLO);payload={"updatedAt":now.strftime("%d.%m.%Y kl. %H:%M"),"updatedISO":now.isoformat(),"qualityMode":"strict-relevance-norwegian-local-images","stories":selected};OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");print(f"Publiserte {len(selected)} strengt filtrerte saker.")
if __name__=="__main__":main()
