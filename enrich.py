"""Verrijking: geocoding (PDOK Locatieserver), rijafstand/-tijd (OSRM publieke demo-server),
hemelsbrede afstand en instapkosten (borg/servicekosten/eenmalige kosten van de advertentiepagina).
Alles wordt gecachet in de listing zelf, dus elke advertentie wordt maar één keer opgevraagd."""
import json,re,html,math,time,urllib.request,urllib.parse,subprocess
UA="woning-dashboard/1.0 (prive huurzoektocht; github.com/Ronic93/woning-dashboard)"
DEST={"adres":"Fokkerweg 300, Oude Meer","lat":None,"lon":None}
_last={"pdok":0,"osrm":0,"page":0,"lbm":0}
def _get(url,kind,gap,headers=None,timeout=30):
    w=_last[kind]+gap-time.time()
    if w>0: time.sleep(w)
    _last[kind]=time.time()
    req=urllib.request.Request(url,headers=headers or {"User-Agent":UA})
    return urllib.request.urlopen(req,timeout=timeout).read().decode('utf8','ignore')
def geocode(q):
    u="https://api.pdok.nl/bzk/locatieserver/search/v3_1/free?"+urllib.parse.urlencode({"q":q,"rows":1,"fl":"weergavenaam,centroide_ll,type"})
    d=json.loads(_get(u,"pdok",0.3))["response"]["docs"]
    if not d: return None
    lon,lat=map(float,re.findall(r'[-\d.]+',d[0]["centroide_ll"])); return dict(lat=lat,lon=lon,match=d[0]["weergavenaam"],type=d[0]["type"])
def hav(a,b):
    R=6371;p1,p2=math.radians(a[0]),math.radians(b[0]);dp=p2-p1;dl=math.radians(b[1]-a[1])
    return 2*R*math.asin(math.sqrt(math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2))
def route(a,b):
    u=f"https://router.project-osrm.org/route/v1/driving/{a[1]},{a[0]};{b[1]},{b[0]}?overview=false"
    r=json.loads(_get(u,"osrm",1.1))["routes"][0]; return r["distance"]/1000,r["duration"]/60
def query(l):
    if l.get("adres"): return f"{l['adres']} {l.get('plaats','')}"
    u=l.get("url","")
    m=re.search(r'/object/([a-z-]+?)-(\d{4}[a-z]{2})-(\d+[a-z]?)-([a-z0-9-]+?)-[0-9a-f]{20,}',u)
    if m: return f"{m.group(4).replace('-',' ')} {m.group(3)} {m.group(2).upper()} {m.group(1).replace('-',' ')}"
    straat=re.sub(r'^(Appartement|Huis|Studio|Kamer|Woning|Benedenwoning|Bovenwoning|Penthouse|Maisonnette)\s+','',l.get("titel",""),flags=re.I)
    pc=re.search(r'\d{4}\s?[A-Z]{2}',l.get("sub","")); return f"{straat} {pc.group(0) if pc else ''} {l.get('plaats','')}"
def set_dest():
    if DEST["lat"] is None:
        g=geocode("Fokkerweg 300 Oude Meer"); DEST.update(lat=g["lat"],lon=g["lon"])
def afstand(l):
    if l.get("rit") and l["rit"].get("dest")==[DEST["lat"],DEST["lon"]]: return
    try:
        g=geocode(query(l))
        if not g: l["rit"]={"fout":"adres niet gevonden"}; return
        a=(g["lat"],g["lon"]);b=(DEST["lat"],DEST["lon"]);km,mn=route(a,b)
        l["geo"]={"lat":round(a[0],5),"lon":round(a[1],5),"match":g["match"],"nauwkeurig":g["type"]}
        # OSRM rekent zonder verkeer; 'spits' is een vuistregel-schatting (+35%, min. +5 min) voor A4/A9/A10-files
        l["rit"]={"hemelsbreed_km":round(hav(a,b),1),"km":round(km,1),"min":round(mn),"min_spits":round(max(mn*1.35,mn+5)),
                  "bron":"OSRM","dest":[DEST["lat"],DEST["lon"]]}
    except Exception as e: l["rit"]={"fout":str(e)[:100]}
# ---------- instapkosten ----------
def eur(s):
    m=re.search(r'€\s*([\d.]+)(?:,(\d{1,2}))?',s or ''); return float(m.group(1).replace('.','')+'.'+(m.group(2) or '0')) if m else None
def pagetext(url):
    if "pararius.nl" in url:
        from refresh import chrome
        time.sleep(2); h=chrome(url)
    else: h=_get(url,"page",1.5,{"User-Agent":"Mozilla/5.0"})
    return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' | ',h)))
def kosten(l,refetch=False):
    if l.get("kosten") and not refetch and "pagina niet geladen" not in l["kosten"].get("notities",[]): return
    huur=float(l.get("huur") or 0); k={"huur":huur,"service":None,"borg":None,"borg_bron":None,"eenmalig":[],"notities":[]}
    try: t=pagetext(l["url"]) if l.get("url") else ""
    except Exception as e: t=""; k["notities"].append("pagina niet geladen")
    if t and len(t)<2000: k["notities"].append("pagina niet geladen")
    if t and len(t)>2000:
        m=re.search(r'Servicekosten\s*\|[\s|]*(€\s*[\d.,]+)',t) or re.search(r'servicekosten[^|.]{0,40}?(€\s*[\d.,]+)',t,re.I)
        if m: k["service"]=eur(m.group(1))
        m=re.search(r'Waarborg(?:som)?\s*\|[\s|]*Vast inkomen:\s*(€\s*[\d.,]+)',t)  # ikwilhuren: borg bij vast inkomen
        if m: k["borg"],k["borg_bron"]=eur(m.group(1)),"advertentie (vast inkomen)"
        if k["borg"] is None:
            m=re.search(r'(?:Waarborgsom|Borg)\s*\|[\s|]*(€\s*[\d.,]+)',t,re.I) or re.search(r'(?:waarborgsom|borg)[^|.€]{0,40}?(€\s*[\d.,]+)',t,re.I)
            if m and eur(m.group(1)) and eur(m.group(1))>=100: k["borg"],k["borg_bron"]=eur(m.group(1)),"advertentie"
        if k["borg"] is None:
            m=re.search(r'(?:waarborgsom|borg)[^|.€]{0,60}?\b(één|een|1|twee|2|drie|3)\s*(?:x|keer|maal|maand)',t,re.I) or \
              re.search(r'\b(één|een|1|twee|2|drie|3)\s*(?:x|keer|maal|maand(?:en)?)\s*(?:de\s*)?(?:kale\s*)?(?:maand)?huur\s*(?:als\s*)?(?:waarborgsom|borg)',t,re.I)
            if m:
                n={"één":1,"een":1,"1":1,"twee":2,"2":2,"drie":3,"3":3}[m.group(1).lower()]; k["borg"],k["borg_bron"]=n*huur,f"advertentie ({n}× huur)"
        for naam,pat in [("contractkosten",r'contractkosten'),("administratiekosten",r'administratiekosten'),("opleveringskosten",r'opleveringskosten')]:
            m=re.search(pat+r'[\s|:]{0,8}(?:van\s*|bedragen\s*)?(€\s*[\d.,]+)',t,re.I)
            if m and eur(m.group(1)): k["eenmalig"].append({"naam":naam,"bedrag":eur(m.group(1))})
        if re.search(r'(bemiddelings|makelaars)kosten[^|]{0,60}€',t,re.I) and not re.search(r'geen\s+(bemiddelings|makelaars)kosten',t,re.I):
            k["notities"].append("Advertentie noemt bemiddelings-/makelaarskosten: die mag de verhuurder/makelaar sinds 2015 niet bij huurders rekenen als hij ook voor de verhuurder werkt.")
    if k["service"] is None and l.get("service") is not None: k["service"]=float(l["service"])
    if k["borg"] is None: k["borg"],k["borg_max"],k["borg_bron"]=huur,2*huur,"geschat"
    k["eerste_betaling"]=round(huur+(k["service"] or 0)+(k["borg"] or 0)+sum(x["bedrag"] for x in k["eenmalig"]),2)
    if k["borg_bron"]=="geschat": k["eerste_betaling_max"]=round(k["eerste_betaling"]+huur,2)
    l["kosten"]=k
KL={1:"Zeer onvoldoende",2:"Ruim onvoldoende",3:"Onvoldoende",4:"Zwak",5:"Voldoende",6:"Ruim voldoende",7:"Goed",8:"Zeer goed",9:"Uitstekend"}
def buurt(l):
    """Leefbaarometer 3.0 (meting 2024) buurtscore via de openbare WFS van het ministerie van BZK."""
    if l.get("buurt") or not l.get("geo"): return
    la,lo=l["geo"]["lat"],l["geo"]["lon"]
    u=("https://geo.leefbaarometer.nl/lbm3/ows?service=WFS&version=2.0.0&request=GetFeature&typeNames=lbm3:buurtscore24"
       f"&outputFormat=application/json&count=1&propertyName=name,gemeente,lbm,kscore,konv,ksoc&bbox={la},{lo},{la},{lo},urn:ogc:def:crs:EPSG::4326")
    try:
        f=json.loads(_get(u,"lbm",0.5))["features"]
        if not f: return
        p=f[0]["properties"]; l["buurt"]={"naam":p["name"],"gemeente":p["gemeente"],"lbm":round(p["lbm"],2),"klasse":p["kscore"],"onv":p["konv"],"soc":p["ksoc"]}
    except Exception: pass
def oordeel(l):
    """Automatisch buurtoordeel voor nieuw aanbod (handmatige oordelen in 'Mijn lijst' blijven staan)."""
    b=l.get("buurt")
    if not b or (l.get("verdict") and not l.get("verdict_auto")): return
    k=b["klasse"]; v="aanrader" if k>=8 else "prima" if k>=6 else "twijfel" if k==5 else "afraden"
    stap=["aanrader","prima","twijfel","afraden"]
    if b["onv"]<=2 and v!="afraden": v=stap[stap.index(v)+1]
    l.update(verdict=v,verdict_auto=True,lbm=b["lbm"],lbm_klasse=KL.get(k,""))
    zorg=[]
    if b["onv"]<=2: zorg.append("veiligheid scoort zwak (overlast/criminaliteit)")
    elif b["onv"]<=3: zorg.append("veiligheid onder het gemiddelde")
    if b["soc"]<=2: zorg.append("sociale samenhang zwak")
    l["review"]=f"Buurt {b['naam']} ({b['gemeente']}): Leefbaarometer {KL.get(k,'')} ({str(b['lbm']).replace('.',',')})"+(" – let op: "+", ".join(zorg) if zorg else " – geen rode vlaggen in de cijfers")+". Automatisch oordeel, check de straat zelf (Street View/'s avonds langsrijden)."
def verrijk(lijst,log,max_nieuw=400):
    set_dest(); n=0
    for l in lijst:
        if n>=max_nieuw: break
        need=not l.get("kosten") or "pagina niet geladen" in l["kosten"].get("notities",[]) or not (l.get("rit") and l["rit"].get("dest")==[DEST["lat"],DEST["lon"]])
        afstand(l); kosten(l); buurt(l); oordeel(l); n+=need
    log.append(f"verrijkt: {n} (bestemming {DEST['adres']})")
    return {"adres":DEST["adres"],"lat":DEST["lat"],"lon":DEST["lon"]}
