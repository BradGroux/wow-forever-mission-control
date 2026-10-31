#!/usr/bin/env python3
"""WoW Forever Legacy Mission Control: one CLI for people and agents.

  ./mc init [--answers FILE] [--force]  setup interview, writes config/roster.json
  ./mc validate [--config F] [--strict]  check the roster (combos, four characters, craft coverage)
  ./mc generate [--config F]             write web/data/plan.js, build/plan.json, build/PLAN.md, canvas adapter
  ./mc plan [--config F]                 print the personalized plan (Markdown)
  ./mc level CHAR LEVEL [--rested R]     record a level by hand (CHAR = id or name)
  ./mc skill CHAR PROFESSION SKILL       record a profession skill by hand
  ./mc check ID [ID ...] [--off]         tick (or untick) checklist items by id
  ./mc progress merge FILE|-             merge an exported progress JSON (web "Export" button)
  ./mc progress show                     print progress
  ./mc import-addon SAVEDVARS.lua [--db NAME]  merge LegacyTracker SavedVariables into progress
  ./mc map CHAR INGAME_NAME              map an in-game name to a roster character for import-addon
  ./mc serve [--port 8000]               serve web/ on localhost
  ./mc ids [TEXT] [--open]               list checklist ids (filter by text; --open hides ticked ones)
  ./mc leakcheck                         fail if personal files are tracked (run before an upstream PR)
  ./mc doctor                            CI checks: examples valid, outputs up to date, progress blocks intact
Every command is plain Python 3.9+, standard library only.
"""
import argparse, copy, datetime, html, json, os, re, sys, unicodedata, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
DATA = os.path.join(ROOT, "data")
CONFIG = os.path.join(ROOT, "config", "roster.json")
EXAMPLE = os.path.join(ROOT, "config", "examples", "alliance.json")
PROGRESS = os.path.join(ROOT, "progress", "progress.json")
DRAFT = os.path.join(ROOT, "config", "roster.draft.json")
WEB_PLAN = os.path.join(ROOT, "web", "data", "plan.js")              # your roster (copies only)
WEB_EXAMPLE = os.path.join(ROOT, "web", "data", "plan.example.js")  # shipped upstream
CANVAS_TEMPLATE = os.path.join(ROOT, "adapters", "grokbot", "template.canvas.tsx")
CANVAS_OUT = os.path.join(ROOT, "adapters", "grokbot", "mission-control.canvas.tsx")
BUILD = os.path.join(ROOT, "build")
LAUNCH = "2026-11-04"
SCHEMA_VERSION = 1
CRAFTS = ["Alchemy", "Blacksmithing", "Enchanting", "Engineering", "Leatherworking", "Tailoring"]
GATHER = ["Herbalism", "Mining", "Skinning"]
SECONDARY = ["Cooking", "First Aid", "Fishing"]
RESTED = ["Empty", "Partial", "Full"]
BRACKETS = [(1, 10), (10, 16), (16, 22), (22, 26), (26, 32), (32, 40), (40, 45), (45, 52), (52, 60)]
CRAFT_TARGET = {150: 25, 225: 32, 300: 52}  # skill -> level by which to reach it
WOWHEAD = "https://www.wowhead.com/forever"


# ---------------------------------------------------------------- data
def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    os.replace(tmp, path)


def write_json(path, obj):
    write_text(path, json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


class Game:
    def __init__(self):
        self.races = load_json(os.path.join(DATA, "races.json"))["races"]
        c = load_json(os.path.join(DATA, "classes.json"))
        self.classes, self.common = c["classes"], c["common_milestones"]
        self.world = load_json(os.path.join(DATA, "world.json"))
        self.profs = load_json(os.path.join(DATA, "professions.json"))
        self.legacy = load_json(os.path.join(DATA, "legacy.json"))
        self.chains = load_json(os.path.join(DATA, "chains.json"))
        self.sources = load_json(os.path.join(DATA, "sources.json"))["sources"]
        self.ids = load_json(os.path.join(DATA, "wowhead.json"))["ids"]

    def link(self, name):
        e = self.ids.get(name)
        if e:
            return f"{WOWHEAD}/{e['type']}={e['id']}", True
        return f"{WOWHEAD}/search?q={urllib.parse.quote(name)}", False


def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "x"


# ---------------------------------------------------------------- config
def config_path(arg=None):
    if arg:
        return arg
    return CONFIG if os.path.exists(CONFIG) else EXAMPLE


def load_config(path):
    cfg = normalize(load_json(path))
    cfg["_path"] = path
    return cfg


def normalize(cfg):
    for i, ch in enumerate(cfg.get("characters") or []):
        ch.setdefault("id", slug(ch.get("name", f"c{i + 1}")))
        for p in ch.get("professions") or []:
            p.setdefault("from", 1)
    return cfg


SCHEMA_PATH = os.path.join(ROOT, "config", "roster.schema.json")


def schema_errors(obj, sch, where="roster"):
    """Tiny stdlib subset of JSON Schema: type, additionalProperties false, min/max, length, pattern, items.
    Enums and required fields are left to validate(), which gives friendlier messages."""
    out = []
    t = sch.get("type")
    kinds = {"object": dict, "array": list, "string": str, "boolean": bool}
    if t == "integer" and (isinstance(obj, bool) or not isinstance(obj, int)):
        return [f"{where} must be a whole number, got {obj!r}"]
    if t in kinds and not isinstance(obj, kinds[t]):
        return [f"{where} must be a{'n' if t[0] in 'aeiou' else ''} {t}, got {obj!r}"]
    if isinstance(obj, (int, float)) and not isinstance(obj, bool):
        if "minimum" in sch and obj < sch["minimum"]: out.append(f"{where} must be at least {sch['minimum']}, got {obj}")
        if "maximum" in sch and obj > sch["maximum"]: out.append(f"{where} must be at most {sch['maximum']}, got {obj}")
    if isinstance(obj, str):
        if "pattern" in sch and not re.search(sch["pattern"], obj): out.append(f"{where} {obj!r} does not match {sch['pattern']}")
        if "minLength" in sch and len(obj) < sch["minLength"]: out.append(f"{where} must not be empty" if sch["minLength"] == 1 else f"{where} is too short")
    if isinstance(obj, dict):
        props = sch.get("properties") or {}
        for k, v in obj.items():
            if k.startswith("_"):
                continue
            if k in props:
                out += schema_errors(v, props[k], f"{where}.{k}")
            elif sch.get("additionalProperties") is False:
                near = [p for p in props if p.replace("_", "") [:5] == k.replace("_", "")[:5]]
                out.append(f"{where}: unknown field {k!r}" + (f" (did you mean {near[0]!r}?)" if near else ""))
    if isinstance(obj, list) and isinstance(sch.get("items"), dict):
        for i, v in enumerate(obj):
            nm = v.get("name") if isinstance(v, dict) and v.get("name") else str(i)
            out += schema_errors(v, sch["items"], f"{where}[{nm}]")
    return out


def prof_spans(ch):
    return [(p["name"], int(p.get("from", 1)), int(p.get("until", 61))) for p in ch.get("professions") or []]


def validate(cfg, g):
    """Return (errors, warnings, info). Pure function; no I/O."""
    E, W, I = [], [], []
    if os.path.exists(SCHEMA_PATH):
        E += schema_errors(cfg, load_json(SCHEMA_PATH))
    fac = cfg.get("faction")
    if fac not in ("Alliance", "Horde"):
        E.append(f"faction must be Alliance or Horde, got {fac!r}")
    if cfg.get("ruleset") not in g.world["rulesets"]:
        E.append(f"ruleset must be one of {', '.join(g.world['rulesets'])}, got {cfg.get('ruleset')!r}")
    chars = cfg.get("characters") or []
    if len(chars) != 4:
        E.append(f"the plan levels exactly four characters; found {len(chars)}")
    seen_ids, seen_names = {}, {}
    for ch in chars:
        who = ch.get("name") or ch.get("id") or "?"
        for key, seen in (("id", seen_ids), ("name", seen_names)):
            v = str(ch.get(key, "")).lower()
            if v in seen:
                E.append(f"duplicate character {key} {ch.get(key)!r}")
            seen[v] = True
        if not re.fullmatch(r"[a-z0-9-]{1,24}", str(ch.get("id", ""))):
            E.append(f"{who}: id must be 1-24 chars of a-z, 0-9 or '-' (it keys saved progress)")
        name = ch.get("name", "")
        if not str(name).strip():
            E.append(f"{who}: name is empty; the addon import matches characters by in-game name")
        elif not re.fullmatch(r"[^\W\d_]{2,12}", name):
            W.append(f"{who}: in-game names are 2-12 letters with no spaces or digits; add 'display' for a longer label")
        race, cls = ch.get("race"), ch.get("class")
        r = g.races.get(race)
        if not r:
            E.append(f"{who}: unknown race {race!r}; one of {', '.join(g.races)}")
        else:
            if fac in ("Alliance", "Horde") and r["faction"] != fac:
                E.append(f"{who}: {race} is {r['faction']}, roster is {fac}")
            if cls not in g.classes:
                E.append(f"{who}: unknown class {cls!r}")
            elif cls not in r["classes"]:
                E.append(f"{who}: {race} cannot be a {cls} in Forever; {race} classes: {', '.join(r['classes'])}")
            if "Skyborne" in race:
                I.append(f"{who}: {race} needs the Skyborne Heroic Pack or higher")
        if cls in g.classes:
            specs = g.classes[cls]["specs"]
            for k in ("leveling_spec", "endgame_spec"):
                if ch.get(k) and ch[k] not in specs:
                    E.append(f"{who}: {k} {ch[k]!r} is not a {cls} spec ({', '.join(specs)})")
        spans = prof_spans(ch)
        for n, a, b in spans:
            if n not in CRAFTS + GATHER:
                E.append(f"{who}: {n!r} is not a primary profession (secondaries {', '.join(SECONDARY)} need no slot)")
            if not (1 <= a <= 60) or b <= a or (b != 61 and not 2 <= b <= 60):
                E.append(f"{who}: {n} from {a} until {b} is not a valid level span (from 1-60, until 2-60 and after from)")
            elif n in CRAFTS and b <= 60:
                short = [str(sk) for sk, lvl in CRAFT_TARGET.items() if craft_due(lvl, a) >= b]
                if short:
                    W.append(f"{who}: {n} is dropped at {b}, before its {'/'.join(short)} target level; those Legacy points are not in the plan")
        for lv in range(1, 61):
            active = [n for n, a, b in spans if a <= lv < b]
            if len(active) > 2:
                E.append(f"{who}: three primary professions at level {lv} ({', '.join(active)}); the limit is two")
                break
    if E:
        return E, W, I
    # coverage
    crafts = {c: [ch["name"] for ch in chars if c in [n for n, _, _ in prof_spans(ch)]] for c in CRAFTS}
    gaps = [c for c, who in crafts.items() if not who]
    for c in gaps:
        W.append(f"gap: no character takes {c}; that is 3 Legacy points left on the table")
    for c, who in crafts.items():
        if len(who) > 1:
            W.append(f"duplicate: {c} on {', '.join(who)}; Legacy pays each craft once per account")
    classes = [ch["class"] for ch in chars]
    for c in sorted(set(classes)):
        if classes.count(c) > 1:
            W.append(f"duplicate class: {classes.count(c)} {c}s; class Legacy points pay once per class")
    all_profs = {n for ch in chars for n, _, _ in prof_spans(ch)}
    for c, info in g.profs["crafting"].items():
        need = [u for u in info.get("uses", []) if u in GATHER]
        if crafts.get(c) and need and not any(u in all_profs for u in need):
            I.append(f"{c} has no {' or '.join(need)} on the roster; plan to buy materials")
    return E, W, I


# ---------------------------------------------------------------- plan
def craft_due(lvl, start):
    """Level by which a craft target is due: the usual target level, or the level it's trained if that's 52+."""
    return max(lvl, start if start >= 52 else lvl)


def overlaps(lo, hi, a, b):
    return a < hi and b > lo


def build_plan(cfg, g, progress=None):
    fac = cfg["faction"]
    other = "Horde" if fac == "Alliance" else "Alliance"
    chars = []
    for ch in cfg["characters"]:
        r, c = g.races[ch["race"]], g.classes[ch["class"]]
        ms = [dict(m) for m in c["milestones"] + g.common
              if m.get("faction", "both") in ("both", fac) and (not m.get("races") or ch["race"] in m["races"])]
        chars.append({
            "id": ch["id"], "name": ch["name"], "display": ch.get("display", ch["name"]),
            "race": ch["race"], "class": ch["class"], "color": c["color"], "icon": c["icon"],
            "leveling_spec": ch.get("leveling_spec") or c["leveling"]["spec"],
            "endgame_spec": ch.get("endgame_spec") or c["endgame"][0],
            "role": ch.get("role", ""), "notes": ch.get("notes", ""),
            "start_zone": r["start_zone"], "start_area": r["start_area"], "first_hub": r["first_hub"],
            "capital": r["capital"], "racials": r["racials"], "race_notes": r["notes"],
            "professions": [{"name": n, "from": a, **({"until": b} if b <= 60 else {})} for n, a, b in prof_spans(ch)],
            "milestones": sorted(ms, key=lambda m: m["level"]),
        })
    zones_ok = [z for z in g.world["zones"] if z["owner"] != other and z["name"] != "Zephras Isle"]
    dungeons = []
    for d in g.world["dungeons"]:
        if d["access"] in (fac, "Both"):
            dungeons.append(dict(d))
        elif d.get("spelunker") and not d.get("starter"):
            # each faction's own starter dungeon covers Novice Spelunker (data/world.json "starter"), so skip the other side's
            dungeons.append({**d, "travel": True})
    brackets = []
    for lo, hi in BRACKETS:
        bid = f"{lo}-{hi}"
        if lo == 1:
            zones = sorted({ch["start_zone"] for ch in chars})
        else:
            cand = [z for z in zones_ok if overlaps(lo, hi, z["min"], z["max"]) and z["min"] <= lo + 4 and z["min"] > 1]
            cand.sort(key=lambda z: (-(z["quests"].get(fac) or 0), z["min"]))
            zones = [z["name"] for z in cand[:6]]
        bd = [d for d in dungeons if lo <= (d["min"] + d["max"]) / 2 < hi or (hi == 60 and (d["min"] + d["max"]) / 2 >= 60)]
        tasks, why = {}, []
        for ch, src in zip(chars, cfg["characters"]):
            items = []

            def add(key, text, tag):
                items.append({"id": f"{bid}-{ch['id']}-{key}", "text": text, "tag": tag})
            if lo == 1:
                add("create", f"Create {ch['name']}, {ch['race']} {ch['class']}, in {ch['start_zone']}", "Start")
            for n, a, b in prof_spans(src):
                if lo <= a < hi or (lo == 1 and a == 1) or (hi == 60 and a == 60):
                    gone = [p for p, _, e in prof_spans(src) if e == a]
                    add(f"train-{slug(n)}", f"Swap {gone[0]} for {n}" if gone else f"Train {n}", "Profession")
                if n in CRAFTS:
                    for skill, lvl in CRAFT_TARGET.items():
                        due = craft_due(lvl, a)
                        if (lo < due <= hi or (lo == 1 and due == 1)) and a < b and due < b:
                            add(f"{slug(n)}-{skill}", f"{n} to {skill}", "Legacy")
            for m in ch["milestones"]:
                if lo <= m["level"] < hi or (hi == 60 and m["level"] == 60):
                    add(f"m-{slug(m['name'])}", f"{m['name']} at {m['level']}", "Class")
            for lv, nm in zip(g.legacy["challenges"]["class"]["levels"], g.legacy["challenges"]["class"]["names"]):
                if lo < lv <= hi:
                    add(f"legacy-{lv}", f"{nm} {ch['class']} at {lv}", "Legacy")
            for d in bd:
                add(f"d-{slug(d['name'])}", f"Run {d['name']}", "Dungeon")
            if lo == 22:
                bag = g.chains["sleeping_bag"]
                add("sleeping-bag", f"{bag['name']} chain, starts in {g.world['factions'][fac]['sleeping_bag_start']['zone']}", "Chain")
            tasks[ch["id"]] = items
        for d in bd:
            why.append(f"{d['name']} ({d['min']}-{d['max']})" + (" in enemy territory" if d.get("travel") else ""))
        for lv, nm in zip(g.legacy["challenges"]["class"]["levels"], g.legacy["challenges"]["class"]["names"]):
            if lo < lv <= hi:
                why.append(f"Level {lv}: {nm} class Legacy points")
        if lo <= 40 < hi or hi == 40:
            why.append("Riding at 40")
        rotation = [{"char": ch["id"], "target": hi,
                     "zones": [ch["start_zone"]] if lo == 1 else zones[:3],
                     "logout": ch["first_hub"] if lo == 1 else ch["capital"]} for ch in chars]
        brackets.append({"id": bid, "from": lo, "to": hi, "zones": zones,
                         "dungeons": [d["name"] for d in bd], "why": why, "tasks": tasks, "rotation": rotation})
    # account-wide checklist
    account = []
    sp = {}
    for d in g.world["dungeons"]:
        if d.get("spelunker"):
            sp.setdefault(d["spelunker"], []).append(d["name"])
    for tier in ("Novice", "Experienced", "Master"):
        account.append({"id": f"acct-spelunker-{tier.lower()}", "text": f"{tier} Spelunker", "tag": "Legacy", "detail": ", ".join(sp.get(tier, []))})
    for k in ("raid", "adventure"):
        for it in g.legacy["challenges"][k]["items"]:
            account.append({"id": f"acct-{slug(it)}", "text": it, "tag": "Legacy"})
    # coverage and Legacy projection
    crafts = {c: [ch["id"] for ch, src in zip(chars, cfg["characters"]) if c in [n for n, _, _ in prof_spans(src)]] for c in CRAFTS}
    distinct = len({ch["class"] for ch in chars})
    covered = sum(1 for v in crafts.values() if v)
    # earliest reachable due level per craft target, across everyone who takes the craft (None: dropped before it)
    due_at = {}
    for c in CRAFTS:
        for sk, lvl in CRAFT_TARGET.items():
            ds = [craft_due(lvl, a) for src in cfg["characters"] for n, a, b in prof_spans(src) if n == c and craft_due(lvl, a) < b]
            if ds:
                due_at[(c, sk)] = min(ds)
    proj = []
    for lo, hi in BRACKETS:
        pts = sum(1 for lv in (25, 45, 60) if lv <= hi) * distinct
        pts += sum(1 for d in due_at.values() if d <= hi)
        proj.append({"at": f"{lo}-{hi}", "points": pts})
    errs, warns, info = validate(cfg, g)
    links = {}
    names = set(g.races) | set(g.classes) | set(CRAFTS + GATHER + SECONDARY)
    names |= {z["name"] for z in g.world["zones"]} | {d["name"] for d in g.world["dungeons"]}
    names |= {m["name"] for c in g.classes.values() for m in c["milestones"]} | {m["name"] for m in g.common}
    names |= {x for ch in chars for x in ch["racials"] + [ch["start_area"], ch["first_hub"], ch["capital"]]}
    names |= {t[k] for t in g.world["transport"] for k in ("from", "to")}
    names |= {fp for v in g.world["flight_paths"].values() for fp in v}
    names |= {s["quest"] for s in g.chains["sleeping_bag"]["steps"]} | {g.chains["sleeping_bag"]["name"]}
    names |= {r["name"] for r in g.legacy["rewards"]} | {p[0] for t in g.legacy["trees"].values() for p in t}
    names |= set(g.ids)
    for n in sorted(names):
        url, direct = g.link(n)
        links[n] = {"url": url, "direct": direct}
    prog = progress or empty_progress(cfg)
    return {
        "schema": SCHEMA_VERSION, "generated_from": os.path.relpath(cfg.get("_path", CONFIG), ROOT).replace(os.sep, "/"),
        "roster": {"name": cfg.get("roster_name", "Legacy Mission Control"), "faction": fac, "ruleset": cfg["ruleset"],
                   "launch": cfg.get("launch", LAUNCH), "key": roster_key(cfg)},
        "characters": chars, "brackets": brackets, "account": account,
        "coverage": {"crafts": crafts, "gaps": [c for c, v in crafts.items() if not v],
                     "distinct_classes": distinct, "crafts_covered": covered,
                     "legacy_from_plan": distinct * 3 + len(due_at), "projection": proj},
        "validation": {"errors": errs, "warnings": warns, "info": info},
        "faction": g.world["factions"][fac],
        "zones": [z for z in g.world["zones"] if z["owner"] != other],
        "dungeons": dungeons,
        "transport": [t for t in g.world["transport"] if t["faction"] in (fac, "Both")],
        "flight_paths": g.world["flight_paths"][fac] + g.world["flight_paths"]["Both"],
        "legacy": g.legacy, "sleeping_bag": g.chains["sleeping_bag"], "professions": g.profs,
        "sources": g.sources, "links": links, "progress": prog,
    }


def roster_key(cfg):
    return slug(cfg.get("roster_name", "roster")) + "-" + "-".join(ch["id"] for ch in cfg["characters"])


# ---------------------------------------------------------------- progress
def empty_progress(cfg):
    return {"version": 1, "roster": roster_key(cfg), "updated": "", "checks": {},
            "levels": {ch["id"]: {"level": 1, "rested": "Empty", "updated": ""} for ch in cfg["characters"]},
            "skills": {}, "map": {}, "notes": ""}


def load_progress(cfg, path=PROGRESS):
    p = empty_progress(cfg)
    if os.path.exists(path):
        got = load_json(path)
        for k in ("checks", "skills", "map"):
            p[k].update(got.get(k) or {})
        for cid, lv in (got.get("levels") or {}).items():
            p["levels"].setdefault(cid, {}).update(lv)
        p["updated"] = got.get("updated", "")
        p["notes"] = got.get("notes", "")
        for k, v in got.items():  # keep keys added by other tools or newer versions
            p.setdefault(k, v)
    return p


def today():
    return datetime.date.today().isoformat()


def find_char(cfg, who):
    w = who.lower()
    for ch in cfg["characters"]:
        if w in (ch["id"].lower(), ch["name"].lower(), str(ch.get("display", "")).lower()):
            return ch
    sys.exit(f"no character {who!r}; roster has {', '.join(c['name'] for c in cfg['characters'])}")


def _rec_time(rec):
    """ms timestamp of a level record: addon lastSeenEpoch, else its updated date."""
    if rec.get("lastSeenEpoch"):
        return int(rec["lastSeenEpoch"]) * 1000
    try:
        return int(datetime.datetime.strptime(rec.get("updated") or "", "%Y-%m-%d").timestamp() * 1000)
    except ValueError:
        return 0


def merge_progress(p, new):
    """Merge an exported progress blob into p.
    Checks: the export is the full state. Levels and skills: keep the higher, unless the export carries a
    page edit stamp (stamp["l:char"], stamp["s:char:prof"]) newer than what p has, so corrections stick.
    Name mappings are unioned (the export wins on a conflict)."""
    st, mine_st = new.get("stamp") or {}, p.setdefault("stamp", {})

    def wins(key, t=0):
        return key in st and st[key] >= max(mine_st.get(key, 0), t)

    if "checks" in new:
        p["checks"] = {k: True for k, v in new["checks"].items() if v}
    for cid, lv in (new.get("levels") or {}).items():
        old = p["levels"].setdefault(cid, {})
        if f"l:{cid}" in st:
            if wins(f"l:{cid}", _rec_time(old)):
                old.update(lv)
        elif (lv.get("level") or 0) >= (old.get("level") or 0):
            old.update(lv)
    for cid, sk in (new.get("skills") or {}).items():
        mine = p["skills"].setdefault(cid, {})
        for prof, v in sk.items():
            k = f"s:{cid}:{prof}"
            if k in st:
                if wins(k):
                    mine[prof] = int(v or 0)
            else:
                mine[prof] = max(int(v or 0), int(mine.get(prof) or 0))
    if ("n" in st and wins("n")) or ("n" not in st and new.get("notes")):
        p["notes"] = new.get("notes") or ""
    p.setdefault("map", {}).update(new.get("map") or {})
    for k, v in st.items():
        mine_st[k] = max(v, mine_st.get(k, 0))
    for k, v in new.items():  # keep keys added by other tools or newer versions
        if k not in ("version", "roster", "updated", "checks", "levels", "skills", "map", "notes", "stamp"):
            p[k] = v
    p["updated"] = new.get("updated") or today()
    return p


def progress_diff(old, new):
    """Human summary of what changed between two progress dicts."""
    out = []
    add = sorted(k for k in new["checks"] if new["checks"][k] and not old["checks"].get(k))
    rem = sorted(k for k in old["checks"] if old["checks"][k] and not new["checks"].get(k))
    if add: out.append(f"+{len(add)} check(s): " + ", ".join(add[:8]) + (" ..." if len(add) > 8 else ""))
    if rem: out.append(f"-{len(rem)} check(s): " + ", ".join(rem[:8]) + (" ..." if len(rem) > 8 else ""))
    for cid in sorted(set(old["levels"]) | set(new["levels"])):
        a, b = (old["levels"].get(cid) or {}), (new["levels"].get(cid) or {})
        if (a.get("level"), a.get("rested")) != (b.get("level"), b.get("rested")):
            out.append(f"{cid}: level {a.get('level')} -> {b.get('level')}, rested {a.get('rested')} -> {b.get('rested')}")
    for cid in sorted(set(old["skills"]) | set(new["skills"])):
        for prof in sorted(set(old["skills"].get(cid, {})) | set(new["skills"].get(cid, {}))):
            x, y = old["skills"].get(cid, {}).get(prof), new["skills"].get(cid, {}).get(prof)
            if x != y: out.append(f"{cid}: {prof} {x} -> {y}")
    for k in sorted(set(new.get("map") or {}) - set(old.get("map") or {})):
        out.append(f"map {k} -> {new['map'][k]}")
    return out or ["no changes"]


def backup_progress(path=PROGRESS):
    """Copy progress.json to progress/backups/ before a destructive change. Returns the backup path or None."""
    if not os.path.exists(path):
        return None
    dest = os.path.join(os.path.dirname(path), "backups", "progress-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + ".json")
    with open(path, encoding="utf-8") as fh:
        write_text(dest, fh.read())
    return dest


def rested_label(rested, xp_max):
    if not rested or not xp_max:
        return "Empty"
    return "Full" if rested / xp_max >= 1.495 else "Partial"


def import_addon(cfg, p, text, force=False, db_name="LegacyTrackerDB"):
    sv = __import__("savedvars").parse(text)
    if db_name not in sv:
        found = ", ".join(k for k in sv if isinstance(sv[k], dict) and "chars" in sv[k]) or "none"
        raise SystemExit(f"{db_name} not found in the file (tables with characters: {found}); use --db NAME for a renamed copy of the addon")
    db = sv.get(db_name) or {}
    chars = db.get("chars") or {}
    byname = {ch["name"].lower(): ch["id"] for ch in cfg["characters"]}
    byname.update({k.lower(): v for k, v in (p.get("map") or {}).items()})
    best, out = {}, []
    for key, c in chars.items():
        if not isinstance(c, dict):
            continue
        nm = str(c.get("name") or str(key).rsplit("-", 1)[-1]).lower()
        cid = byname.get(nm) or byname.get(str(key).lower())
        if not cid:
            out.append(f"skip {key}: not on the roster (./mc map CHAR {c.get('name', key)})")
            continue
        if cid not in best or (c.get("lastSeen") or 0) > (best[cid].get("lastSeen") or 0):
            best[cid] = c
    for cid, c in sorted(best.items()):
        old = p["levels"].setdefault(cid, {})
        seen = c.get("lastSeen") or 0
        if not force and old.get("lastSeenEpoch") and seen <= old["lastSeenEpoch"]:
            out.append(f"{cid}: unchanged (addon data not newer)")
            continue
        if not force and (old.get("level") or 0) > (c.get("level") or 0):
            out.append(f"{cid}: skipped, would lower level {old.get('level')} -> {c.get('level')} (use --force)")
            continue
        xp, xm, rs = c.get("xp") or 0, c.get("xpMax") or 0, c.get("rested") or 0
        old.update({k: v for k, v in {
            "level": c.get("level"), "rested": rested_label(rs, xm),
            "updated": datetime.datetime.fromtimestamp(seen).date().isoformat() if seen else today(),
            "pctToNext": round(xp / xm * 100, 1) if xm else None,
            "restedBubbles": round(rs / xm * 20, 1) if xm else None,
            "zone": c.get("zone"), "lastSeenEpoch": seen or None, "source": "LegacyTracker"}.items() if v is not None})
        sk = p["skills"].setdefault(cid, {})
        for prof, v in (c.get("professions") or {}).items():
            if isinstance(v, dict) and v.get("rank") is not None:
                sk[prof] = max(int(v["rank"]), int(sk.get(prof) or 0))
        out.append(f"{cid}: level {c.get('level')}, rested {old['rested']}, skills {sk}")
    p["updated"] = today()
    return p, out


def scrub_addon(cfg, text, db_name="LegacyTrackerDB"):
    """Roster characters' level, rested, zone and skills from a LegacyTracker file, nothing else (no gold, time played or other characters)."""
    p, lines = import_addon(cfg, empty_progress(cfg), text, True, db_name)
    found = {l.split(":")[0] for l in lines if not l.startswith("skip ")}
    out = {"version": 1, "roster": p["roster"], "updated": today(),
           "levels": {k: v for k, v in p["levels"].items() if k in found},
           "skills": {k: v for k, v in p["skills"].items() if k in found and v}}
    return out, lines


def save_progress(p, path=PROGRESS):
    write_json(path, p)


# ---------------------------------------------------------------- outputs
def plan_markdown(plan):
    L = plan["links"]

    def a(n):
        return f"[{n}]({L[n]['url']})" if n in L else n

    def lt(text):
        keys = sorted((k for k in L if k in text), key=len, reverse=True)
        if not keys:
            return text
        pat = re.compile(r"(?<![A-Za-z0-9])(" + "|".join(re.escape(k) for k in keys) + r")(?![A-Za-z0-9])")
        return pat.sub(lambda m: a(m.group(1)), text)
    r = plan["roster"]
    o = [f"# {r['name']}", "", f"{a(r['faction'])} · {r['ruleset']} · launch {r['launch']}", ""]
    o += ["## Roster", "", "| Character | Race | Class | Leveling | Endgame | Professions | Starts |", "|---|---|---|---|---|---|---|"]
    for c in plan["characters"]:
        pr = ", ".join(a(p["name"]) + (f" {p['from']}-{p['until']}" if "until" in p else (f" from {p['from']}" if p["from"] > 1 else "")) for p in c["professions"])
        o.append(f"| {c['display']} | {a(c['race'])} | {a(c['class'])} | {c['leveling_spec']} | {c['endgame_spec']} | {pr} | {a(c['start_zone'])} |")
    cv = plan["coverage"]
    o += ["", "## Craft coverage", "", "| Craft | Characters |", "|---|---|"]
    names = {c["id"]: c["display"] for c in plan["characters"]}
    for craft, who in cv["crafts"].items():
        o.append(f"| {a(craft)} | {', '.join(names[w] for w in who) or 'none'} |")
    o += ["", f"Legacy points from this plan: {cv['legacy_from_plan']} ({cv['distinct_classes']} classes x 3, {cv['crafts_covered']} crafts x 3).", ""]
    v = plan["validation"]
    if v["warnings"] or v["info"]:
        o += ["## Validator notes", ""] + [f"- {x}" for x in v["warnings"] + v["info"]] + [""]
    for b in plan["brackets"]:
        o += [f"## Levels {b['from']}-{b['to']}", ""]
        if b["why"]:
            o += [lt(", ".join(b["why"])), ""]
        if b["zones"]:
            o += ["Zones: " + ", ".join(a(z) for z in b["zones"]), ""]
        for c in plan["characters"]:
            items = b["tasks"][c["id"]]
            if not items:
                continue
            o.append(f"**{c['display']}** ({c['race']} {c['class']})")
            o += [f"- [ ] {lt(i['text'])} `{i['tag']}`" for i in items]
            o.append("")
    o += ["## Account", ""] + [f"- [ ] {lt(i['text'])}" + (f": {lt(i['detail'])}" if i.get("detail") else "") for i in plan["account"]]
    o += ["", "## Sources", ""] + [f"- [{s['title']}]({s['url']}) · {s['site']}" for s in plan["sources"].values()]
    return "\n".join(o) + "\n"


def script_json(obj, **kw):
    """JSON that is also safe inside an HTML <script> block or a TSX file: no </script>, <!--, or line separators."""
    t = json.dumps(obj, ensure_ascii=False, **kw)
    for a, b in (("<", "\\u003c"), (">", "\\u003e"), ("&", "\\u0026"), ("\u2028", "\\u2028"), ("\u2029", "\\u2029")):
        t = t.replace(a, b)
    return t


def web_js(plan):
    return "// Generated by ./mc generate. Do not edit by hand.\nwindow.MC_PLAN = " + script_json(plan, separators=(",", ":")) + ";\n"


def canvas_tsx(plan):
    t = open(CANVAS_TEMPLATE, encoding="utf-8").read()
    data = {k: v for k, v in plan.items() if k != "progress"}
    t = re.sub(r"// ROSTER-START.*?// ROSTER-END", lambda _: "// ROSTER-START\nconst PLAN: Plan = " + script_json(data) + ";\n// ROSTER-END", t, flags=re.S)
    t = re.sub(r"// SAVED-START.*?// SAVED-END", lambda _: "// SAVED-START\nconst SAVED: Saved = " + script_json(plan["progress"], indent=2) + ";\n// SAVED-END", t, flags=re.S)
    return t


def outputs(cfg_path, personal=None):
    """Files to write for one config. personal=False builds the shipped example (no progress, no plan.js)."""
    g = Game()
    cfg = load_config(cfg_path)
    cfg["_path"] = cfg_path
    E, _, _ = validate(cfg, g)
    if E:
        raise SystemExit("validation failed:\n  " + "\n  ".join(E))
    if personal is None:
        personal = os.path.abspath(cfg_path) != os.path.abspath(EXAMPLE)
    plan = build_plan(cfg, g, load_progress(cfg) if personal else None)
    files = {os.path.join(BUILD, "plan.json"): json.dumps(plan, indent=2, ensure_ascii=False) + "\n",
             os.path.join(BUILD, "PLAN.md"): plan_markdown(plan)}
    if personal:
        files[WEB_PLAN] = web_js(plan)
        files[CANVAS_OUT] = canvas_tsx(plan)
    else:
        files[os.path.join(BUILD, "mission-control.canvas.tsx")] = canvas_tsx(plan)
    return files, plan


def example_files():
    g = Game()
    files = {WEB_EXAMPLE: web_js(build_plan(load_config(EXAMPLE), g))}
    for ex in ("alliance", "horde"):
        p = os.path.join(ROOT, "config", "examples", f"{ex}.json")
        files[os.path.join(ROOT, "docs", "examples", f"{ex}-plan.md")] = plan_markdown(build_plan(load_config(p), g))
    return files


def missing_links():
    g = Game()
    plan = build_plan(load_config(EXAMPLE), g)
    out = set()
    for f in ("horde.json",):
        out |= {n for n, v in build_plan(load_config(os.path.join(ROOT, "config", "examples", f)), g)["links"].items() if not v["direct"]}
    return out | {n for n, v in plan["links"].items() if not v["direct"]}


# ---------------------------------------------------------------- interview
QUESTIONS = [
    ("roster_name", "Roster name (shown as the page title)", "My Legacy Roster"),
    ("faction", "Faction: Alliance or Horde", "Alliance"),
    ("ruleset", "Ruleset: Normal, PvP, Roleplay or Hardcore", "Normal"),
]


def interview(answers=None):
    g = Game()
    ask = (lambda k, q, d: answers.get(k, d)) if answers is not None else (lambda k, q, d: input(f"{q} [{d}]: ").strip() or d)
    cfg = {"$schema": "./roster.schema.json", "launch": LAUNCH}
    for k, q, d in QUESTIONS:
        cfg[k] = ask(k, q, d)
    fac = cfg["faction"]
    chars = []
    for i in range(4):
        pre = f"c{i + 1}."
        races = [r for r, v in g.races.items() if v["faction"] == fac]
        name = ask(pre + "name", f"Character {i + 1} name", f"Hero{i + 1}")
        race = ask(pre + "race", f"  Race ({', '.join(races)})", races[0])
        cls_opts = g.races.get(race, {}).get("classes", [])
        cls = ask(pre + "class", f"  Class ({', '.join(cls_opts)})", cls_opts[0] if cls_opts else "Warrior")
        c = g.classes.get(cls, {})
        lv = ask(pre + "leveling_spec", f"  Leveling spec ({', '.join(c.get('specs', []))})", c.get("leveling", {}).get("spec", ""))
        eg = ask(pre + "endgame_spec", "  Endgame spec", (c.get("endgame") or [""])[0])
        pr = ask(pre + "professions", "  Professions, e.g. 'Mining 1-60, Blacksmithing, Engineering 60-'", "")
        profs = []
        for part in [x.strip() for x in str(pr).split(",") if x.strip()]:
            m = re.fullmatch(r"(.+?)(?:\s+(\d*)\s*(?:-\s*(\d*))?)?", part)
            p = {"name": m.group(1).strip().title()}
            if m.group(2):
                p["from"] = int(m.group(2))
            if m.group(3):
                p["until"] = int(m.group(3))
            profs.append(p)
        chars.append({"id": slug(name), "name": name, "race": race, "class": cls, "leveling_spec": lv, "endgame_spec": eg, "professions": profs})
    cfg["characters"] = chars
    return cfg


# ---------------------------------------------------------------- doctor
def doctor():
    g = Game()
    problems = []
    for f in sorted(os.listdir(os.path.join(ROOT, "config", "examples"))):
        cfg = load_config(os.path.join(ROOT, "config", "examples", f))
        E, W, _ = validate(cfg, g)
        if E or W:
            problems.append(f"examples/{f}: " + "; ".join(E + W))
        build_plan(cfg, g)
    starters = {}
    for d in g.world["dungeons"]:
        if d.get("starter"):
            starters.setdefault(d["access"], []).append(d["name"])
            if d.get("spelunker") != "Novice":
                problems.append(f"starter dungeon {d['name']} should be a Novice Spelunker dungeon")
    for side in ("Alliance", "Horde"):
        if len(starters.get(side, [])) != 1:
            problems.append(f"data/world.json: expected exactly one {side} starter dungeon, found {starters.get(side, [])}")
    for path, text in example_files().items():
        cur = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
        if cur != text:
            problems.append(f"{os.path.relpath(path, ROOT)} is out of date: run ./mc generate")
    if os.path.exists(CONFIG):
        files, plan = outputs(CONFIG)
        for path in (WEB_PLAN, CANVAS_OUT):
            cur = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
            if cur != files[path]:
                problems.append(f"{os.path.relpath(path, ROOT)} is out of date: run ./mc generate")
        src = files[CANVAS_OUT]
    else:
        files, plan = outputs(EXAMPLE, personal=False)
        src = files[os.path.join(BUILD, "mission-control.canvas.tsx")]
    m = re.search(r"// SAVED-START\s*const SAVED: Saved = (\{.*?\});\s*// SAVED-END", src, re.S)
    if not m or json.loads(m.group(1)) != plan["progress"]:
        problems.append("canvas SAVED block missing or not equal to progress")
    if "// ROSTER-START" not in src or "PLAN: Plan" not in src:
        problems.append("canvas ROSTER block missing")
    ids = [i["id"] for b in plan["brackets"] for t in b["tasks"].values() for i in t] + [i["id"] for i in plan["account"]]
    if len(ids) != len(set(ids)):
        problems.append("duplicate checklist ids")
    for d in ("classes", "races", "world"):
        for s in re.findall(r'"source": "([^"]+)"', open(os.path.join(DATA, f"{d}.json"), encoding="utf-8").read()):
            if s not in g.sources:
                problems.append(f"data/{d}.json cites unknown source {s}")
    return problems


PERSONAL = ["config/roster.json", "progress/", "web/data/plan.js", "adapters/grokbot/mission-control.canvas.tsx", "build/"]


def leakcheck():
    """Personal files must never be part of an upstream pull request."""
    import subprocess
    try:
        tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    except Exception as e:  # not a git checkout
        return [f"git ls-files failed: {e}"]
    probs = [f"{f} is tracked" for f in tracked if any(f == x or (x.endswith("/") and f.startswith(x)) for x in PERSONAL) and not f.endswith(".gitkeep")]
    probs += [f"{f} looks like SavedVariables" for f in tracked if re.search(r"(^|/)(WTF|SavedVariables)/", f)]
    return probs


# ---------------------------------------------------------------- CLI
def main(argv=None):
    ap = argparse.ArgumentParser(prog="mc", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    s = sub.add_parser("init"); s.add_argument("--answers"); s.add_argument("--force", action="store_true")
    s = sub.add_parser("validate"); s.add_argument("--config"); s.add_argument("--strict", action="store_true")
    s = sub.add_parser("generate"); s.add_argument("--config")
    s = sub.add_parser("plan"); s.add_argument("--config")
    s = sub.add_parser("level"); s.add_argument("char"); s.add_argument("level", type=int); s.add_argument("--rested", choices=RESTED); s.add_argument("--config")
    s = sub.add_parser("skill"); s.add_argument("char"); s.add_argument("profession"); s.add_argument("skill", type=int); s.add_argument("--config")
    s = sub.add_parser("check"); s.add_argument("ids", nargs="+"); s.add_argument("--off", action="store_true"); s.add_argument("--force", action="store_true"); s.add_argument("--config")
    s = sub.add_parser("progress"); s.add_argument("action", choices=["merge", "show", "reset"]); s.add_argument("file", nargs="?"); s.add_argument("--dry-run", action="store_true"); s.add_argument("--force", action="store_true"); s.add_argument("--config")
    s = sub.add_parser("import-addon"); s.add_argument("savedvars"); s.add_argument("--force", action="store_true"); s.add_argument("--dry-run", action="store_true"); s.add_argument("--db", default="LegacyTrackerDB", help="SavedVariables table name (for a renamed copy of the addon)"); s.add_argument("--config")
    s = sub.add_parser("scrub-addon", help="write a shareable progress JSON from LegacyTracker.lua (roster characters only, no gold or time played)")
    s.add_argument("savedvars"); s.add_argument("-o", "--out"); s.add_argument("--db", default="LegacyTrackerDB"); s.add_argument("--config")
    s = sub.add_parser("map"); s.add_argument("char"); s.add_argument("ingame"); s.add_argument("--config")
    s = sub.add_parser("serve"); s.add_argument("--port", type=int, default=8000)
    sub.add_parser("doctor")
    s = sub.add_parser("ids"); s.add_argument("text", nargs="?"); s.add_argument("--open", action="store_true"); s.add_argument("--config")
    sub.add_parser("leakcheck")
    a = ap.parse_args(argv)
    g = None
    if a.cmd == "init":
        if os.path.exists(CONFIG) and not a.force:
            sys.exit("config/roster.json exists; use --force to overwrite")
        cfg = interview(load_json(a.answers) if a.answers else None)
        g = Game()
        E, W, I = validate(normalize(json.loads(json.dumps(cfg))), g)
        dest = DRAFT if E else CONFIG
        write_json(dest, cfg)
        print(f"wrote {os.path.relpath(dest, ROOT)}" + (" (not config/roster.json: fix the errors below, then rename it)" if E else ""))
        for x in E: print("error:", x)
        for x in W: print("warning:", x)
        for x in I: print("note:", x)
        return 1 if E else 0
    if a.cmd == "validate":
        path = config_path(a.config)
        E, W, I = validate(load_config(path), Game())
        print(f"{os.path.relpath(path, ROOT)}: {len(E)} error(s), {len(W)} warning(s)")
        for x in E: print("error:", x)
        for x in W: print("warning:", x)
        for x in I: print("note:", x)
        return 1 if E or (a.strict and W) else 0
    if a.cmd in ("generate", "plan"):
        files, plan = outputs(config_path(a.config))
        if a.cmd == "plan":
            print(files[os.path.join(BUILD, "PLAN.md")])
            return 0
        files.update(example_files())
        for path, text in files.items():
            write_text(path, text)
            print("wrote", os.path.relpath(path, ROOT))
        if not os.path.exists(CONFIG) and not a.config:
            print("no config/roster.json yet: the page shows the example roster (./mc init to make yours)")
        for x in plan["validation"]["warnings"]: print("warning:", x)
        return 0
    if a.cmd == "serve":
        import http.server, functools
        h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=os.path.join(ROOT, "web"))
        print(f"http://localhost:{a.port}/")
        http.server.ThreadingHTTPServer(("127.0.0.1", a.port), h).serve_forever()
    if a.cmd == "ids":
        cfg = load_config(config_path(a.config))
        _, plan = outputs(config_path(a.config))
        done = load_progress(cfg)["checks"]
        rows = [(f"{b['from']}-{b['to']}", i) for b in plan["brackets"] for t in b["tasks"].values() for i in t] + [("account", i) for i in plan["account"]]
        for where, i in rows:
            if a.text and a.text.lower() not in (i["id"] + " " + i["text"]).lower(): continue
            if a.open and done.get(i["id"]): continue
            print(f"{'x' if done.get(i['id']) else ' '} {i['id']:<48} {where:<8} {i['text']}")
        return 0
    if a.cmd == "leakcheck":
        probs = leakcheck()
        for x in probs: print("LEAK:", x)
        print("leakcheck: ok" if not probs else f"leakcheck: {len(probs)} problem(s); see CONTRIBUTING.md")
        return 1 if probs else 0
    if a.cmd == "doctor":
        probs = doctor()
        for x in probs: print("FAIL:", x)
        print("doctor: ok" if not probs else f"doctor: {len(probs)} problem(s)")
        return 1 if probs else 0
    if a.cmd == "scrub-addon":
        cfg = load_config(config_path(a.config))
        out, lines = scrub_addon(cfg, open(a.savedvars, encoding="utf-8", errors="replace").read(), a.db)
        for l in lines: print(l, file=sys.stderr)
        dest = os.path.abspath(a.out or f"progress-share-{today()}.json")
        write_json(dest, out)
        print(f"wrote {dest}: {len(out['levels'])} character(s); send this instead of LegacyTracker.lua (merge with ./mc progress merge)")
        return 0
    if a.cmd in ("level", "skill", "check", "progress", "import-addon", "map"):
        cfg = load_config(config_path(a.config))
        p = load_progress(cfg)
        if a.cmd == "level":
            ch = find_char(cfg, a.char)
            if not 1 <= a.level <= 60: sys.exit("level must be 1-60")
            e = p["levels"].setdefault(ch["id"], {})
            e.update({"level": a.level, "updated": today(), "source": "manual"})
            if a.rested: e["rested"] = a.rested
            print(f"{ch['name']}: level {a.level}")
        elif a.cmd == "skill":
            ch = find_char(cfg, a.char)
            prof = a.profession.title()
            if prof not in CRAFTS + GATHER + SECONDARY: sys.exit(f"unknown profession {a.profession}")
            if not 0 <= a.skill <= 300: sys.exit("skill must be 0-300")
            p["skills"].setdefault(ch["id"], {})[prof] = a.skill
            print(f"{ch['name']}: {prof} {a.skill}")
        elif a.cmd == "check":
            plan = build_plan(cfg, Game())
            known = {i["id"] for b in plan["brackets"] for t in b["tasks"].values() for i in t} | {i["id"] for i in plan["account"]}
            bad = [i for i in a.ids if i not in known]
            if bad and not a.off and not a.force:
                sys.exit(f"unknown checklist id(s): {', '.join(bad)}. Find ids with ./mc ids <text>, or add --force.")
            for i in a.ids:
                if a.off: p["checks"].pop(i, None)
                else: p["checks"][i] = True
            print(("unticked " if a.off else "ticked ") + ", ".join(a.ids))
        elif a.cmd == "map":
            ch = find_char(cfg, a.char)
            p["map"][a.ingame] = ch["id"]
            print(f"in-game {a.ingame} -> {ch['id']}")
        elif a.cmd == "progress":
            if a.action == "show":
                print(json.dumps(p, indent=2, ensure_ascii=False)); return 0
            before = copy.deepcopy(p)
            if a.action == "reset":
                if not a.force and not a.dry_run:
                    sys.exit("progress reset clears every level, skill, tick and mapping. Run with --dry-run to see what goes, or --force to do it (a backup is written to progress/backups/).")
                p = empty_progress(cfg)
            else:
                raw = sys.stdin.read() if a.file in (None, "-") else open(a.file, encoding="utf-8").read()
                m = re.search(r"\{.*\}", raw, re.S)
                if not m: sys.exit("no JSON object found")
                new = json.loads(m.group(0))
                if new.get("roster") and new["roster"] != p["roster"]:
                    print(f"warning: export is for roster {new['roster']!r}, this roster is {p['roster']!r}")
                p = merge_progress(p, new)
                had, now = sum(1 for v in before["checks"].values() if v), sum(1 for v in p["checks"].values() if v)
                if not a.force and not a.dry_run and had - now >= 5 and now < had / 2:
                    sys.exit(f"this file would untick {had - now} of {had} checks (a partial export?). Run with --dry-run to see the changes, or --force to merge anyway.")
            for line in progress_diff(before, p): print(("would: " if a.dry_run else "") + line)
            if a.dry_run:
                return 0
            bk = backup_progress()
            if bk: print("backup:", os.path.relpath(bk, ROOT))
        elif a.cmd == "import-addon":
            p, lines = import_addon(cfg, p, open(a.savedvars, encoding="utf-8", errors="replace").read(), a.force, a.db)
            print("\n".join(lines))
            if a.dry_run: return 0
        p["updated"] = today()
        save_progress(p)
        print("saved progress/progress.json; run ./mc generate to bake it into the page")
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
