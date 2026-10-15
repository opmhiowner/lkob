#!/usr/bin/env python3
"""Rename pages/ and thumbs/ files from LKO 1 numbering to LKO 2 numbering, in place, on the computer that holds them.
Run from the folder that contains pages/ and thumbs/:  python3 renumber_images.py idmap_lko1.json idmap_lko.json
Then set _state/images.json to {"numbering": "lko2"}, rebuild, and upload the renamed folders."""
import json, os, sys
old = json.load(open(sys.argv[1])); new = json.load(open(sys.argv[2]))
old_of = {v: k for k, v in old.items()}                  # Dnnn-ppp -> old PG
plan = [(old_of[src], pg) for pg, src in new.items()]    # (old PG, new PG)
for folder in ("pages", "thumbs"):
    tmp = {}
    for o, n in plan:                                    # two passes so a swap never overwrites
        if os.path.exists(f"{folder}/{o}.jpg"): os.rename(f"{folder}/{o}.jpg", f"{folder}/{o}.tmp"); tmp[o] = n
    for o, n in tmp.items(): os.rename(f"{folder}/{o}.tmp", f"{folder}/{n}.jpg")
    print(folder, len(tmp), "files renamed")
