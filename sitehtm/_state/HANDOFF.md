# LKO binder — build 1 (preview) — HANDOFF

Fourth Oishi archive app, built on the OPM 8 framework (index.htm), recolored ORANGE
(--orange #e8731a, --orange-dk #b8540e, --amber #ff9a3c, --amber-wash #fff4ea; logo fill #f57c1f;
apple-touch-icon recolored). Working name "LKO binder" — real name/tagline TBD.

SOURCE: ScanSnap folder "2025 3 PILLAR JOBS" — 415 PDFs, 1,440 pages, no embedded text.
_state/manifest.json maps D001..D415 -> original PDF filename + page count.
_state/idmap_lko.json maps PG-nnnn -> Dnnn-ppp (source doc/page). Never re-OCR: _state/pages.jsonl.

PIPELINE (scripts in _state/; run from a folder containing sitehtm/ with these files in _work/):
  pdftoppm -r 200 -jpeg per PDF -> _work/raw_Dnnn/   (never pdfimages)
  OCR: rotation check + Tesseract (psm 3, oem 1) -> _work/pages.jsonl   [DONE, 1,440]
  clean.py      : deskew/crop + upright footer-stamp removal -> pages/   [DONE]
  assemble_lko.py: order, dup groups, titles, data.js/combined.json/titles.json
  images_lko.py : 2400px pages/ + 320px thumbs/
  Optional: enhance.py (CLAHE) — NOT yet run for LKO.
  NO single-file phone build (1,440 pages would be ~300MB); hosted multi-file site only.
  Background jobs die when the session idles — run every stage in budgeted batches (timeout 110).

DUPLICATES (nothing deleted): _state/dup_review.json = 63 doc-level groups (46 same, 17 partial)
from TF-IDF cosine >=0.55 + page-level >=0.70. Keep copy = best OCR readability (partial groups:
most pages first). Keep pages carry keep:true; other copies map page-to-page (sim >=0.45) into
groups (g) and are hidden from Everything by default, shown in the Duplicates tab. Pages in
duplicate docs with no matching page in the keep copy stay visible. Overrides file:
_work/dup_overrides.json {"overrides":{"7":"D143"},"keep_all":["5"]}.
36 pages also exist in OPM 8 (dup_review.json "opm_overlap"); kept as ordinary pages.

SANCTIONED EDITS to index.htm beyond recolor: Duplicates tab restored in tabDefs (shows when
groups exist); primary-copy rule honors byId[i].keep; titles/app name -> LKO.

BUILD 1 STATE: pages in scan (document) order, PG-0001..PG-1440; titles are AUTO placeholders
(first clean words of page 1 per document + "(p/n)"); CONCEPTS = {} (none yet).

NEXT: heading-based titles; topic clustering -> ~30-40 concept groups for approval ->
curriculum order + renumber (_work/doc_order.json drives assemble_lko.py); enhance pass;
service worker; real name/tagline.
