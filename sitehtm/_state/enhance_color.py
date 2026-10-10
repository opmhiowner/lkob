#!/usr/bin/env python3
"""Color-preserving readability pass. For pages whose color source shows real color,
re-render the site page keeping chroma: CLAHE + unsharp on the LAB L channel only
(text-heavy pages) or autocontrast + light sharpen (photo pages). Pages that are
effectively monochrome keep their existing grayscale-enhanced image (higher res /
better compression, looks identical). Resumable via _work/color_done.txt.
    python3 enhance_color.py <budget>"""
import os, sys, json
import cv2
import numpy as np
from PIL import Image, ImageOps, ImageEnhance

SITE = "sitehtm"
DONE_F = "_work/color_done.txt"
COLOR_FRAC = 0.010          # >=1% clearly-chromatic pixels => color page
budget = int(sys.argv[1]) if len(sys.argv) > 1 else 60

pages = {p["id"]: p for p in map(json.loads, open("_work/pages.jsonl"))}
srcmap = json.load(open("_work/colorsrc.json"))
done = set(open(DONE_F).read().split()) if os.path.exists(DONE_F) else set()
todo = [i for i in sorted(pages) if i not in done]
print(f"{len(pages)} pages, {len(done)} done, {len(todo)} to go; doing up to {budget}", flush=True)

def color_fraction(bgr):
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    a = lab[:, :, 1].astype(np.int16) - 128
    b = lab[:, :, 2].astype(np.int16) - 128
    chroma = np.abs(a) + np.abs(b)
    return float((chroma > 18).mean())

def enhance_text_lab(bgr):
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    L = lab[:, :, 0]
    L = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(16, 16)).apply(L)
    blur = cv2.GaussianBlur(L, (0, 0), 2.0)
    L = cv2.addWeighted(L, 1.6, blur, -0.6, 0)
    L = cv2.normalize(L, None, 0, 255, cv2.NORM_MINMAX)
    lab[:, :, 0] = L
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

n = changed = 0
with open(DONE_F, "a") as df:
    for pid in todo:
        if n >= budget:
            break
        kind, src = srcmap[pid]
        img = cv2.imread(src)
        if img is None:
            df.write(pid + "\n"); n += 1; continue
        frac = color_fraction(img)
        if frac >= COLOR_FRAC:
            if len(pages[pid]["text"]) > 400:               # colorful text page
                out = enhance_text_lab(img); q = 90
            else:                                            # colorful photo/diagram
                pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
                pil = ImageOps.autocontrast(pil, cutoff=1)
                pil = ImageEnhance.Sharpness(pil).enhance(1.4)
                out = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR); q = 85
            dst = os.path.join(SITE, "pages", pid + ".jpg")
            cv2.imwrite(dst, out, [cv2.IMWRITE_JPEG_QUALITY, q, cv2.IMWRITE_JPEG_OPTIMIZE, 1])
            t = Image.open(dst); t.thumbnail((320, 320))
            t.save(os.path.join(SITE, "thumbs", pid + ".jpg"), quality=80, optimize=True)
            changed += 1
            print(f"   {pid} color {frac:.3f} ({kind}, {'text' if len(pages[pid]['text'])>400 else 'photo'})", flush=True)
        # else: monochrome page — keep existing enhanced image
        df.write(pid + "\n"); df.flush()
        n += 1
print(f"this run: {n} checked, {changed} re-rendered in color; total {len(done)+n}/{len(pages)}", flush=True)
