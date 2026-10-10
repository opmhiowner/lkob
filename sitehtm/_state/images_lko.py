import json,os,sys
from PIL import Image
site="sitehtm"; WEB,TH=2400,320
m=json.load(open('_work/imgmap.json')); n=0
os.makedirs(f"{site}/pages",exist_ok=True); os.makedirs(f"{site}/thumbs",exist_ok=True)
for e in m:
    dp,dt=f"{site}/pages/{e['id']}.jpg",f"{site}/thumbs/{e['id']}.jpg"
    if os.path.exists(dp) and os.path.exists(dt): continue
    im=Image.open(e['img']).convert("RGB"); w=im.copy(); w.thumbnail((WEB,WEB)); w.save(dp,quality=82,optimize=True)
    t=im.copy(); t.thumbnail((TH,TH)); t.save(dt,quality=78,optimize=True); n+=1
print("IMAGES DONE",n)
