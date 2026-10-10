# DEPLOY.md — GitHub → Bluehost for OPM LKO, one command at a time

Hosted address: `https://oishis.net/iservices/lvhi/lkobinder/index.htm`
Hosted folder: `public_html/iservices/lvhi/lkobinder/` (holds the CONTENTS of `sitehtm/`, not the folder itself).

Two things travel separately:

| what | how it gets to Bluehost |
|---|---|
| the app: `index.htm`, `data.js`, `titles.json`, `concepts.json`, `apple-touch-icon.png` | through git (Part B or Part C) |
| the page images: `pages/` (~620 MB) and `thumbs/` (~24 MB) | once, by zip or SFTP (Part D) — they are not in git |

---

## Part A — GitHub (done from any computer with git)

A1. Get the repository.
```
git clone https://github.com/opmhiowner/lkob.git
cd lkob
```

A2. See the branches. The Claude branch holds the build; `main` is what Bluehost will deploy.
```
git fetch origin
git branch -r
```

A3. Make `main` from the Claude branch (first time only; the repository started empty).
```
git checkout -b main origin/claude/peaceful-feynman-7o9pmm
git push -u origin main
```
Then on github.com: **Settings → General → Default branch → main** (the pencil icon), Update.

A4. Every later release arrives as a pull request from a `claude/…` branch. Merge it on github.com
(**Pull requests → the PR → Merge pull request**), then on your computer:
```
git checkout main
git pull origin main
```

---

## Part B — Bluehost by cPanel "Git Version Control" (recommended: no passwords typed anywhere)

B1. Log in to Bluehost → **Advanced** (cPanel) → **Files → Git™ Version Control**.

B2. Click **Create**. Fill in:
- Clone a Repository: **ON**
- Clone URL: `https://github.com/opmhiowner/lkob.git`
- Repository Path: `repos/lkob` (cPanel fills in the rest of the path itself)
- Repository Name: `lkob`
Click **Create**. (The repository is public, so no SSH key is needed.)

B3. Nothing to edit: `.cpanel.yml` uses the account's own home folder (`$HOME`), so it needs no user name.

B4. Back in cPanel → Git Version Control → **Manage** (next to `lkob`) → tab **Pull or Deploy**:
1. **Update from Remote** (pulls `main`)
2. **Deploy HEAD Commit** (runs the tasks in `.cpanel.yml`: copies `sitehtm/` contents into `public_html/iservices/lvhi/lkobinder/`)

B5. Repeat B4 after every merge to `main`. That is the whole release.

---

## Part C — Bluehost by SSH instead (if you prefer a terminal)

C1. cPanel → **Security → SSH Access → Manage SSH Keys → Generate a New Key** → then **Manage → Authorize**.
Download the private key, or paste your own public key under **Import Key**.

C2. From your computer (host name and port are on the SSH Access page; Bluehost uses port 22):
```
ssh CPANEL_USER@your-server-host
```

C3. First time on the server:
```
mkdir -p ~/repos && cd ~/repos
git clone https://github.com/opmhiowner/lkob.git
mkdir -p ~/public_html/iservices/lvhi/lkobinder
```

C4. Every release:
```
cd ~/repos/lkob && git pull origin main
cp -R sitehtm/. ~/public_html/iservices/lvhi/lkobinder/
rm -rf ~/public_html/iservices/lvhi/lkobinder/_state ~/public_html/iservices/lvhi/lkobinder/rebuild.py ~/public_html/iservices/lvhi/lkobinder/combined.json
```

---

## Part D — the page images (once, and again only when images change)

The images come out of the pipeline on the build computer (`images_lko.py` writes `sitehtm/pages/` and `sitehtm/thumbs/`).

D1. Make three zips on the build computer, inside `sitehtm/` (cPanel's uploader stops at 500 MB, so pages are split):
```
cd sitehtm
zip -0 -r ../thumbs.zip thumbs
cd pages
ls PG-0001.jpg PG-0720.jpg PG-0721.jpg PG-1440.jpg
zip -0 ../../pages_1.zip PG-0[0-6]??.jpg PG-07[01]?.jpg PG-0720.jpg
zip -0 ../../pages_2.zip PG-072[1-9].jpg PG-07[3-9]?.jpg PG-0[89]??.jpg PG-1???.jpg
cd ../..
ls -la thumbs.zip pages_1.zip pages_2.zip
```
Check the counts before uploading (720 + 720 = 1,440):
```
unzip -l pages_1.zip | tail -1
unzip -l pages_2.zip | tail -1
```

D2. cPanel → **Files → File Manager** → go to `public_html/iservices/lvhi/lkobinder/`:
- **Upload** `thumbs.zip` → select it → **Extract** (makes `thumbs/`)
- make a folder `pages` (**+ Folder**), open it, **Upload** `pages_1.zip`, **Extract**; then `pages_2.zip`, **Extract**
- delete the three zips afterwards (**Delete**) so they do not count against disk space.

D3. Or by SFTP from the build computer, no size limit (FileZilla: host = the SSH host, port 22, protocol SFTP), or from a terminal:
```
scp -r sitehtm/thumbs sitehtm/pages CPANEL_USER@your-server-host:~/public_html/iservices/lvhi/lkobinder/
```

---

## Part E — check it is live

```
curl -I https://oishis.net/iservices/lvhi/lkobinder/index.htm
curl -I https://oishis.net/iservices/lvhi/lkobinder/data.js
curl -I https://oishis.net/iservices/lvhi/lkobinder/thumbs/PG-0001.jpg
curl -I https://oishis.net/iservices/lvhi/lkobinder/pages/PG-1440.jpg
```
Each line should answer `HTTP/2 200`. A `404` on the first line usually means the files landed one level deep
(`lkobinder/sitehtm/index.htm`): move the contents of `sitehtm` up one level in File Manager.

Then on an iPhone: Safari → the address → Share → **Add to Home Screen** → it installs as **OPM LKO**.

---

## Part F — every later build (the framework's rule)

Before a build is committed, bump the cache stamp in `sitehtm/index.htm` (the `data.js?v=` value, line ~464), or
phones that installed the icon keep showing the previous `data.js`. When a `sw.js` service worker is added,
bump its `VERSION` too.
