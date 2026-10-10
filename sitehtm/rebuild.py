#!/usr/bin/env python3
"""
rebuild.py — regenerate the Oishi's binder archive from fresh PDFs.

The website code (index.htm) is NOT touched. This only regenerates:
    data.js      the search index: text, titles, keywords, duplicates, numbers
    thumbs/      320px card thumbnails
    pages/       1400px page images
    binders_combined.html   the single-file phone build

Usage:
    python3 rebuild.py --hawaii Hawaii.pdf --vegas Las_Vegas.pdf --site sitehtm
    python3 rebuild.py ... --limit 6        # quick test on the first few pages

Requires: poppler-utils (pdfimages), tesseract-ocr, pillow, numpy, opencv-python,
          scikit-learn, pytesseract
"""

import argparse, base64, glob, io, json, os, re, shutil, subprocess, sys
import collections

import numpy as np
from PIL import Image
import cv2
import pytesseract
from sklearn.feature_extraction.text import TfidfVectorizer

# ---------------------------------------------------------------- settings
DPI_SCALE      = 8       # detection downscale
MAX_DESKEW     = 6.0     # degrees
DUP_THRESHOLD  = 0.55    # cosine similarity that counts as the same page
ROT_MIN_GAIN   = 3       # extra real words needed to accept a 90-degree rotation
WEB_PX, THUMB_PX = 2400, 320
PHONE_PAGE_PX, PHONE_THUMB_PX = 1300, 300

STOPWORDS = set("""this that with have will your from they when what their there
which would could should about into more been than them then some very""".split())


# ---------------------------------------------------------------- 1. extract
def extract_pages(pdf, outdir, dpi=200):
    """Rasterize one image per PDF page, in order.

    Earlier this used `pdfimages -all`, but that dumps every embedded image
    OBJECT (soft-masks, CCITT stencils, .params sidecars), which breaks the
    one-image-per-page numbering on any scan that isn't a single flat JPEG.
    pdftoppm renders exactly one upright page image per page.
    """
    os.makedirs(outdir, exist_ok=True)
    subprocess.run(["pdftoppm", "-r", str(dpi), "-jpeg", pdf,
                    os.path.join(outdir, "pg")], check=True)
    files = sorted(glob.glob(os.path.join(outdir, "pg-*.jpg")))
    print(f"   extracted {len(files)} page scans from {os.path.basename(pdf)}")
    return files


# ---------------------------------------------------------------- 2. deskew + crop
def estimate_skew(gray):
    """The angle whose horizontal ink profile has the sharpest peaks is level."""
    ink = (gray < 200).astype(np.float32)
    if ink.sum() < 500:
        return 0.0
    h, w = ink.shape
    best_a, best_s = 0.0, -1.0
    for a in np.arange(-MAX_DESKEW, MAX_DESKEW + .001, .25):
        M = cv2.getRotationMatrix2D((w/2, h/2), float(a), 1.0)
        r = cv2.warpAffine(ink, M, (w, h), flags=cv2.INTER_NEAREST, borderValue=0)
        prof = r.sum(axis=1)
        s = float(((prof[1:] - prof[:-1]) ** 2).sum())
        if s > best_s:
            best_s, best_a = s, float(a)
    return best_a


def content_mask(gray):
    m = (cv2.GaussianBlur(gray, (5,5), 0) < 250).astype(np.uint8) * 255
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN,  np.ones((3,3),  np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((35,35), np.uint8))
    return m


def deskew_and_crop(src, dst, margin=40):
    img = cv2.imread(src)
    if img is None:
        return False
    H, W = img.shape[:2]
    small = cv2.resize(img, (W//DPI_SCALE, H//DPI_SCALE), interpolation=cv2.INTER_AREA)
    gray  = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    ang   = estimate_skew(gray)
    if ang:
        M = cv2.getRotationMatrix2D((W/2, H/2), ang, 1.0)
        img = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_CUBIC,
                             borderMode=cv2.BORDER_CONSTANT, borderValue=(255,255,255))
        small = cv2.resize(img, (W//DPI_SCALE, H//DPI_SCALE), interpolation=cv2.INTER_AREA)
        gray  = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    pts = cv2.findNonZero(content_mask(gray))
    if pts is None:
        cv2.imwrite(dst, img, [cv2.IMWRITE_JPEG_QUALITY, 95]); return True
    x, y, w, h = [v*DPI_SCALE for v in cv2.boundingRect(pts)]
    x0, y0 = max(0, x-margin), max(0, y-margin)
    x1, y1 = min(W, x+w+margin), min(H, y+h+margin)
    if (x1-x0)*(y1-y0) < .45*W*H:          # sparse page: don't crop to a stray mark
        x0, y0, x1, y1 = 0, 0, W, H
    cv2.imwrite(dst, img[y0:y1, x0:x1], [cv2.IMWRITE_JPEG_QUALITY, 95])
    return True


# ---------------------------------------------------------------- 3. footers
FOOT_TOKEN = re.compile(r"""(
    ^[A-Za-z]:\\ | \\\\ | \\
  | \.(?:docx?|vsd|xlsx?|pdf)\b
  | ^\d{1,2}/\d{1,2}/\d{2,4}$ | ^\d{1,2}:\d{2}(?::\d{2})?$ | ^(?:AM|PM)$
  | ^(?:created|printed|modified|last)$ | ^(?:share|n)/ | ^[A-Za-z]:$
)""", re.I | re.X)

def _footer_pass(im, det_w=1500, top=.12, bot=.18, pad=6):
    W, H = im.size
    sc = det_w / W
    small = im.resize((det_w, max(1, int(H*sc))), Image.LANCZOS)
    sw, sh = small.size
    try:
        d = pytesseract.image_to_data(small, output_type=pytesseract.Output.DICT, config="--psm 6")
    except Exception:
        return im, 0
    lines = {}
    for i, t in enumerate(d["text"]):
        if not t.strip():
            continue
        y = d["top"][i] + d["height"][i]/2
        if not (y <= sh*top or y >= sh*(1-bot)):
            continue
        lines.setdefault((d["block_num"][i], d["par_num"][i], d["line_num"][i]), []).append(i)
    boxes = []
    for idxs in lines.values():
        idxs.sort(key=lambda i: d["left"][i])
        flags = [bool(FOOT_TOKEN.search(d["text"][i].strip())) and len(d["text"][i].strip()) > 1
                 for i in idxs]
        if not any(flags):
            continue
        a, b = flags.index(True), len(flags)-1-flags[::-1].index(True)
        boxes += [(d["left"][i], d["top"][i], d["width"][i], d["height"][i]) for i in idxs[a:b+1]]
    if not boxes:
        return im, 0
    arr, inv = np.array(im), 1/sc
    for (x, y, w, h) in boxes:
        X0, X1 = max(0, int((x-pad)*inv)), min(W, int((x+w+pad)*inv))
        Y0, Y1 = max(0, int((y-pad)*inv)), min(H, int((y+h+pad)*inv))
        arr[Y0:Y1, X0:X1] = 255
    return Image.fromarray(arr), len(boxes)


def strip_footers(path):
    """Whiten file-path/timestamp stamps at the bottom, top, or up the side margin."""
    im, total = Image.open(path).convert("RGB"), 0
    for fwd, back in [(None, None),
                      (Image.ROTATE_90, Image.ROTATE_270),
                      (Image.ROTATE_270, Image.ROTATE_90)]:
        work = im.transpose(fwd) if fwd else im
        work, n = _footer_pass(work)
        im = work.transpose(back) if back else work
        total += n
    if total:
        im.save(path, quality=95)
    return total


# ---------------------------------------------------------------- 4. rotation
DICT_WORDS = set("""the and for you are with that this your when their have will they from
what page team time work rules message customer business problem people listen owner
property management""".split())

def _word_score(im):
    try:
        t = pytesseract.image_to_string(im, config="--psm 6").lower()
    except Exception:
        return 0
    return sum(w in DICT_WORDS for w in re.findall(r"[a-z]{3,}", t))


def fix_rotation(path):
    """Turn sideways page-spreads upright. Two signals: OSD, then readability."""
    im = Image.open(path).convert("RGB")
    probe = im.copy(); probe.thumbnail((1000, 1000))
    try:
        osd = pytesseract.image_to_osd(probe, config="--psm 0")
        rot = int(re.search(r"Rotate: (\d+)", osd).group(1))
    except Exception:
        return 0
    if rot == 0:
        return 0
    pil = {90: Image.ROTATE_270, 180: Image.ROTATE_180, 270: Image.ROTATE_90}[rot]
    base, fixed = _word_score(probe), _word_score(probe.transpose(pil))
    if fixed <= base + ROT_MIN_GAIN:        # diagrams and correct pages fail this
        return 0
    im.transpose(pil).save(path, quality=95)
    return rot


# ---------------------------------------------------------------- 5. OCR
def ocr_page(path, px=1500):
    im = Image.open(path); im.thumbnail((px, px))
    try:
        return " ".join(pytesseract.image_to_string(im, config="--psm 1").split())
    except Exception:
        return ""


TAIL_PATH = re.compile(r"[A-Za-z]:\\|\\\\")

def clean_text(t):
    """Drop any path/stamp text that survived at the very end of the page."""
    tail = t[-500:]
    i = tail.find("\\\\")
    if i == -1:
        m = TAIL_PATH.search(tail)
        i = m.start() if m else -1
    if i != -1:
        t = (t[:-500] + tail[:i]).strip()
    return " ".join(t.split())


# ---------------------------------------------------------------- 6. duplicates
def find_duplicates(pages):
    """Group pages that are the same document, within and across binders."""
    docs = [p["text"].lower() for p in pages]
    if not any(docs):
        return {}
    vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2),
                          sublinear_tf=True, token_pattern=r"[a-z]{3,}")
    X = vec.fit_transform(docs)
    S = (X @ X.T).toarray()
    np.fill_diagonal(S, 0)

    parent = list(range(len(pages)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i
    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb: parent[rb] = ra

    for i in range(len(pages)):
        for j in range(i+1, len(pages)):
            if S[i, j] >= DUP_THRESHOLD:
                union(i, j)

    clusters = collections.defaultdict(list)
    for i in range(len(pages)):
        clusters[find(i)].append(i)
    gid, out = 0, {}
    for members in clusters.values():
        if len(members) > 1:
            gid += 1
            for i in members:
                out[i] = gid
    return out


# ---------------------------------------------------------------- 7. titles + keywords
def real_word(w):
    if not re.fullmatch(r"[a-z][a-z'\-]{3,13}", w):
        return False
    v = sum(c in "aeiouy" for c in w) / len(w)
    return .15 <= v <= .7 and not re.search(r"[bcdfghjklmnpqrstvwxz]{4}", w)


def keywords_for(text, n=8):
    freq = collections.Counter(
        w for w in re.findall(r"[a-z]{4,}", text.lower())
        if w not in STOPWORDS and real_word(w))
    return [w for w, _ in freq.most_common(n)]


def title_for(page, curated):
    """Curated title if we have one, else a topic label from the page's own keywords."""
    key = f"{page['book']}|{page['p']}"
    if key in curated:
        return curated[key], False
    kws = page["kw"][:3]
    return (" · ".join(w.capitalize() for w in kws) or f"{page['book']} page {page['p']}"), True


# ---------------------------------------------------------------- 8. concepts
def attach_concepts(pages, concepts):
    """Re-tag pages with the hand-written concept explainers by matching their terms."""
    for p in pages:
        p["concepts"], p["learn"] = [], ""
    for cid, c in concepts.items():
        needles = [c["name"].lower()] + [t.lower() for t in c.get("match", [])]
        blob = " ".join([c["name"], c["one_line"], c["definition"],
                         " ".join(c["examples"]), c["why_it_matters"],
                         " ".join(c["related"]), c.get("search_terms", "")])
        pins = set(c.get("pin", []))
        pin_only = c.get("pin_only", False)
        hits = []
        for p in pages:
            hay = (p["title"] + " " + p["text"]).lower()
            hit = p["id"] in pins or (not pin_only and any(n in hay for n in needles if len(n) > 3))
            if hit:
                p["concepts"].append(cid)
                p["learn"] += " " + blob
                hits.append(p["id"])
        c["pages"] = hits
    return concepts


# ---------------------------------------------------------------- pipeline
def process_binder(pdf, book, prefix, workdir, limit=None):
    raw = os.path.join(workdir, f"raw_{prefix}")
    out = os.path.join(workdir, f"clean_{prefix}")
    os.makedirs(out, exist_ok=True)
    files = extract_pages(pdf, raw)
    if limit:
        files = files[:limit]

    pages = []
    for n, src in enumerate(files, 1):
        pid = f"{prefix}-{n:03d}"
        dst = os.path.join(out, f"{pid}.jpg")
        if not deskew_and_crop(src, dst):
            shutil.copy(src, dst)          # keep the page even if deskew failed
        strip_footers(dst)
        fix_rotation(dst)
        text = clean_text(ocr_page(dst))
        pages.append({"id": pid, "book": book, "p": n, "text": text, "img": dst})
        print(f"   {pid}  {len(text):5d} chars", flush=True)
    return pages


def build(args):
    work = args.work
    os.makedirs(work, exist_ok=True)

    print("1/6  reading PDFs, deskewing, removing footers, fixing rotation, OCR")
    pages  = process_binder(args.hawaii, "Hawaii",    "HI", work, args.limit)
    pages += process_binder(args.vegas,  "Las Vegas", "LV", work, args.limit)

    print("2/6  keywords")
    for p in pages:
        p["kw"] = keywords_for(p["text"])

    print("3/6  titles")
    curated = {}
    if args.titles and os.path.exists(args.titles):
        curated = json.load(open(args.titles))
        print(f"     using {len(curated)} curated titles from {args.titles}")
    for p in pages:
        p["title"], p["auto"] = title_for(p, curated)

    print("4/6  duplicate detection")
    gmap = find_duplicates(pages)
    for i, p in enumerate(pages):
        p["g"] = gmap.get(i, 0)
    ngroups = len(set(gmap.values()))
    cross = sum(1 for g in set(gmap.values())
                if len({pages[i]["book"] for i, gg in gmap.items() if gg == g}) > 1)
    print(f"     {ngroups} duplicate groups ({cross} span both binders)")

    print("5/6  numbering (Hawaii first, then Las Vegas)")
    order = sorted(pages, key=lambda e: (0 if e["book"] == "Hawaii" else 1, e["p"]))
    for i, p in enumerate(order, 1):
        p["num"] = i
    print(f"     pages 1-{len(order)}")

    print("6/6  concepts, images, data.js")
    concepts = {}
    if args.concepts and os.path.exists(args.concepts):
        concepts = attach_concepts(pages, json.load(open(args.concepts)))

    site = args.site
    for sub in ("thumbs", "pages"):
        d = os.path.join(site, sub)
        shutil.rmtree(d, ignore_errors=True); os.makedirs(d, exist_ok=True)

    for p in pages:
        im = Image.open(p["img"]).convert("RGB")
        w = im.copy(); w.thumbnail((WEB_PX, WEB_PX))
        w.save(os.path.join(site, "pages", p["id"] + ".jpg"), quality=82, optimize=True)
        t = im.copy(); t.thumbnail((THUMB_PX, THUMB_PX))
        t.save(os.path.join(site, "thumbs", p["id"] + ".jpg"), quality=78, optimize=True)

    records = [{k: v for k, v in p.items() if k != "img"} for p in pages]
    with open(os.path.join(site, "data.js"), "w") as f:
        f.write("window.BINDER=" + json.dumps(records, ensure_ascii=False) + ";\n")
        f.write("window.CONCEPTS=" + json.dumps(concepts, ensure_ascii=False) + ";\n")
    json.dump(records, open(os.path.join(site, "combined.json"), "w"), ensure_ascii=False)

    # single-file phone build: same code, images inlined
    index = os.path.join(site, "index.htm")
    if not os.path.exists(index):
        index = os.path.join(site, "index.html")
    if os.path.exists(index):
        def enc(path, px, q):
            im = Image.open(path).convert("L"); im.thumbnail((px, px))
            b = io.BytesIO(); im.save(b, "JPEG", quality=q, optimize=True, progressive=True)
            return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()
        T = {p["id"]: enc(p["img"], PHONE_THUMB_PX, 66) for p in pages}
        P = {p["id"]: enc(p["img"], PHONE_PAGE_PX, 56) for p in pages}
        html = open(index).read()
        html = re.sub(r'<script src="data\.js[^"]*"></script>',
                      "<script>\nwindow.BINDER=" + json.dumps(records, ensure_ascii=False) + ";\n"
                      "window.CONCEPTS=" + json.dumps(concepts, ensure_ascii=False) + ";\n"
                      "window.THUMB=" + json.dumps(T) + ";\n"
                      "window.PAGEIMG=" + json.dumps(P) + ";\n</script>", html, count=1)
        open(os.path.join(site, "binders_combined.html"), "w").write(html)

    print(f"\nDone. {len(pages)} pages -> {site}/data.js, thumbs/, pages/, binders_combined.html")
    print("index.htm was NOT modified: all site features are unchanged.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hawaii", required=True, help="Hawaii PDF")
    ap.add_argument("--vegas",  required=True, help="Las Vegas PDF")
    ap.add_argument("--site",   default="sitehtm", help="site folder holding index.htm")
    ap.add_argument("--work",   default="_work",   help="scratch folder")
    ap.add_argument("--titles",   default="titles.json",   help="curated titles to keep")
    ap.add_argument("--concepts", default="concepts.json", help="hand-written explainers")
    ap.add_argument("--limit", type=int, help="only process the first N pages of each PDF (testing)")
    build(ap.parse_args())
