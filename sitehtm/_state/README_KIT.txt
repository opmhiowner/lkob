LKO BUILD KIT — lets a fresh Claude session rebuild "LKO 1" without re-OCR.
Needs: this kit + the original scans zip (12252025_..._2025_3_PILLAR_JOBS.zip, 415 PDFs).
Steps (all scripts expect to run from a folder containing sitehtm/ and _work/):
 1. unzip scans to /home/claude/lko_src ; put kit's *.py/*.json/*.jsonl in _work/ ; sitehtm/ from kit.
 2. python3 _work/rasterize.py            (pdftoppm -r 200 -> _work/raw_Dnnn/)   ~10 min
 3. python3 _work/clean.py 90  repeatedly until "CLEAN DONE"  (deskew + stamps -> pages/) ~70 min
    (run in budgeted batches with timeout 110; background jobs die when the session idles)
 4. python3 _work/assemble_lko.py ; python3 _work/images_lko.py
 5. zip -0 sitehtm -> split -b 19m -> SendUserFile + device_commit_files to the linked folder.
See sitehtm/_state/HANDOFF.md for the full project description. NEVER re-run OCR (pages.jsonl).
