#!/usr/bin/env python3
"""Maintainer tool: find and verify Wowhead Forever IDs for entity names.

  python3 tools/wowhead_lookup.py "Ragefire Chasm" "Taming the Beast" ...
  python3 tools/wowhead_lookup.py --missing        # every linked name in data/ without an id
  python3 tools/wowhead_lookup.py --missing --write # add verified hits to data/wowhead.json

A hit counts only when the search result name matches exactly and the tooltip
endpoint (nether.wowhead.com/forever/tooltip/<type>/<id>) returns the same name.
Not used by CI; needs network.
"""
import json, os, sys, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TYPES = {1: "npc", 3: "item", 5: "quest", 6: "spell", 7: "zone", 13: "class", 14: "race", 15: "skill"}
NO_TOOLTIP = {"class", "race", "skill"}  # exact search hit is the check for these
UA = {"User-Agent": "Mozilla/5.0 (wow-forever-mission-control maintainer tool)"}


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def lookup(name, prefer=None):
    q = urllib.parse.quote(name)
    try:
        res = get(f"https://www.wowhead.com/forever/search/suggestions-template?q={q}").get("results", [])
    except Exception as e:  # noqa: BLE001
        return None, f"search failed: {e}"
    hits = [r for r in res if r.get("type") in TYPES and r.get("name", "").lower() == name.lower()]
    if prefer:
        hits.sort(key=lambda r: TYPES[r["type"]] != prefer)
    for r in hits:
        t = TYPES[r["type"]]
        if t in NO_TOOLTIP:
            return {"type": t, "id": r["id"]}, "ok"
        try:
            tip = get(f"https://nether.wowhead.com/forever/tooltip/{t}/{r['id']}")
        except Exception:  # noqa: BLE001
            continue
        if tip.get("name", "").lower() == name.lower():
            return {"type": t, "id": r["id"]}, "ok"
    return None, "no exact verified match"


def main(argv):
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    write = "--write" in argv
    names = [a for a in argv if not a.startswith("--")]
    if "--missing" in argv:
        import mc  # noqa: E402
        names += sorted(mc.missing_links())
    reg_path = os.path.join(ROOT, "data", "wowhead.json")
    reg = json.load(open(reg_path, encoding="utf-8"))
    found = 0
    for n in names:
        hit, why = lookup(n)
        print(f"{n}: {hit or why}")
        if hit:
            found += 1
            reg["ids"][n] = hit
        time.sleep(0.4)
    if write:
        reg["ids"] = dict(sorted(reg["ids"].items()))
        json.dump(reg, open(reg_path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        open(reg_path, "a").write("\n")
    print(f"{found}/{len(names)} verified")


if __name__ == "__main__":
    main(sys.argv[1:])
