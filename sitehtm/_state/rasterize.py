import json,os,subprocess,glob
man=json.load(open('_work/manifest.json'))
for m in man:
    d=f"_work/raw_{m['suffix']}"
    if len(glob.glob(d+'/pg-*.jpg'))==m['pages']: continue
    os.makedirs(d,exist_ok=True)
    subprocess.run(['pdftoppm','-r','200','-jpeg','/home/claude/lko_src/'+m['name'],d+'/pg'],check=True)
    print(m['suffix'],flush=True)
print("RASTER DONE")
