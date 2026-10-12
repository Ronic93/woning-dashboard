import json,re
R=open('/workspace/woning-zoeken/buurtrecensies-2026-10-08.md').read()
why={}
for m in re.finditer(r'^### (\w+)\. .*?\n(.*?)(?=^### |\Z)',R,re.S|re.M):
    w=re.search(r'\*\*Waarom [^:]*:\*\* (.*)',m.group(2)); why[m.group(1)]=w.group(1).strip() if w else ''
P='https://www.pararius.nl/appartement-te-huur/'
I='https://ikwilhuren.nu/object/'
S='https://zoeken.schepvastgoedmanagers.nl/huur/woningen/other-properties-ptm-schep-prod-'
# id,plaats,adres,regio,huur,service,m2,lbm_buurt,lbm_score,verdict,parkeren,url,online,beschikbaar
L=[
("1","Voorburg","Vlietwijck 104","Zuid-Holland",980.91,78,50,"Uitstekend",4.36,"aanrader","Vergunning (Leidschendam-Voorburg)",P+"voorburg/2d469429/vlietwijck",True,"per direct"),
("2","Rijswijk","Grote Vuurvlinderstraat 261","Zuid-Holland",1025,0,66,"Zeer goed",4.23,"aanrader","Parkeerdruk 's avonds (lage norm)",P+"rijswijk/65959627/grote-vuurvlinderstraat",True,"volgorde binnenkomst"),
("3","Rotterdam","Oudedijk 188A","Zuid-Holland",1050,0,57,"Goed",4.17,"aanrader","Vergunning Rotterdam",P+"rotterdam/b14645a0/oudedijk",None,""),
("4a","Vlaardingen","Jean Monnetring 209","Zuid-Holland",1044,60,81,"Ruim voldoende",4.04,"prima","Gratis parkeren ✔",I+"vlaardingen-3137dc-209-jean-monnetring-22d11dbbf16d7af1b227ff4d7a83c7f6/",True,"per direct"),
("4b","Vlaardingen","Jean Monnetring 193","Zuid-Holland",1036,60,81,"Ruim voldoende",4.04,"prima","Gratis parkeren ✔",I+"vlaardingen-3137dc-193-jean-monnetring-201ba7700a6077a04b4139e66f449eae/",True,"1 nov"),
("5","Zoetermeer","Engelandlaan 180","Zuid-Holland",1077,37,53,"Ruim voldoende",4.04,"prima","Vergunning €36/jaar",S+"engelandlaan-180",None,"1 nov"),
("6","Leiden","Breestraat","Zuid-Holland",837,0,47,"Uitstekend",4.28,"prima","Lastig (wachtlijst zone A)",P+"leiden/5c90dd2b/breestraat",None,""),
("7","Sliedrecht","Geulstraat 8","Zuid-Holland",932,100,58,"Ruim voldoende",4.07,"prima","Gratis ✔",P+"sliedrecht/52c77b5b/geulstraat",None,""),
("8","Rotterdam","Jufferstraat","Zuid-Holland",1075,25,61,"Zeer goed",4.21,"prima","Eigen parkeerplaats ✔","https://www.huurstunt.nl/appartement/huren/in/rotterdam/jufferstraat/f3ewc",False,"waarschijnlijk verouderd"),
("9","Den Haag","Loosduinseweg","Zuid-Holland",850,0,60,"Goed",4.14,"twijfel","Vergunning Den Haag",P+"den-haag/f745469d/loosduinseweg",None,"huisvestingsvergunning nodig"),
("10","Rotterdam","Quadenoord 72","Zuid-Holland",1083.88,27.70,60,"Voldoende",3.96,"twijfel","Vergunning",P+"rotterdam/e7698a46/quadenoord",None,""),
("11","Rotterdam","Pretorialaan 24D","Zuid-Holland",920,0,52,"Ruim voldoende",4.00,"twijfel","Vergunning",P+"rotterdam/da716b78/pretorialaan",True,"16 okt"),
("12","Den Haag","Erasmusweg 1179-L","Zuid-Holland",1070.14,60,65,"Zwak",3.82,"twijfel","Eigen parkeerplaats +€57 ✔",S+"erasmusweg-1179-l",True,"1 nov"),
("13","Nieuwegein","Tinnegieterstede 68","Utrecht",1057.13,90,52,"Voldoende",3.95,"twijfel","Geen vergunning mogelijk",I+"nieuwegein-3431hx-68-tinnegieterstede-3f19e977d31e52612ccb5a89e8a1263e/",None,"16 dec"),
("14","Rotterdam","Schiedamseweg 101B","Zuid-Holland",985,0,70,"Zwak",3.90,"afraden","Vergunning",P+"rotterdam/107d2b16/schiedamseweg",None,""),
("15","Utrecht","Vader Rijndreef 154","Utrecht",986.68,65,54,"Zwak",3.92,"afraden","",I+"utrecht-3561xa-154-vader-rijndreef-4506a59d16ecc5751e6cf6ae12a0cd8c/",None,"loting"),
]
K=["id","plaats","adres","regio","huur","service","m2","lbm_klasse","lbm","verdict","parkeren","url","online","beschikbaar"]
out=[]
for t in L:
    d=dict(zip(K,t)); d["review"]=why.get(d["id"].rstrip("ab"),""); d["bron"]="seed 8-12 okt"
    d["extra"]=57 if d["id"]=="12" else 0
    out.append(d)
json.dump({"bijgewerkt":"2026-10-12T07:45","listings":out,"nieuw":[]},open("data/listings.json","w"),ensure_ascii=False,indent=1)
print(len(out),sum(1 for d in out if d["review"]))
