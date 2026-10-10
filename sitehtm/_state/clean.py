#!/usr/bin/env python3
"""Stage 2: deskew/crop + upright footer-stamp removal (raw -> pages/). Checkpoint: _work/clean_done.txt. Resumable."""
from PIL import Image
import importlib.util, os, glob, json, shutil, sys, time
spec = importlib.util.spec_from_file_location("rb", "sitehtm/rebuild.py")
rb = importlib.util.module_from_spec(spec); spec.loader.exec_module(rb)
pages=[json.loads(l) for l in open('_work/pages.jsonl')]
CK='_work/clean_done.txt'
done=set(l.split()[0] for l in open(CK) if l.strip()) if os.path.exists(CK) else set()
budget=float(sys.argv[1]) if len(sys.argv)>1 else 110
t0=time.time(); n=0
with open(CK,'a') as ck:
    for p in pages:
        if p['id'] in done: continue
        if time.time()-t0>budget: print('budget',n,len(done)+n); sys.exit(0)
        raw=f"_work/raw_D{p['doc']:03d}"
        src=sorted(glob.glob(raw+'/pg-*.jpg'))[p['p']-1]
        dst=p['img']
        if not rb.deskew_and_crop(src,dst): shutil.copy(src,dst)
        im=Image.open(dst).convert("RGB"); im,nf=rb._footer_pass(im,det_w=1000)
        if nf: im.save(dst,quality=95)
        ck.write(f"{p['id']} {nf}\n"); ck.flush(); n+=1
print("CLEAN DONE",n)
