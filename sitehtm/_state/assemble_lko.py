#!/usr/bin/env python3
"""LKO assembly: pages.jsonl + dup_review.json -> ordered pages, dup groups, titles, data.js."""
import importlib.util, os, json, re, numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
spec=importlib.util.spec_from_file_location("rb","sitehtm/rebuild.py"); rb=importlib.util.module_from_spec(spec); spec.loader.exec_module(rb)
site="sitehtm"
pages=[json.loads(l) for l in open("_work/pages.jsonl") if l.strip()]
docs={}
for p in pages: docs.setdefault(p['doc'],[]).append(p)
for d in docs: docs[d].sort(key=lambda p:p['p'])
order=json.load(open("_work/doc_order.json")) if os.path.exists("_work/doc_order.json") else sorted(docs)
# page-level similarity (recomputed; cheap)
vec=TfidfVectorizer(stop_words="english",ngram_range=(1,2),sublinear_tf=True,token_pattern=r"[a-z]{3,}")
Xp=vec.fit_transform([p['text'].lower() for p in pages]); pidx={p['id']:i for i,p in enumerate(pages)}
def sim(a,b): return float((Xp[pidx[a]]@Xp[pidx[b]].T).toarray()[0,0])
rv=json.load(open("_work/dup_review.json")); ov=json.load(open("_work/dup_overrides.json")) if os.path.exists("_work/dup_overrides.json") else {}
gid=0
for c in rv['clusters']:
    g=c['group']
    ms=sorted(c['members'],key=(lambda m:(-m['pages'],-m['quality'])) if c['kind']!='same' else (lambda m:(-m['quality'],-m['pages'])))
    if str(g) in ov.get('keep_all',[]): continue
    keep=ov.get('overrides',{}).get(str(g),ms[0]['id']); kd=int(keep[1:])
    for p in docs[kd]: p['keep']=True
    for m in c['members']:
        d=int(m['id'][1:])
        if d==kd: continue
        for p in docs[d]:
            best=max(docs[kd],key=lambda q:sim(p['id'],q['id'])); s=sim(p['id'],best['id'])
            if s>=0.45 or m['pages']==len(docs[kd]):
                tgt=best if s>=0.45 else docs[kd][min(p['p'],len(docs[kd]))-1]
                if not tgt.get('g'): gid+=1; tgt['g']=gid
                p['g']=tgt['g']
dt=json.load(open("_work/doc_titles.json")) if os.path.exists("_work/doc_titles.json") else {}
def auto_doc_title(d):
    t=docs[d][0]['text']; toks=re.findall(r"[A-Za-z][A-Za-z'&\-]*",t)
    ok=lambda w: re.fullmatch(r"[A-Z]?[a-z']{2,}|[A-Z][a-z']+|[A-Z]{3,}",w) is not None
    best=None
    for i in range(len(toks)):
        if not ok(toks[i]): continue
        run=[]
        for w in toks[i:i+9]:
            if ok(w): run.append(w)
            else: break
        if len(run)>=6: best=run; break
        if best is None or len(run)>len(best): best=run
    s=" ".join(best or toks[:8]).strip()
    return (s[:1].upper()+s[1:])[:64] if len(s)>8 else f"Document {d}"
ordered=[p for d in order for p in docs[d]]
curated={}
for i,p in enumerate(ordered,1):
    p['book']="Binder"; p['srcp']=p['p']; p['num']=i; p['p']=i; p['id']=f"PG-{i:04d}"
    n=len(docs[p['doc']]); title=dt.get(f"D{p['doc']:03d}") or auto_doc_title(p['doc'])
    curated[f"Binder|{i}"]=title if n==1 else f"{title} ({p['srcp']}/{n})"
    p['kw']=rb.keywords_for(p['text']); p['title']=curated[f"Binder|{i}"]; p['auto']=f"D{p['doc']:03d}" not in dt
    p['src_pdf']=p['src']; p['src_id']=f"D{p['doc']:03d}-{p['srcp']:03d}"
json.dump(curated,open(f"{site}/titles.json","w"),indent=0,ensure_ascii=False)
json.dump({p['id']:p['src_id'] for p in ordered},open(f"{site}/_state/idmap_lko.json","w"),indent=0)
concepts=rb.attach_concepts(ordered,json.load(open(f"{site}/concepts.json"))) if os.path.exists(f"{site}/concepts.json") else {}
records=[{k:v for k,v in p.items() if k not in ("img","learn","src","doc","np","rot","stage")} for p in ordered]
with open(f"{site}/data.js","w") as f:
    f.write("window.BINDER="+json.dumps(records,ensure_ascii=False)+";\n"); f.write("window.CONCEPTS="+json.dumps(concepts,ensure_ascii=False)+";\n")
json.dump(records,open(f"{site}/combined.json","w"),ensure_ascii=False)
json.dump([{"id":p['id'],"img":p['img']} for p in ordered],open("_work/imgmap.json","w"))
ng=len(set(p['g'] for p in ordered if p.get('g'))); ns=sum(1 for p in ordered if p.get('g') and not p.get('keep'))
print(f"{len(ordered)} pages, {ng} dup groups, {ns} surplus copies hidden; data.js {os.path.getsize(site+'/data.js')//1024} KB")
