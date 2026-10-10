#!/usr/bin/env python3
"""Re-render site page images for readability. Resumable: skips ids in _work/enhanced.txt.

Text-heavy pages (OCR > 400 chars): grayscale, CLAHE contrast normalization, unsharp
mask — crisp black-on-white type at full native resolution (no downscale).
Photo/diagram pages: kept in color with mild autocontrast + light sharpening.
Thumbnails are regenerated from the enhanced page.
    python3 enhance.py <budget>
"""
import os, sys, json
import cv2
import numpy as np
from PIL import Image, ImageOps, ImageEnhance

SITE = "sitehtm"
DONE_F = "_work/enhanced.txt"
budget = int(sys.argv[1]) if len(sys.argv) > 1 else 40

pages = [json.loads(l) for l in open("_work/pages.jsonl") if l.strip()]
done = set(open(DONE_F).read().split()) if os.path.exists(DONE_F) else set()
todo = [p for p in pages if p["id"] not in done]
print(f"{len(pages)} pages, {len(done)} enhanced, {len(todo)} to go; doing up to {budget}", flush=True)

def enhance_text(img_bgr):
    g = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    g = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(16, 16)).apply(g)
    blur = cv2.GaussianBlur(g, (0, 0), 2.0)
    sharp = cv2.addWeighted(g, 1.6, blur, -0.6, 0)          # unsharp mask
    # normalize paper to near-white without clipping ink
    sharp = cv2.normalize(sharp, None, 0, 255, cv2.NORM_MINMAX)
    return cv2.cvtColor(sharp, cv2.COLOR_GRAY2BGR)

n = 0
with open(DONE_F, "a") as df:
    for p in todo:
        if n >= budget:
            break
        src = p["img"]
        img = cv2.imread(src)
        if img is None:
            df.write(p["id"] + "\n"); continue
        if len(p["text"]) > 400:                            # typed/text page
            img = enhance_text(img)
            q = 90
        else:                                               # photo, diagram, blank
            pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            pil = ImageOps.autocontrast(pil, cutoff=1)
            pil = ImageEnhance.Sharpness(pil).enhance(1.4)
            img = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
            q = 85
        # full native resolution — no downscale
        cv2.imwrite(os.path.join(SITE, "pages", p["id"] + ".jpg"), img,
                    [cv2.IMWRITE_JPEG_QUALITY, q, cv2.IMWRITE_JPEG_OPTIMIZE, 1])
        t = Image.open(os.path.join(SITE, "pages", p["id"] + ".jpg"))
        t.thumbnail((320, 320))
        t.save(os.path.join(SITE, "thumbs", p["id"] + ".jpg"), quality=80, optimize=True)
        df.write(p["id"] + "\n"); df.flush()
        n += 1
print(f"enhanced this run: {n}; total {len(done)+n}/{len(pages)}", flush=True)
