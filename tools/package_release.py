#!/usr/bin/env python3
"""Build the release assets into dist/ (standard library only).

  python3 tools/package_release.py            # uses VERSION
  python3 tools/package_release.py --check    # build into a temp folder and verify, write nothing (CI)

Assets:
  LegacyTracker-<version>.zip               LegacyTracker/ folder, ready to drop into Interface/AddOns
  mission-control-web-<version>.zip         the static page (index.html, app.js, style.css, data/plan.example.js)
                                            ready for any static host; add your own data/plan.js from ./mc generate
  SHA256SUMS.txt                            checksums of both zips
"""
import argparse, hashlib, os, re, sys, tempfile, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import mc  # noqa: E402

ADDON_FILES = ["LegacyTracker.toc", "LegacyTracker.lua"]
WEB_FILES = ["index.html", "app.js", "style.css", "data/plan.example.js"]
FIXED_TIME = (2026, 1, 1, 0, 0, 0)  # stable zip timestamps, so the same tree gives the same bytes

WEB_README = """WoW Forever Legacy Mission Control {v}: static page

Upload this folder's contents to any static host (GitHub Pages, Cloudflare Pages,
ChatGPT Sites, Netlify, S3 ...) or open index.html directly. It shows the example
Alliance roster until you add your own data/plan.js:

  1. Get the repository (https://github.com/BradGroux/wow-forever-mission-control),
     describe your roster (./mc init) and run ./mc generate.
  2. Copy web/data/plan.js from your copy into data/ here (next to plan.example.js).

Progress is saved in each visitor's browser. Hosting guide:
https://github.com/BradGroux/wow-forever-mission-control/blob/main/docs/hosting.md
"""


def add(z, src, arc):
    info = zipfile.ZipInfo(arc, FIXED_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    with open(src, "rb") as fh:
        z.writestr(info, fh.read())


def build(out_dir, version):
    os.makedirs(out_dir, exist_ok=True)
    addon = os.path.join(out_dir, f"LegacyTracker-{version}.zip")
    with zipfile.ZipFile(addon, "w") as z:
        for f in ADDON_FILES:
            add(z, os.path.join(ROOT, "addon", "LegacyTracker", f), f"LegacyTracker/{f}")
    web = os.path.join(out_dir, f"mission-control-web-{version}.zip")
    with zipfile.ZipFile(web, "w") as z:
        for f in WEB_FILES:
            add(z, os.path.join(ROOT, "web", f), f"mission-control-web/{f}")
        info = zipfile.ZipInfo("mission-control-web/README.txt", FIXED_TIME)
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        z.writestr(info, WEB_README.format(v=version))
    sums = []
    for p in (addon, web):
        with open(p, "rb") as fh:
            sums.append(f"{hashlib.sha256(fh.read()).hexdigest()}  {os.path.basename(p)}")
    with open(os.path.join(out_dir, "SHA256SUMS.txt"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(sums) + "\n")
    return addon, web


def verify(addon, web, version):
    with zipfile.ZipFile(addon) as z:
        names = sorted(z.namelist())
        assert names == sorted(f"LegacyTracker/{f}" for f in ADDON_FILES), names
        toc = z.read("LegacyTracker/LegacyTracker.toc").decode("utf-8")
        assert re.search(rf"^## Version: {re.escape(version)}\s*$", toc, re.M), "toc version"
        assert "LegacyTracker.lua" in toc
    with zipfile.ZipFile(web) as z:
        names = set(z.namelist())
        for f in WEB_FILES:
            assert f"mission-control-web/{f}" in names, f
        assert not any(n.endswith("/data/plan.js") for n in names), "personal plan.js must not ship"
        plan = z.read("mission-control-web/data/plan.example.js").decode("utf-8")
        assert f'"release":"{version}"' in plan, "plan.example.js release does not match VERSION (run ./mc generate)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--out", default=os.path.join(ROOT, "dist"))
    a = ap.parse_args()
    probs = mc.version_problems()
    if probs:
        sys.exit("version problems:\n  " + "\n  ".join(probs))
    v = mc.release_version()
    if a.check:
        with tempfile.TemporaryDirectory() as t:
            verify(*build(t, v), v)
        print(f"package check ok: {v}")
        return 0
    addon, web = build(a.out, v)
    verify(addon, web, v)
    for p in (addon, web, os.path.join(a.out, "SHA256SUMS.txt")):
        print("wrote", os.path.relpath(p, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
