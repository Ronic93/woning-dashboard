#!/usr/bin/env python3
"""Ververst aanbod uit openbare zoekpagina's (zonder login) -> data/listings.json ('nieuw').
Alleen lezen; neemt NOOIT contact op met verhuurders. Pararius via headless Chrome
(curl krijgt 403), ikwilhuren.nu via curl. Funda/Huurwoningen blokkeren of zijn JS-only."""
import json,re,html,subprocess,datetime,os,sys,urllib.request
from zoneinfo import ZoneInfo
TZ=ZoneInfo('Europe/Amsterdam')
D=os.path.dirname(os.path.abspath(__file__)); F=os.path.join(D,'data','listings.json')
MAX=1100
STEDEN=["rotterdam","den-haag","rijswijk","voorburg","leidschendam","delft","schiedam","vlaardingen","zoetermeer","leiden",
 "dordrecht","capelle-aan-den-ijssel","barendrecht","gouda","alphen-aan-den-rijn","utrecht","nieuwegein","houten",
 "zeist","amersfoort","haarlem","amstelveen","hoofddorp","sliedrecht","spijkenisse"]
REGIO={**{s:"Utrecht" for s in ["utrecht","nieuwegein","houten","zeist","amersfoort"]},
       **{s:"Noord-Holland (zuid)" for s in ["haarlem","amstelveen","hoofddorp"]}}
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128 Safari/537.36"
clean=lambda x: html.unescape(re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',x))).strip()
def num(s):
    m=re.search(r'€\s*([\d.]+)(?:,(\d+))?',s or ''); return float(m.group(1).replace('.','')+'.'+(m.group(2) or '0')) if m else None
def chrome(url):
    r=subprocess.run(["google-chrome","--headless=new","--no-sandbox","--disable-gpu","--user-agent="+UA,"--dump-dom",url],
                     capture_output=True,text=True,timeout=60); return r.stdout
def pararius(stad):
    h=chrome(f"https://www.pararius.nl/huurwoningen/{stad}/0-{MAX}"); out=[]
    for s in re.split(r'<section\s+class="listing-search-item ',h)[1:]:
        s=s.split('</section>')[0]; g=lambda p:(clean(m.group(1)) if (m:=re.search(p,s,re.S)) else '')
        href=re.search(r'href="(/[a-z-]+-te-huur/[^"]+)"',s)
        if not href: continue
        price=g(r'listing-search-item__price-main">(.*?)</span>') or g(r'listing-search-item__price">(.*?)</div>')
        out.append(dict(url='https://www.pararius.nl'+href.group(1),titel=g(r'aria-label="([^"]*)"'),
          sub=g(r'listing-search-item__sub-title[^"]*">(.*?)</div>'),huur=num(price),
          m2=g(r'surface-area">.*?</span>(.*?)</li>'),interieur=g(r'interior">.*?</span>(.*?)</li>'),
          plaats=stad.replace('-',' ').title(),regio=REGIO.get(stad,"Zuid-Holland"),bron="Pararius"))
    return out
def ikwilhuren(pages=4):
    out=[]
    for p in range(1,pages+1):
        req=urllib.request.Request(f"https://ikwilhuren.nu/aanbod/?page={p}",headers={"User-Agent":UA})
        h=urllib.request.urlopen(req,timeout=30).read().decode('utf8','ignore')
        for c in h.split('card-woning shadow-sm')[1:]:
            c=c[:4000]; u=re.search(r'href="(/object/[^"]+)"',c)
            if not u: continue
            plaats=u.group(1).split('/')[2].split('-')[0]
            if plaats not in [s.split('-')[0] for s in STEDEN]: continue
            out.append(dict(url='https://ikwilhuren.nu'+u.group(1),titel=clean(re.search(r'stretched-link"[^>]*>(.*?)</a>',c,re.S).group(1)),
              sub=clean(re.search(r'</a>\s*</span>\s*<span>(.*?)</span>',c,re.S).group(1)) if re.search(r'</a>\s*</span>\s*<span>(.*?)</span>',c,re.S) else '',
              huur=num(c),m2=(re.search(r'(\d+) m<sup>',c) or [None,''])[1]+' m²',interieur='',plaats=plaats.title(),
              regio=REGIO.get(plaats,"Zuid-Holland"),bron="ikwilhuren.nu"))
    return out
def git(*a,check=True): return subprocess.run(["git",*a],cwd=D,capture_output=True,text=True,check=check)
def merge(data,fresh,now):
    added=0; known={l['url'] for l in data['listings']}; old={l['url']:l for l in data.get('nieuw',[])}
    for l in fresh:
        if not l['huur'] or l['huur']>MAX or l['url'] in known and l['url'] not in old: continue
        if any(w in (l['titel']+l['sub']).lower() for w in ['kamer ','studio']) and 'appartement' not in l['titel'].lower(): continue
        if l['url'] not in old: l['gevonden']=now; old[l['url']]=l; added+=1
        else: old[l['url']].update({k:v for k,v in l.items() if k not in('gevonden','rit','geo','kosten')}); old[l['url']]['gezien']=now
    data['nieuw']=sorted(old.values(),key=lambda x:x.get('gevonden',''),reverse=True)[:150]
    return added
def main():
    push='--push' in sys.argv; args=[a for a in sys.argv[1:] if not a.startswith('--')]
    if push: git("pull","--rebase","--autostash","-q")
    fresh=[];log=[]
    for s in (args or STEDEN):
        try: r=pararius(s); fresh+=r; log.append(f"Pararius {s}: {len(r)}")
        except Exception as e: log.append(f"Pararius {s}: fout {e}")
    try: r=ikwilhuren(); fresh+=r; log.append(f"ikwilhuren: {len(r)} in regio")
    except Exception as e: log.append(f"ikwilhuren: fout {e}")
    import enrich
    for attempt in range(3):
        data=json.load(open(F)); now=datetime.datetime.now(TZ).isoformat(timespec='minutes')
        added=merge(data,fresh,now); elog=list(log)
        data['bestemming']=enrich.verrijk(data['listings']+data['nieuw'],elog)
        data['refresh']={"tijd":now,"toegevoegd":added,"log":elog,"door":"box" if push else os.environ.get("GITHUB_ACTIONS") and "github" or "lokaal"}
        data['bijgewerkt']=now
        json.dump(data,open(F+'.tmp','w'),ensure_ascii=False,indent=1); os.replace(F+'.tmp',F)
        print(f"{now}: {added} nieuw toegevoegd"); print("\n".join(elog))
        if not push: return
        git("add","data/listings.json")
        if git("diff","--cached","--quiet",check=False).returncode==0: print("geen wijzigingen"); return
        git("commit","-qm",f"aanbod refresh (box) {now}")
        if git("push","-q",check=False).returncode==0: print("gepusht"); return
        # remote is veranderd: remote-versie nemen en opnieuw samenvoegen (verrijking zit in cache van eigen run)
        prev={l['url']:l for l in data['nieuw']+data['listings']}
        git("reset","-q","HEAD~1"); git("checkout","HEAD","--","data/listings.json")
        git("pull","--rebase","--autostash","-q")
        for l in fresh:
            for k in('rit','geo','kosten'):
                if k in prev.get(l['url'],{}): l[k]=prev[l['url']][k]
    sys.exit("push mislukt na 3 pogingen")
if __name__=="__main__": main()
