#!/usr/bin/env python3
"""LKO 2 build, framework shape (FRAMEWORK.md): pages.jsonl + dup_review.json + concepts.json + doc_groups.py
-> sitehtm/data.js (window.BINDER / window.CONCEPTS), combined.json, titles.json, concepts.json (pins filled),
   _state/idmap_lko.json, _work/doc_order.json, _work/doc_titles.json, _work/imgmap.json.
Run from the build folder (the one holding sitehtm/ and _work/):  python3 sitehtm/_state/build_lko2.py
Never re-OCR: pages.jsonl is the checkpoint. Images are made by images_lko.py from _work/imgmap.json."""
import importlib.util, os, re, sys, json, collections
from sklearn.feature_extraction.text import TfidfVectorizer

site = "sitehtm"
spec = importlib.util.spec_from_file_location("rb", f"{site}/rebuild.py"); rb = importlib.util.module_from_spec(spec); spec.loader.exec_module(rb)
sys.path.insert(0, "_work"); from doc_groups import GROUPS

pages = [json.loads(l) for l in open("_work/pages.jsonl") if l.strip()]
docs = collections.defaultdict(list)
for p in pages: docs[p["doc"]].append(p)
for d in docs: docs[d].sort(key=lambda p: p["p"])
man = {m["doc"]: m for m in json.load(open("_work/manifest.json"))}
rv = json.load(open("_work/dup_review.json"))
concepts = json.load(open(f"{site}/concepts.json"))
group_of = {d: g for g, ds in GROUPS for d in ds}
assert sorted(group_of) == sorted(docs), "every document must be in exactly one group"
assert [g for g, _ in GROUPS] == list(concepts), "doc_groups.py and concepts.json must list the same groups in the same order"

# ---- duplicate groups: keep copy = best OCR quality (same) / most pages (partial), as dup_review decided
vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True, token_pattern=r"[a-z]{3,}")
Xp = vec.fit_transform([p["text"].lower() for p in pages]); pidx = {p["id"]: i for i, p in enumerate(pages)}
def sim(a, b): return float((Xp[pidx[a]] @ Xp[pidx[b]].T).toarray()[0, 0])
keep_of = {}           # member doc -> keep doc (same-kind clusters, used for ordering)
gid = 0
for c in rv["clusters"]:
    key = (lambda m: (-m["pages"], -m["quality"])) if c["kind"] != "same" else (lambda m: (-m["quality"], -m["pages"]))
    ms = sorted(c["members"], key=key); kd = int(ms[0]["id"][1:])
    for p in docs[kd]: p["keep"] = True
    for m in c["members"]:
        d = int(m["id"][1:])
        if d == kd: continue
        if c["kind"] == "same": keep_of[d] = kd
        for p in docs[d]:
            best = max(docs[kd], key=lambda q: sim(p["id"], q["id"])); s = sim(p["id"], best["id"])
            if s >= 0.45 or m["pages"] == len(docs[kd]):
                tgt = best if s >= 0.45 else docs[kd][min(p["p"], len(docs[kd])) - 1]
                if not tgt.get("g"): gid += 1; tgt["g"] = gid
                p["g"] = tgt["g"]

# ---- teaching order: groups as listed; inside a group scan order, an identical copy right after its keep copy
order = []
for g, ds in GROUPS:
    placed = set()
    for d in sorted(ds):
        if d in placed: continue
        chain = [d] + sorted(x for x in ds if keep_of.get(x) == d)
        if keep_of.get(d) in ds and keep_of[d] not in placed and keep_of[d] > d:   # copy scanned before its keep copy
            continue
        for x in chain:
            if x not in placed: order.append(x); placed.add(x)
    for d in sorted(ds):                                                           # anything the chain rule skipped
        if d not in placed: order.append(d); placed.add(d)
assert sorted(order) == sorted(docs)

# ---- titles: the scan's own name (ScanSnap's first line) when it reads like words, else the kit's auto title
def clean_name(d):
    n = re.sub(r"\.pdf$", "", man[d]["name"]); n = re.sub(r"^\d{8}_", "", n); n = re.sub(r"_\d{3}$", "", n)
    n = n.replace("#U2022", " ").replace("#U2751", " "); n = re.sub(r"#U[0-9a-fA-F]{4}", " ", n)
    n = n.replace("_", " "); n = re.sub(r"\s+", " ", n).strip(" -.,;:'\"")
    toks = re.findall(r"[A-Za-z]+", n)
    good = sum(1 for t in toks if rb.real_word(t.lower()) or t.isupper() and len(t) >= 2 or len(t) >= 3 and t[0].isupper())
    return n[:72] if toks and good >= 2 and good / len(toks) >= 0.6 else None
def auto_title(d):
    t = docs[d][0]["text"]; toks = re.findall(r"[A-Za-z][A-Za-z'&\-]*", t)
    ok = lambda w: re.fullmatch(r"[A-Z]?[a-z']{2,}|[A-Z][a-z']+|[A-Z]{3,}", w) is not None
    best = None
    for i in range(len(toks)):
        if not ok(toks[i]): continue
        run = []
        for w in toks[i:i + 9]:
            if ok(w): run.append(w)
            else: break
        if len(run) >= 6: best = run; break
        if best is None or len(run) > len(best): best = run
    s = " ".join(best or toks[:8]).strip()
    return (s[:1].upper() + s[1:])[:64] if len(s) > 8 else None
doc_titles = {}
for d in docs:
    doc_titles[f"D{d:03d}"] = clean_name(d) or auto_title(d) or f"Scan {man[d]['name'][:8]} (document {d})"

# ---- renumber and shape every page the framework's way
ordered = [p for d in order for p in docs[d]]
curated, idmap, imgmap, records = {}, {}, [], []
for i, p in enumerate(ordered, 1):
    pid = f"PG-{i:04d}"; n = len(docs[p["doc"]]); t = doc_titles[f"D{p['doc']:03d}"]
    title = t if n == 1 else f"{t} ({p['p']}/{n})"
    curated[f"Binder|{i}"] = title; idmap[pid] = f"D{p['doc']:03d}-{p['p']:03d}"; imgmap.append({"id": pid, "img": p["img"]})
    r = {"id": pid, "book": "Binder", "p": i, "num": i, "title": title, "text": p["text"], "kw": rb.keywords_for(p["text"]),
         "g": p.get("g", 0), "concepts": [], "learn": ""}
    if p.get("keep"): r["keep"] = True          # the better copy of a duplicate (the LKO index.htm honours it; others ignore it)
    r["_doc"] = p["doc"]; records.append(r)
for g, ds in GROUPS:
    concepts[g]["pin"] = [r["id"] for r in records if r["_doc"] in set(ds)]
    concepts[g]["pin_only"] = True; concepts[g]["match"] = []
for r in records: del r["_doc"]
concepts = rb.attach_concepts(records, concepts)
for g, c in concepts.items():
    nums = sorted(int(i[3:]) for i in c["pages"]); assert nums == list(range(nums[0], nums[-1] + 1)), f"{g} is not contiguous"
assert all(len(r["concepts"]) == 1 for r in records), "every page has exactly one home group"

json.dump(curated, open(f"{site}/titles.json", "w"), indent=0, ensure_ascii=False)
json.dump(concepts, open(f"{site}/concepts.json", "w"), indent=1, ensure_ascii=False)
json.dump(idmap, open(f"{site}/_state/idmap_lko.json", "w"), indent=0)
json.dump(order, open("_work/doc_order.json", "w")); json.dump(doc_titles, open("_work/doc_titles.json", "w"), indent=0, ensure_ascii=False)
json.dump(imgmap, open("_work/imgmap.json", "w"))
with open(f"{site}/data.js", "w") as f:
    f.write("window.BINDER=" + json.dumps(records, ensure_ascii=False) + ";\n")
    f.write("window.CONCEPTS=" + json.dumps(concepts, ensure_ascii=False) + ";\n")
json.dump(records, open(f"{site}/combined.json", "w"), ensure_ascii=False)
ng = len(set(r["g"] for r in records if r["g"])); ns = sum(1 for r in records if r["g"] and not r.get("keep"))
named = sum(1 for d in docs if clean_name(d))
print(f"{len(records)} pages, {len(concepts)} groups, {ng} dup groups, {ns} surplus copies hidden, "
      f"{named} of {len(docs)} titles from the scan names; data.js {os.path.getsize(site + '/data.js') // 1024} KB")
