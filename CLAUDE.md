# CLAUDE.md — OPM LKO (opmhiowner/lkob)

Handoff for Claude Code sessions. Read fully before changing anything. Written 2026-10-09 from the chat that built LKO 1.

## What this app is

**OPM LKO** is the fourth Oishi's scanned-binder archive app, built on the OPM 8 framework (same `index.htm` family as OPM, the Binders archive and OPM Recitals): a static, phone-first website of 1,440 scanned pages with full-text search, page/range lookup, a page viewer, a Duplicates tab, an Add-scan tab, and iPhone home-screen installability. No backend, no build step at runtime — the browser loads `index.htm` + `data.js` and lazy-loads JPEGs.

- Source: ScanSnap folder "2025 3 PILLAR JOBS" — 415 PDFs, 1,440 pages, no embedded text (all OCR'd).
- Theme: **brown** (`--brown #8b5a2b`, `--brown-dk #5c3a1a`, `--tan #c49a6c`, `--tan-wash #f7f1ea`; logo fill `#7a4a22`; `apple-touch-icon.png` recolored to match).
- Names: browser title and iPhone home-screen label = **"OPM LKO"**. On-page heading = **"LKO"** with tagline "(LKO binder)". No dark company site-nav bar (logo band only, like OPM Recitals).
- Target hosting: Bluehost shared, `public_html/iservices/lvhi/lkobinder/` → `https://oishis.net/iservices/lvhi/lkobinder/index.htm`. (OPM lives beside it at `…/lvhi/opm/`.) Site folder on disk is `sitehtm/`; the hosted folder holds its *contents*, not the folder itself.
- Current release: **LKO 1 (preview)** — searchable, duplicates grouped, but auto titles and no concept groups yet (see Open items).

## Non-negotiable working rules (owner's standing protocol)

1. **Never push without explicit approval.** Post the review package (file list, diff summary, commit message, expected result) and wait for the literal word "push". Claude Code tasks push only to their own `claude/…` branch; `main` is updated by a GitHub pull request the owner merges.
2. **Never re-OCR existing pages.** `_state/pages.jsonl` is the checkpoint (1,440 records). Re-running OCR costs ~2 hours and changes search text; everything downstream reads this file.
3. **Never use `pdfimages`.** Rasterize with `pdftoppm -r 200 -jpeg` only (pdfimages dumps embedded objects, not pages).
4. **`index.htm` is shared framework code.** Only "sanctioned edits" (listed below) — no refactors, no re-layout. Desktop layout is approved; phone-only changes go inside the `max-width:700px` media block.
5. **Nothing is deleted from the archive.** Duplicates are *grouped and hidden*, never removed (owner's decision, differs from OPM 8 where surplus copies were deleted).
6. No generative-AI image restoration — OpenCV/Pillow only (CLAHE, unsharp, Lanczos). Generative tools hallucinate text on scanned business records.
7. Give time estimates and finish times in **HST and PST**. Before any build or zip, post diagnosis / fix description / time and wait for "start".
8. Deliverables are named `OPM LKO <n>` (zip or folder) with the version in the name; verify from inside the zip before delivery.

## Repository layout

| Path | Role |
|---|---|
| `sitehtm/index.htm` | The app (vanilla JS, single file, ~93 KB). Reads `window.BINDER` and `window.CONCEPTS` from `data.js`. |
| `sitehtm/data.js` | Search index: one record per page — `id` (PG-0001…), `num`, `title`, `text` (OCR), `kw`, `g` (dup group id), `keep` (true on the primary copy of a dup group), `src_id` (source doc/page, e.g. D288-005), `src_pdf`, `concepts`. ~3.4 MB. `combined.json` is the same array as JSON. |
| `sitehtm/titles.json` | `"Binder|<num>": "<title>"` — curated titles override auto titles at assembly. Currently all auto. |
| `sitehtm/concepts.json` | Concept groups (`{id: {name, pages, one_line, definition, examples, why_it_matters, related, search_terms, match, pin}}`). **Absent for LKO 1** — `_state/opm_concepts_reference.json` is OPM's 33-group file as a format reference. |
| `sitehtm/pages/PG-nnnn.jpg` | 2400 px page images (q82). 1,440 files, ~620 MB. |
| `sitehtm/thumbs/PG-nnnn.jpg` | 320 px thumbnails (q78), ~24 MB. |
| `sitehtm/apple-touch-icon.png` | 180 px brown home-screen icon. |
| `sitehtm/rebuild.py` | OPM's original pipeline library — `deskew_and_crop`, `_footer_pass`/`strip_footers`, `fix_rotation`, `ocr_page`, `clean_text`, `find_duplicates`, `keywords_for`, `title_for`, `attach_concepts`. Imported by the LKO scripts; not run directly. |
| `sitehtm/_state/HANDOFF.md` | Build-level handoff (pipeline detail). |
| `sitehtm/_state/pages.jsonl` | **OCR checkpoint** — `{id: Dnnn-ppp, doc, src, p, np, text, img, rot}` per page. |
| `sitehtm/_state/manifest.json` | D001…D415 → original PDF filename + page count. |
| `sitehtm/_state/idmap_lko.json` | PG-nnnn → Dnnn-ppp traceability. |
| `sitehtm/_state/dup_review.json` | 63 document-level duplicate groups (46 identical, 17 partial/overlap) + 36 pages that also exist in OPM 8 (`opm_overlap`). |
| `sitehtm/_state/*.py` | `rasterize.py`, `ocr_fast.py`, `clean.py`, `assemble_lko.py`, `images_lko.py`, plus OPM's `enhance.py` / `enhance_color.py` (not yet run for LKO). |

## Pipeline (how a build is produced)

All scripts expect to run from a working folder containing `sitehtm/` and `_work/` (copy the `_state` scripts/JSON into `_work/`). Source PDFs unzipped to `/home/claude/lko_src/`.

1. `python3 _work/rasterize.py` — pdftoppm 200 dpi → `_work/raw_Dnnn/pg-N.jpg` (~10 min, 2.3 GB).
2. `ocr_fast.py` — **done; do not rerun.** Rotation check (`fix_rotation`) + Tesseract `--psm 3 --oem 1` at 1500 px → `pages.jsonl`.
3. `python3 _work/clean.py 90` — repeat until it prints `CLEAN DONE`: `deskew_and_crop` + upright `_footer_pass` (whitens the printer's file-path/date stamps; 3,080 removed) → `pages/Dnnn-ppp.jpg`. ~70 min. Resumable via `_work/clean_done.txt`. The sideways (rotated) footer passes are deliberately off — they never found anything on ScanSnap pages and tripled the runtime.
4. `python3 _work/assemble_lko.py` — orders documents (scan order, or `_work/doc_order.json` if present), builds dup groups from `dup_review.json` (+ optional `_work/dup_overrides.json` `{"overrides":{"7":"D143"},"keep_all":["5"]}`), applies `_work/doc_titles.json` if present else auto titles, renumbers PG-0001…, writes `data.js`, `combined.json`, `titles.json`, `_state/idmap_lko.json`, `_work/imgmap.json`.
5. `python3 _work/images_lko.py` — 2400 px pages + 320 px thumbs into `sitehtm/`.
6. Optional `enhance.py` (CLAHE, native res; color pages via `enhance_color.py` LAB-L) — OPM ran it, LKO hasn't.

Operational gotchas: background jobs (`nohup`/`setsid`) die when the chat session idles — run every long stage in budgeted foreground batches (`timeout 110 python3 … 90`). Tool calls cap at ~2 minutes. Dense 4,000-char pages take 3–4× longer than average.

## Duplicate model (how the Duplicates tab works)

- Document-level: TF-IDF (1–2-grams, words ≥3 letters) cosine ≥ 0.55 between whole PDFs, plus page-level ≥ 0.70 across different PDFs, union-find → 63 groups.
- Keep copy per group: best OCR readability score (fraction of real-looking words); for partial groups, most pages first. Keep pages carry `keep:true`.
- Other copies are mapped page-to-page to the keep copy (page sim ≥ 0.45) and share its `g`. `index.htm` hides non-primary group members from Everything (`isSurplus`), lists each group side-by-side in the Duplicates tab, and shows "Copies of this page" in the viewer. "Show duplicates" toggle reveals them inline.
- Result in LKO 1: 1,155 pages visible, 285 hidden copies in 217 page-groups. 62 pages inside duplicate PDFs had no matching page in the keep copy and stay visible.
- A review page with thumbnails (`LKO_duplicate_review.html`) and a tap-to-pick tool (`LKO_keep_picker.html`) exist from the Sept 18 chat; the owner chose "keep originals as main, all duplicates in their own tab" without overrides.

## Sanctioned edits to `index.htm` (beyond OPM 8)

1. Color tokens renamed/recolored to brown (`--brown`, `--brown-dk`, `--tan`, `--tan-wash`); logo `<path fill>` and `apple-touch-icon.png` recolored.
2. `<title>` and `apple-mobile-web-app-title` → "OPM LKO"; `<h1>` "LKO"; tagline "(LKO binder · LKO <version>)" — the tagline carries the release number since 2.2 (owner's ask, 2026-10-15) so the live build can be read off the page; every release updates it together with the `data.js?v=` stamp.
3. `tabDefs()` adds `['dup','Duplicates', n]` when any groups exist (OPM 8 had removed the tab after deleting its copies).
4. Primary-copy rule: `ids.find(i => byId[i].keep) || …` before OPM's old `LV-` / lowest-id fallback.
5. `brandbar`/`sitenav` block removed from `<header>` (logo band only).
6. Page-number regexes `\d{1,3}` → `\d{1,4}` (three places) so four-digit pages and ranges work (2026-10-12).

Everything else (search, ranges, typo-tolerant fallback, TOC, viewer arrows, concept scoping, Add-scan/IndexedDB, negative-sticky phone header) is unchanged OPM 8 code — see `_state/HANDOFF.md` from OPM 8 for the full feature list if needed.

## Deployment

- **Bluehost (current target):** manual cPanel File Manager upload (the Bluehost apps are no longer git-deployed; DIR went back to manual on 2026-09-04). cPanel caps single uploads at 500 MB, so ship as three zips — `LKO_site.zip` (everything except `pages/`), `pages_1.zip` (PG-0001–0720), `pages_2.zip` (PG-0721–1440) — and extract each in place (`pages_*.zip` inside the `pages` folder). Or FileZilla (no limit).
- **If a GitHub Actions FTPS deploy is wanted:** `.github/workflows/deploy.yml` with `SamKirkland/FTP-Deploy-Action`, `local-dir: sitehtm/`, `server-dir: public_html/iservices/lvhi/lkobinder/`, secrets `FTP_SERVER / FTP_USERNAME / FTP_PASSWORD` (a jailed `deploy@oishis.net` account existed for DIR; its secrets were deleted from the `dir` repo — Chris must re-add). Expect 20–30 min per run for 1,440 files; GitHub warns near 1 GB repo size. Add `.gitattributes` is not needed (no LFS) but keep raw rasters (`_work/raw_*`) and `lko_src/` out of the repo (`.gitignore`).
- After any `data.js` change on the hosted site, bump the `data.js?v=` stamp in `index.htm` (iOS home-screen cache is isolated from Safari's). If a service worker is added later, bump its `VERSION` too (OPM rule).
- Staff install: open the URL in iOS Safari → Share → Add to Home Screen → appears as "OPM LKO".

## Open items (state as of 2026-10-09)

1. **Hosting not confirmed live.** A first upload went to a HostMonster cPanel (`host2150.hostmonster.com`) and `…/lvhi/lkobinder/index.htm` returns Not Found — likely the wrong account or the zip extracted one level deep (`lkobinder/sitehtm/`). Verify in Bluehost cPanel → `public_html/iservices/lvhi/`.
2. **Titles are auto placeholders** (first clean words of each document's page 1 + "(p/n)"); many read like OCR noise. Plan: heading pass — Tesseract `image_to_data` on page 1 of each of the 415 documents, take the tallest text line as the title → `_work/doc_titles.json` → re-run assemble (no image work needed).
3. **No concept groups.** Plan: cluster documents by topic from OCR text → propose ~30–40 named groups for owner approval → `concepts.json` with `pin` lists → `_work/doc_order.json` for curriculum order → renumber into contiguous ranges (OPM convention: every group is a contiguous page range; teachers assign ranges). Renumbering is fine; `idmap_lko.json` keeps traceability.
4. Enhance pass (CLAHE) not yet run; 30 pages have <50 chars of OCR (likely diagrams/blank backs) — flag, don't delete.
5. Service worker (offline + background self-update, as OPM 12 has) not yet added.
6. The 36 pages overlapping OPM 8 are kept as ordinary pages; owner may want an "also in OPM" flag later.
7. Owner's rejected variants, do not reintroduce: orange theme (replaced by brown), "OPM LKO" as the on-page heading (heading stays "LKO"), the dark site-nav bar.

## LKO 2 build (2026-10-10): the FRAMEWORK way

The owner's rule from `FRAMEWORK.md` (OPM app framework): **the app is only the framework; everything that is LKO lives in the data.** So:

- `sitehtm/_state/build_lko2.py` (run from the build folder: `python3 sitehtm/_state/build_lko2.py`) replaces `assemble_lko.py`. It reads the same checkpoints (`pages.jsonl`, `dup_review.json`, `manifest.json`), plus `_state/doc_groups.py` (every document D001-D415 in exactly one concept group, groups in teaching order) and `sitehtm/concepts.json` (the 26 group explainers), and writes `data.js` in the framework's exact page shape (`id book p num title text kw g concepts learn`; `g` is 0 when not a duplicate; `keep:true` is the one extra field, on the better copy of a duplicate - the LKO `index.htm` honours it, a stock framework `index.htm` ignores it and shows the lowest-numbered copy). Pages are renumbered PG-0001… in teaching order so every group is one contiguous range (the TOC rule); `_state/idmap_lko.json` keeps the trace back to the scan. `_work/doc_order.json` and `_work/doc_titles.json` are written too, so `assemble_lko.py` would reproduce the same order.
- Titles: the scan's own name (ScanSnap's first OCR line, cleaned) when it reads like words, else the kit's auto title. 252 of 415 come from the scan names. Curate in `_state/titles_curated.json` (`"D220": "Title"`), which wins at build time.
- Proof-read text: `_state/text_curated.json` (`"D220-001": "the page's words"`) replaces that page's OCR at build time; the checkpoint `pages.jsonl` is never edited. First entry 2026-10-15: D220-001 (Mark McCormack, "Mastering the art of the 5-minute conversation"), whose OCR read "vunversation" and took its title from an ad, so search could not find it. When a page cannot be found, this is the fix: transcribe it, add it here, rebuild, bump the stamp.
- The 26 groups are a **proposal for the owner's approval** (the kit's open item 3). Change membership in `_state/doc_groups.py`, the words in `concepts.json`, re-run the build. `to-be-identified` holds the 23 scans whose OCR is unreadable; nothing is deleted.
- Sanctioned edit 6 (owner's call, 2026-10-12): the three page-number regexes in `index.htm` (`plain` page lookup, the HI/LV lookup, `rangeOf`) read `\d{1,4}` instead of the framework's `\d{1,3}`, so pages 1000-1440 and TOC ranges past 999 work. Cache stamp `data.js?v=202610121`. Staff who had the icon on the home screen before this change delete and re-add it once (iOS caches the old `index.htm`).
- **Images on Bluehost are still numbered the LKO 1 way** (the September `pages/` and `thumbs/` were uploaded unchanged, 2026-10-15). `_state/images.json` says `"numbering": "lko1"`, so the build adds `window.PAGEIMG` / `window.THUMB` to `data.js`, mapping every LKO 2 page id to its LKO 1 file via `_state/idmap_lko1.json` (the framework's `index.htm` reads those maps before its default `pages/<id>.jpg`). Without that map every page shows the wrong picture (page 995 showed the Bolt article). To retire the map: rename the files on the computer that holds them with `_state/renumber_images.py idmap_lko1.json idmap_lko.json`, upload the renamed folders, set `images.json` to `lko2`, rebuild. Any future renumbering (a new teaching order) needs the same care: the images and `data.js` must agree.
- Deployment is in `DEPLOY.md` (GitHub -> Bluehost by cPanel Git Version Control, SSH, or the optional manual GitHub Action); `.cpanel.yml` holds the cPanel deploy tasks.

## Version line

LKO 1 (2026-09-18, orange, nav bar) → brown recolor + "OPM LKO" app name (2026-09-18) → nav bar removed, heading restored to "LKO" (2026-09-18) = LKO 1 → **LKO 2 (2026-10-10, framework build: 26 concept groups, curriculum numbering, scan-name titles) = current**. Next: owner's review of the groups and titles; images + hosting.
