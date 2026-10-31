"""Unit tests for the mc CLI. Run: python3 -m unittest discover -s tests -v"""
import contextlib, copy, io, json, os, re, subprocess, sys, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import mc  # noqa: E402

G = mc.Game()
EX = mc.load_config(os.path.join(ROOT, "config", "examples", "alliance.json"))
HORDE = mc.load_config(os.path.join(ROOT, "config", "examples", "horde.json"))


def cfg_with(**changes):
    c = copy.deepcopy(EX)
    for i, ch in changes.get("chars", {}).items():
        c["characters"][i].update(ch)
    for k, v in changes.items():
        if k != "chars":
            c[k] = v
    return c


class Validate(unittest.TestCase):
    def test_examples_clean(self):
        for cfg in (EX, HORDE):
            e, w, _ = mc.validate(cfg, G)
            self.assertEqual((e, w), ([], []))

    def test_bad_combo(self):
        e, _, _ = mc.validate(cfg_with(chars={0: {"race": "Gnome", "class": "Paladin"}}), G)
        self.assertTrue(any("cannot be a Paladin" in x for x in e))

    def test_faction_mismatch(self):
        e, _, _ = mc.validate(cfg_with(chars={0: {"race": "Orc"}}), G)
        self.assertTrue(any("is Horde" in x for x in e))

    def test_skyborne_sides(self):
        e, _, _ = mc.validate(cfg_with(chars={0: {"race": "High Order Skyborne", "class": "Shaman", "leveling_spec": "Enhancement", "endgame_spec": "Restoration"}}), G)
        self.assertTrue(any("cannot be a Shaman" in x for x in e))

    def test_three_characters_allowed(self):
        c = copy.deepcopy(EX)
        c["characters"] = c["characters"][:3]
        e, _, i = mc.validate(c, G)
        self.assertEqual(e, [])
        self.assertTrue(any("four is the recommended" in x for x in i))

    def test_three_primaries(self):
        e, _, _ = mc.validate(cfg_with(chars={1: {"professions": [{"name": "Herbalism", "from": 1}, {"name": "Alchemy", "from": 1}, {"name": "Mining", "from": 5}]}}), G)
        self.assertTrue(any("three primary" in x for x in e))

    def test_gap_and_duplicate(self):
        _, w, _ = mc.validate(cfg_with(chars={3: {"professions": [{"name": "Tailoring", "from": 1}, {"name": "Alchemy", "from": 1}]}}), G)
        self.assertTrue(any(x.startswith("gap: no character takes Enchanting") for x in w))
        self.assertTrue(any(x.startswith("duplicate: Alchemy") for x in w))

    def test_duplicate_class(self):
        _, w, _ = mc.validate(cfg_with(chars={1: {"race": "Human", "class": "Warrior", "leveling_spec": "Arms", "endgame_spec": "Fury"}}), G)
        self.assertTrue(any("duplicate class" in x for x in w))

    def test_spec_must_match_class(self):
        e, _, _ = mc.validate(cfg_with(chars={0: {"leveling_spec": "Frost"}}), G)
        self.assertTrue(any("not a Warrior spec" in x for x in e))


class Plan(unittest.TestCase):
    def test_ids_unique_and_stable(self):
        p1, p2 = mc.build_plan(EX, G), mc.build_plan(copy.deepcopy(EX), G)
        ids = [i["id"] for b in p1["brackets"] for t in b["tasks"].values() for i in t]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(ids, [i["id"] for b in p2["brackets"] for t in b["tasks"].values() for i in t])

    def test_legacy_projection(self):
        p = mc.build_plan(EX, G)
        self.assertEqual(p["coverage"]["legacy_from_plan"], 30)
        self.assertEqual(p["coverage"]["projection"][-1]["points"], 30)

    def test_faction_filters(self):
        a, h = mc.build_plan(EX, G), mc.build_plan(HORDE, G)
        an = {d["name"] for d in a["dungeons"]}
        hn = {d["name"] for d in h["dungeons"]}
        self.assertIn("The Hall of Thanes", an)
        self.assertNotIn("Ragefire Chasm", an)
        self.assertIn("Ruins of Lordaeron", an)  # needed for Novice Spelunker, enemy territory
        self.assertIn("Ragefire Chasm", hn)
        self.assertNotIn("The Stockade", hn)
        self.assertNotIn("Westfall", {z["name"] for z in h["zones"]})
        self.assertNotIn("The Barrens", {z["name"] for z in a["zones"]})

    def test_class_milestones_respect_faction(self):
        h = mc.build_plan(HORDE, G)
        pal = [c for c in h["characters"] if c["class"] == "Paladin"][0]
        names = [m["name"] for m in pal["milestones"]]
        self.assertIn("A Forsaken Paladin's First Lessons", names)
        self.assertNotIn("Verigan's Fist", names)

    def test_every_task_name_links(self):
        p = mc.build_plan(EX, G)
        for c in p["characters"]:
            for m in c["milestones"]:
                self.assertIn(m["name"], p["links"])
        for d in p["dungeons"]:
            self.assertIn(d["name"], p["links"])


class Progress(unittest.TestCase):
    def test_merge_keeps_higher(self):
        p = mc.empty_progress(EX)
        p["levels"]["aldric"]["level"] = 20
        mc.merge_progress(p, {"checks": {"a": True, "b": False}, "levels": {"aldric": {"level": 12}, "elowen": {"level": 9}}, "skills": {"elowen": {"Alchemy": 40}}})
        self.assertEqual(p["checks"], {"a": True})
        self.assertEqual(p["levels"]["aldric"]["level"], 20)
        self.assertEqual(p["levels"]["elowen"]["level"], 9)
        self.assertEqual(p["skills"]["elowen"]["Alchemy"], 40)

    def test_unknown_keys_survive(self):
        p = mc.empty_progress(EX)
        mc.merge_progress(p, {"moves": {"x": 1}})
        self.assertEqual(p["moves"], {"x": 1})
        with tempfile.TemporaryDirectory() as d:
            f = os.path.join(d, "p.json")
            mc.save_progress(p, f)
            self.assertEqual(mc.load_progress(EX, f)["moves"], {"x": 1})

    def test_import_addon_sample(self):
        sample = open(os.path.join(ROOT, "addon", "test", "SavedVariables.sample.lua"), encoding="utf-8").read()
        p = mc.empty_progress(EX)
        p, lines = mc.import_addon(EX, p, sample)
        self.assertEqual(p["levels"]["aldric"]["level"], 12)
        self.assertEqual(p["skills"]["aldric"]["Mining"], 45)
        self.assertEqual(p["levels"]["elowen"]["level"], 10)
        # second import is a no-op
        _, lines2 = mc.import_addon(EX, p, sample)
        self.assertTrue(all("unchanged" in x for x in lines2))

    def test_import_addon_db_name(self):
        sample = open(os.path.join(ROOT, "addon", "test", "SavedVariables.sample.lua"), encoding="utf-8").read()
        renamed = sample.replace("LegacyTrackerDB", "MyTrackerDB")
        with self.assertRaises(SystemExit):
            mc.import_addon(EX, mc.empty_progress(EX), renamed)
        p, _ = mc.import_addon(EX, mc.empty_progress(EX), renamed, db_name="MyTrackerDB")
        self.assertEqual(p["levels"]["aldric"]["level"], 12)

    def test_import_addon_mapping(self):
        sample = open(os.path.join(ROOT, "addon", "test", "SavedVariables.sample.lua"), encoding="utf-8").read()
        sample = sample.replace('"Aldric"', '"Aldricthebold"').replace("ExampleRealm-Aldric", "ExampleRealm-Aldricthebold")
        p = mc.empty_progress(EX)
        _, lines = mc.import_addon(EX, p, sample)
        self.assertTrue(any("not on the roster" in x for x in lines))
        p["map"]["Aldricthebold"] = "aldric"
        p, _ = mc.import_addon(EX, p, sample)
        self.assertEqual(p["levels"]["aldric"]["level"], 12)


class Strict(unittest.TestCase):
    def test_unknown_fields_rejected(self):
        c = cfg_with(bogus_top=1)
        c["characters"][0]["leveling_spac"] = "Arms"
        e, _, _ = mc.validate(c, G)
        self.assertTrue(any("unknown field 'bogus_top'" in x for x in e))
        self.assertTrue(any("'leveling_spac'" in x and "leveling_spec" in x for x in e))

    def test_until_range_and_empty_name(self):
        c = copy.deepcopy(EX)
        c["characters"][0]["professions"][0]["until"] = 999
        c["characters"][1]["name"] = ""
        e, _, _ = mc.validate(c, G)
        self.assertTrue(any("until" in x and "999" in x for x in e))
        self.assertTrue(any("name is empty" in x for x in e))

    def test_train_at_60(self):
        p = mc.build_plan(EX, G)
        last = p["brackets"][-1]["tasks"]["aldric"]
        self.assertTrue(any(t["text"] == "Swap Mining for Engineering" for t in last))

    def test_dropped_craft_targets_not_counted(self):
        c = copy.deepcopy(EX)
        c["characters"][1]["professions"] = [{"name": "Herbalism", "from": 1}, {"name": "Alchemy", "from": 1, "until": 30}, {"name": "Skinning", "from": 30}]
        _, w, _ = mc.validate(c, G)
        self.assertTrue(any("Alchemy is dropped at 30" in x and "225/300" in x for x in w))
        p = mc.build_plan(c, G)
        texts = [t["text"] for b in p["brackets"] for t in b["tasks"]["elowen"]]
        self.assertIn("Alchemy to 150", texts)
        self.assertNotIn("Alchemy to 300", texts)
        self.assertEqual(p["coverage"]["legacy_from_plan"], 28)
        self.assertEqual(p["coverage"]["projection"][-1]["points"], 28)

    def test_starter_dungeons_come_from_data(self):
        starters = [d for d in G.world["dungeons"] if d.get("starter")]
        self.assertEqual(sorted(d["access"] for d in starters), ["Alliance", "Horde"])
        g2 = mc.Game()
        for d in g2.world["dungeons"]:
            if d["name"] == "Ragefire Chasm":
                d["name"] = "Ragefire Chasm Renamed"
        names = [d["name"] for d in mc.build_plan(EX, g2)["dungeons"]]
        self.assertNotIn("Ragefire Chasm Renamed", names)

    def run_mc(self, *args):
        ex = os.path.join(ROOT, "config", "examples", "alliance.json")
        return subprocess.run([sys.executable, os.path.join(ROOT, "mc"), *args, "--config", ex], capture_output=True, text=True, cwd=ROOT)

    def test_cli_skill_and_check_guards(self):
        r = self.run_mc("skill", "aldric", "Mining", "999")
        self.assertNotEqual(r.returncode, 0); self.assertIn("0-300", r.stderr)
        r = self.run_mc("check", "bogus-id-123")
        self.assertNotEqual(r.returncode, 0); self.assertIn("unknown checklist id", r.stderr)


class RosterSize(unittest.TestCase):
    EXTRA = [
        {"name": "Brunhild", "race": "Dwarf", "class": "Paladin", "professions": [{"name": "Mining"}, {"name": "Herbalism"}]},
        {"name": "Selwyn", "race": "Human", "class": "Priest", "professions": [{"name": "Herbalism"}, {"name": "Skinning"}]},
    ]

    def roster(self, n):
        c = copy.deepcopy(EX)
        c["characters"] = (c["characters"] + copy.deepcopy(self.EXTRA))[:n]
        return mc.normalize(c)

    def test_sizes_validate_and_plan(self):
        for n in (1, 2, 3, 4, 5, 6):
            c = self.roster(n)
            e, w, i = mc.validate(c, G)
            self.assertEqual(e, [], (n, e))
            if n < 3:
                self.assertFalse(any(x.startswith("gap:") for x in w), (n, w))
            if n != 4:
                self.assertTrue(any("four is the recommended" in x for x in i))
            p = mc.build_plan(c, G)
            self.assertEqual(len(p["characters"]), n)
            ids = [t["id"] for b in p["brackets"] for tl in b["tasks"].values() for t in tl]
            self.assertEqual(len(ids), len(set(ids)))
            self.assertEqual(len(p["brackets"][0]["rotation"]), n)

    def test_bounds(self):
        c = copy.deepcopy(EX); c["characters"] = []
        self.assertTrue(any("1 to 10" in x for x in mc.validate(c, G)[0]))
        c = self.roster(4); c["characters"] = [dict(c["characters"][0], name=f"Alt{chr(97 + i)}", id=f"alt{i}") for i in range(11)]
        self.assertTrue(any("1 to 10" in x for x in mc.validate(c, G)[0]))

    def test_four_unchanged(self):
        self.assertEqual(mc.build_plan(EX, G)["roster"]["key"], mc.roster_key(EX))
        self.assertEqual(mc.validate(EX, G), ([], [], []))

    def test_init_count(self):
        ans = {"roster_name": "Duo", "faction": "Alliance", "ruleset": "Normal", "count": "2",
               "c1.name": "Aldric", "c1.race": "Human", "c1.class": "Warrior", "c2.name": "Elowen", "c2.race": "Night Elf", "c2.class": "Druid"}
        cfg = mc.interview(ans)
        self.assertEqual(len(cfg["characters"]), 2)
        self.assertEqual(len(mc.interview({k: v for k, v in ans.items() if k != "count"})["characters"]), 4)


class InitFaction(unittest.TestCase):
    def test_faction_case_and_space(self):
        for f in ("alliance", "ALLIANCE", " Horde "):
            cfg = mc.interview({"faction": f, "ruleset": "normal", "count": "1"})
            self.assertIn(cfg["faction"], ("Alliance", "Horde"))
            self.assertEqual(cfg["ruleset"], "Normal")
            self.assertEqual(mc.validate(mc.normalize(cfg), G)[0], [])

    def test_bad_faction_no_crash(self):
        cfg = mc.interview({"faction": "", "count": "1"})
        self.assertTrue(mc.validate(cfg, G)[0])


class SpelunkerNames(unittest.TestCase):
    def test_tier_criteria_match_world(self):
        names = {d["name"] for d in G.world["dungeons"]}
        for tv in G.legacy["challenges"]["dungeon"]["tiers"].values():
            for crit in tv["criteria"]:
                for alt in crit.split(" or "):
                    self.assertTrue(alt in names or alt.split(": ")[0] in names, alt)


class CraftDue(unittest.TestCase):
    # #49: no craft target or projected point before the craft is trained
    def plan(self, start, until=None):
        c = mc.load_config(mc.EXAMPLE)
        p = c["characters"][1]["professions"][1]
        p["from"] = start
        if until:
            p["until"] = until
        self.assertEqual(mc.validate(c, G)[0], [])
        return mc.build_plan(c, G)

    def test_late_starts(self):
        lo = {b["id"]: int(b["id"].split("-")[0]) for b in self.plan(1)["brackets"]}
        for start in (26, 33, 40, 51):
            p = self.plan(start)
            for b in p["brackets"]:
                for t in b["tasks"]["elowen"]:
                    if t["text"].startswith("Alchemy to"):
                        self.assertGreaterEqual(int(b["id"].split("-")[1]), start, (start, b["id"], t["text"]))
                        self.assertTrue(lo[b["id"]] <= start or b["id"] != "1-10")
            train = [b["id"] for b in p["brackets"] for t in b["tasks"]["elowen"] if t["text"] == "Train Alchemy"][0]
            first = [b["id"] for b in p["brackets"] for t in b["tasks"]["elowen"] if t["text"] == "Alchemy to 150"][0]
            self.assertEqual(train, first, start)

    def test_dropped_before_later_target(self):
        p = self.plan(40, until=50)
        texts = [t["text"] for b in p["brackets"] for t in b["tasks"]["elowen"]]
        self.assertIn("Alchemy to 225", texts)
        self.assertNotIn("Alchemy to 300", texts)

    def test_projection_not_early(self):
        base = self.plan(1)["coverage"]["projection"]
        late = self.plan(40)["coverage"]["projection"]
        self.assertEqual(late[4]["at"], "26-32")
        self.assertEqual(late[4]["points"], base[4]["points"] - 2)  # Alchemy 150/225 not before 40
        self.assertEqual(late[5]["points"], base[5]["points"] - 2)  # 32-40 still before training
        self.assertEqual(late[6]["points"], base[6]["points"])      # 40-45 trained and caught up

    def test_projection_matches_tasks(self):
        # #64: a target due the level the craft is trained (start 32 or 52) counts where its task is, never earlier
        c = mc.load_config(mc.EXAMPLE)
        self.assertEqual([ch["id"] for ch in c["characters"] if any(p["name"] == "Alchemy" for p in ch["professions"])], ["elowen"])
        c["characters"][1]["professions"][1]["until"] = 2
        none = [x["points"] for x in mc.build_plan(c, G)["coverage"]["projection"]]
        for start in (1, 24, 25, 26, 31, 32, 33, 40, 51, 52, 53, 59):
            p = self.plan(start)
            run, want = 0, []
            for b in p["brackets"]:
                run += sum(1 for t in b["tasks"]["elowen"] if t["text"].startswith("Alchemy to"))
                want.append(run)
            got = [x["points"] - n for x, n in zip(p["coverage"]["projection"], none)]
            self.assertEqual(got, want, start)
        p = self.plan(32)
        self.assertEqual([t["text"] for b in p["brackets"] if b["id"] == "26-32" for t in b["tasks"]["elowen"] if "Alchemy" in t["text"]], [])
        self.assertEqual(p["coverage"]["projection"][4]["points"], none[4])

    def test_markdown_breakdown_matches_total(self):
        # #68: 0, 1, 2 and 3 reachable Alchemy targets, plus the standard roster
        for until, cp in ((20, 15), (30, 16), (40, 17), (None, 18)):
            c = mc.load_config(mc.EXAMPLE)
            if until:
                c["characters"][1]["professions"][1]["until"] = until
            p = mc.build_plan(c, G)
            cv = p["coverage"]
            self.assertEqual(cv["craft_points"], cp, until)
            self.assertEqual(cv["legacy_from_plan"], cv["distinct_classes"] * 3 + cp)
            line = [l for l in mc.plan_markdown(p).splitlines() if l.startswith("Legacy points from this plan")][0]
            nums = [int(x) for x in re.findall(r"\d+", line)]
            if until:
                self.assertIn(f"{cp} craft targets reachable across {cv['crafts_covered']} crafts", line)
                self.assertEqual(nums[0], nums[1] * nums[2] + nums[3])
            else:
                self.assertIn(f"{cv['crafts_covered']} crafts x 3", line)
                self.assertEqual(nums[0], nums[1] * nums[2] + nums[3] * nums[4])

    def test_early_and_60_unchanged(self):
        self.assertEqual(mc.craft_due(25, 1), 25)
        self.assertEqual(mc.craft_due(25, 52), 52)
        self.assertEqual(mc.craft_due(52, 60), 60)


class RosterStructure(unittest.TestCase):
    # #53: malformed but parseable rosters give errors, not tracebacks
    def cases(self):
        def ch(f):
            c = copy.deepcopy(mc.load_json(mc.EXAMPLE)); f(c); return c
        return [
            ch(lambda c: c["characters"][0]["professions"][0].__setitem__("from", "later")),
            ch(lambda c: c["characters"][0]["professions"].append({})),
            ch(lambda c: c["characters"].append("oops")),
            ch(lambda c: c.__setitem__("characters", {"a": 1})),
            ch(lambda c: c["characters"][0].__setitem__("professions", "Mining")),
            [],
            # #63: scalar fields with the wrong type
            ch(lambda c: (c["characters"][0].__setitem__("name", 12), c["characters"][0].pop("id", None))),
            ch(lambda c: (c["characters"][0].__setitem__("name", None), c["characters"][0].pop("id", None))),
            ch(lambda c: c["characters"][0].__setitem__("name", ["Aldric"])),
            ch(lambda c: (c["characters"][0].__setitem__("name", 12), c["characters"][0].__setitem__("id", "aldric"))),
            ch(lambda c: c["characters"][0].__setitem__("race", [])),
            ch(lambda c: c["characters"][0].__setitem__("class", {})),
            ch(lambda c: c["characters"][0].__setitem__("id", 7)),
            ch(lambda c: c.__setitem__("faction", ["Alliance"])),
        ]

    def test_scalar_type_messages(self):
        c = copy.deepcopy(mc.load_json(mc.EXAMPLE)); c["characters"][0]["race"] = []
        self.assertIn("roster.characters[0].race must be a string, got []", mc.structure_errors(c))

    def test_generate_rejects_before_writing(self):
        c = copy.deepcopy(mc.load_json(mc.EXAMPLE)); c["characters"][0]["class"] = {}
        out = os.path.join(mc.ROOT, "build", "PLAN.md")
        before = open(out, encoding="utf-8").read() if os.path.exists(out) else None
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(c, f)
        r = subprocess.run([sys.executable, os.path.join(mc.ROOT, "scripts", "mc.py"), "generate", "--config", f.name], capture_output=True, text=True)
        os.unlink(f.name)
        self.assertNotEqual(r.returncode, 0); self.assertNotIn("Traceback", r.stderr)
        self.assertIn("class must be a string", r.stderr + r.stdout)
        self.assertEqual(before, open(out, encoding="utf-8").read() if os.path.exists(out) else None)

    def test_errors_not_exceptions(self):
        for raw in self.cases():
            e, _, _ = mc.validate(mc.normalize(raw), G)
            self.assertTrue(e, raw if not isinstance(raw, dict) else "")

    def test_cli_exits_cleanly(self):
        for raw in self.cases():
            with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
                json.dump(raw, f)
            r = subprocess.run([sys.executable, os.path.join(mc.ROOT, "scripts", "mc.py"), "validate", "--config", f.name], capture_output=True, text=True)
            os.unlink(f.name)
            self.assertNotEqual(r.returncode, 0)
            self.assertNotIn("Traceback", r.stderr)


class LegacyTracking(unittest.TestCase):
    def test_account_reaches_full_total(self):
        p = mc.build_plan(EX, G)
        ch = G.legacy["challenges"]
        pvp = [a for a in p["account"] if a["tag"] == "PvP"]
        self.assertEqual(len(pvp), ch["pvp"]["total"])
        self.assertEqual(len(p["account"]), ch["pvp"]["total"] + ch["dungeon"]["total"] + ch["raid"]["total"] + ch["adventure"]["total"])
        self.assertEqual(p["flight_paths_status"], G.world["flight_paths_status"])
        md = mc.plan_markdown(p)
        self.assertIn(G.legacy["claim_at"]["coords"], md)

    def test_spelunker_criteria(self):
        acct = {a["id"]: a for a in mc.build_plan(EX, G)["account"]}
        self.assertTrue(acct["acct-spelunker-novice"]["detail"].startswith("All 6: "))
        self.assertIn("Scarlet Monastery: Cathedral", acct["acct-spelunker-experienced"]["detail"])
        self.assertTrue(acct["acct-spelunker-master"]["detail"].startswith("All 17: "))

    def test_unknown_quest_counts_rank_last(self):
        p = mc.build_plan(EX, G)
        unknown = {z["name"] for z in G.world["zones"] if z["quests"].get("Alliance") is None}
        for b in p["brackets"]:
            seen_unknown = False
            for z in b["zones"]:
                if z in unknown: seen_unknown = True
                else: self.assertFalse(seen_unknown and b["from"] > 1, f"{b['id']}: known zone after unknown")


class ProgressSafety(unittest.TestCase):
    def base(self):
        p = mc.empty_progress(EX)
        p["checks"] = {"a": True, "b": True}
        p["levels"]["aldric"].update({"level": 20, "updated": "2026-11-05"})
        p["skills"]["aldric"] = {"Mining": 120}
        p["map"] = {"Aldricthebold": "aldric"}
        return p

    def test_page_stamp_lowers_level_and_skill(self):
        p = self.base()
        later = mc._rec_time(p["levels"]["aldric"]) + 1000
        mc.merge_progress(p, {"levels": {"aldric": {"level": 12, "updated": "2026-11-06"}}, "skills": {"aldric": {"Mining": 80}},
                              "stamp": {"l:aldric": later, "s:aldric:Mining": later}})
        self.assertEqual(p["levels"]["aldric"]["level"], 12)
        self.assertEqual(p["skills"]["aldric"]["Mining"], 80)

    def test_unstamped_still_keeps_higher(self):
        p = self.base()
        mc.merge_progress(p, {"levels": {"aldric": {"level": 12}}, "skills": {"aldric": {"Mining": 80}}})
        self.assertEqual((p["levels"]["aldric"]["level"], p["skills"]["aldric"]["Mining"]), (20, 120))

    def test_stored_stamp_beats_stale_export(self):
        # #41: a stamped edit already stored is not undone by an older, unstamped export
        p = self.base()
        t = mc._rec_time({"updated": "2026-11-06"})
        mc.merge_progress(p, {"updated": "2026-11-06", "checks": {"b": True}, "levels": {"aldric": {"level": 12, "updated": "2026-11-06"}},
                              "skills": {"aldric": {"Mining": 80}}, "notes": "fixed",
                              "stamp": {"c:a": t, "l:aldric": t, "s:aldric:Mining": t, "n": t}})
        stale = {"updated": "2026-11-05", "checks": {"a": True, "b": True}, "levels": {"aldric": {"level": 20, "updated": "2026-11-05"}},
                 "skills": {"aldric": {"Mining": 120}}, "notes": "old"}
        mc.merge_progress(p, stale)
        self.assertNotIn("a", p["checks"])
        self.assertTrue(p["checks"]["b"])
        self.assertEqual(p["levels"]["aldric"]["level"], 12)
        self.assertEqual(p["skills"]["aldric"]["Mining"], 80)
        self.assertEqual(p["notes"], "fixed")
        # newer unstamped data (a later addon read) still goes through
        mc.merge_progress(p, {"updated": "2026-11-08", "checks": {"b": True, "c": True}, "levels": {"aldric": {"level": 22, "lastSeenEpoch": t // 1000 + 86400 * 2}}})
        self.assertEqual(p["levels"]["aldric"]["level"], 22)
        self.assertTrue(p["checks"].get("c"))
        self.assertNotIn("a", p["checks"])

    def test_older_incoming_check_stamp_loses(self):
        p = self.base()
        mc.merge_progress(p, {"checks": {"b": True}, "stamp": {"c:a": 2000}})
        mc.merge_progress(p, {"checks": {"a": True, "b": True}, "stamp": {"c:a": 1000}})
        self.assertNotIn("a", p["checks"])

    def test_map_survives_merge(self):
        p = self.base()
        mc.merge_progress(p, {"map": {"SomeAlt": "elowen"}})
        self.assertEqual(p["map"], {"Aldricthebold": "aldric", "SomeAlt": "elowen"})

    def test_diff_and_backup(self):
        old = self.base(); new = copy.deepcopy(old)
        new["checks"].pop("b"); new["levels"]["aldric"]["level"] = 21
        d = "\n".join(mc.progress_diff(old, new))
        self.assertIn("-1 check(s): b", d); self.assertIn("level 20 -> 21", d)
        with tempfile.TemporaryDirectory() as t:
            path = os.path.join(t, "progress.json")
            self.assertIsNone(mc.backup_progress(path))
            mc.write_json(path, old)
            bk = mc.backup_progress(path)
            self.assertTrue(bk.startswith(os.path.join(t, "backups")))
            self.assertEqual(json.load(open(bk, encoding="utf-8"))["checks"], old["checks"])

    def test_cli_reset_needs_force_and_merge_dry_run(self):
        ex = os.path.join(ROOT, "config", "examples", "alliance.json")
        r = subprocess.run([sys.executable, os.path.join(ROOT, "mc"), "progress", "reset", "--config", ex], capture_output=True, text=True, cwd=ROOT)
        self.assertNotEqual(r.returncode, 0); self.assertIn("--force", r.stderr)
        with tempfile.TemporaryDirectory() as t:
            f = os.path.join(t, "x.json")
            mc.write_json(f, {"levels": {"aldric": {"level": 7}}})
            r = subprocess.run([sys.executable, os.path.join(ROOT, "mc"), "progress", "merge", f, "--dry-run", "--config", ex], capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(r.returncode, 0, r.stderr); self.assertIn("would: aldric: level", r.stdout)
        self.assertFalse(os.path.exists(mc.PROGRESS) and "level\": 7" in open(mc.PROGRESS, encoding="utf-8").read())


class ProgressProtocol(unittest.TestCase):
    EXP = os.path.join(ROOT, "config", "examples", "alliance.json")

    def cli(self, p, *args):
        """Run an mc progress command against p in memory; returns the saved progress."""
        from unittest import mock
        saved = {}
        with mock.patch.object(mc, "load_progress", lambda cfg, path=None: p), \
             mock.patch.object(mc, "save_progress", lambda q, path=None: saved.update(q)), \
             mock.patch.object(mc, "backup_progress", lambda path=None: None), \
             contextlib.redirect_stdout(io.StringIO()):
            mc.main([*args, "--config", self.EXP])
        return saved

    def test_cli_untick_beats_older_page_stamp(self):
        # #50: a later ./mc check --off survives an older page export of the same tick
        t0 = mc.now_ms() - 60000
        p = mc.empty_progress(EX)
        p["checks"]["a"] = True; p["stamp"] = {"c:a": t0}
        q = self.cli(p, "check", "a", "--off", "--force")
        self.assertGreater(q["stamp"]["c:a"], t0)
        mc.merge_progress(q, {"updated": mc.today(), "checks": {"a": True}, "stamp": {"c:a": t0}})
        self.assertNotIn("a", q["checks"])
        # a genuinely later page edit still wins
        mc.merge_progress(q, {"checks": {"a": True}, "stamp": {"c:a": q["stamp"]["c:a"] + 1000}})
        self.assertTrue(q["checks"]["a"])

    def test_cli_level_and_skill_stamped(self):
        p = mc.empty_progress(EX)
        p["levels"]["aldric"] = {"level": 30, "rested": "Full", "lastSeenEpoch": 1700000000, "updated": "2023-11-14", "source": "LegacyTracker"}
        q = self.cli(p, "level", "aldric", "28")
        self.assertIn("l:aldric", q["stamp"])
        # an older unstamped addon share (newer than the old addon data, older than the correction) can't undo it
        mc.merge_progress(q, {"levels": {"aldric": {"level": 30, "lastSeenEpoch": 1700000500, "updated": "2023-11-14"}}})
        self.assertEqual(q["levels"]["aldric"]["level"], 28)
        q = self.cli(q, "skill", "aldric", "mining", "100")
        self.assertIn("s:aldric:Mining", q["stamp"])
        mc.merge_progress(q, {"skills": {"aldric": {"Mining": 150}}, "updated": "2023-11-14"})
        self.assertEqual(q["skills"]["aldric"]["Mining"], 100)

    def test_addon_import_respects_later_manual_level(self):
        p = mc.empty_progress(EX)
        p["stamp"] = {"l:aldric": 1800000000 * 1000}
        text = 'LegacyTrackerDB = { chars = { ["R-Aldric"] = {name="Aldric", level=40, lastSeen=1700000000} } }'
        _, out = mc.import_addon(EX, p, text)
        self.assertTrue(any("later manual" in x for x in out))
        self.assertNotEqual(p["levels"]["aldric"].get("level"), 40)

    def test_merge_skips_stale_addon_record(self):
        # #55
        p = mc.empty_progress(EX)
        p["levels"]["aldric"] = {"level": 20, "rested": "Full", "lastSeenEpoch": 200, "updated": "2026-11-07"}
        mc.merge_progress(p, {"levels": {"aldric": {"level": 20, "rested": "Empty", "lastSeenEpoch": 100, "updated": "2026-11-06"}}})
        self.assertEqual((p["levels"]["aldric"]["rested"], p["levels"]["aldric"]["lastSeenEpoch"]), ("Full", 200))
        mc.merge_progress(p, {"levels": {"aldric": {"level": 20, "rested": "Empty", "lastSeenEpoch": 200}}})
        self.assertEqual(p["levels"]["aldric"]["rested"], "Full", "equal epoch is not newer")
        mc.merge_progress(p, {"levels": {"aldric": {"level": 20, "rested": "Partial", "lastSeenEpoch": 300}}})
        self.assertEqual(p["levels"]["aldric"]["rested"], "Partial", "a newer same-level snapshot updates")
        mc.merge_progress(p, {"levels": {"aldric": {"level": 21, "updated": "2026-11-08"}}})
        self.assertEqual(p["levels"]["aldric"]["level"], 21, "records with no addon time follow the level rule")

    def test_progress_errors(self):
        # #54
        self.assertEqual(mc.progress_errors({"levels": {"aldric": {"level": 12, "rested": "Partial"}}, "skills": {"aldric": {"Mining": 45}}}), [])
        self.assertEqual(mc.progress_errors({"version": 1, "roster": "x", "updated": "2026-11-06", "checks": {"a": True, "b": False}, "map": {}, "stamp": {"c:a": 1}}), [])
        for bad, frag in ((["x"], "JSON object"), ({"levels": {"aldric": {"level": 1, "updated": "2026-11-06", "rested": {}}}}, "rested"),
                          ({"levels": []}, "levels: must be an object"), ({"levels": {"aldric": {"level": 61}}}, "1-60"),
                          ({"levels": {"aldric": {"level": "12"}}}, "1-60"), ({"skills": {"aldric": {"Mining": 400}}}, "0-300"),
                          ({"checks": {"a": "yes"}}, "checks.a"), ({"version": 2}, "version"), ({"stamp": {"c:a": "x"}}, "stamp")):
            errs = mc.progress_errors(bad)
            self.assertTrue(any(frag in e for e in errs), (bad, errs))

    def test_cli_merge_rejects_invalid_without_saving(self):
        p = mc.empty_progress(EX)
        with tempfile.TemporaryDirectory() as t:
            f = os.path.join(t, "bad.json")
            mc.write_json(f, {"levels": {"aldric": {"level": 1, "updated": "2026-11-06", "rested": {}}}})
            with self.assertRaises(SystemExit) as cm:
                self.cli(p, "progress", "merge", f)
            self.assertIn("rested", str(cm.exception.code))
        self.assertEqual(p["levels"]["aldric"]["rested"], "Empty")


class AuditProgress(unittest.TestCase):
    def lua(self, level=20, rank=None, seen=1800000000, name="Aldric"):
        prof = "" if rank is None else ", professions={Mining={rank=%s}}" % rank
        return 'LegacyTrackerDB = { chars = { ["R-%s"] = {name="%s", level=%s, lastSeen=%d%s} } }' % (name, name, level, seen, prof)

    def test_addon_ranges_rejected(self):
        # #61: import-addon and scrub-addon skip out-of-range records and say why
        for level, rank, frag in ((0, 10, "level 0"), (61, 10, "level 61"), (999, 10, "level 999"),
                                  (20, 301, "rank 301"), (20, 999, "rank 999"), (20, -5, "rank -5"), (20, "1e309", "rank inf")):
            p = mc.empty_progress(EX)
            _, out = mc.import_addon(EX, p, self.lua(level, rank))
            self.assertTrue(any(x.startswith("skip aldric: invalid") and frag in x for x in out), (level, rank, out))
            self.assertEqual(p["levels"]["aldric"].get("level"), 1)
            self.assertEqual(mc.progress_errors(p), [])
            sh, _ = mc.scrub_addon(EX, self.lua(level, rank), mapping={})
            self.assertNotIn("aldric", sh["levels"]); self.assertNotIn("aldric", sh["skills"])
        p = mc.empty_progress(EX)
        mc.import_addon(EX, p, self.lua(20, 75))
        self.assertEqual((p["levels"]["aldric"]["level"], p["skills"]["aldric"]["Mining"]), (20, 75))

    def test_generate_refuses_invalid_saved_progress(self):
        from unittest import mock
        bad = mc.empty_progress(EX); bad["levels"]["aldric"]["level"] = 999
        with mock.patch.object(mc, "load_progress", lambda cfg, path=None: bad):
            with self.assertRaises(SystemExit) as cm:
                mc.outputs(mc.EXAMPLE, personal=True)
        self.assertIn("levels.aldric.level", str(cm.exception.code))

    def test_newer_addon_skill_beats_older_manual_edit(self):
        # #62: CLI import and JSON merge use the snapshot time for skills
        t = 1800000000
        for later, want in ((t + 3600, 100), (t - 3600, 10)):
            p = mc.empty_progress(EX); p["skills"]["aldric"] = {"Mining": 10}; p["stamp"] = {"s:aldric:Mining": t * 1000}
            mc.import_addon(EX, p, self.lua(20, 100, later))
            self.assertEqual(p["skills"]["aldric"]["Mining"], want, later)
            q = mc.empty_progress(EX); q["skills"]["aldric"] = {"Mining": 10}; q["stamp"] = {"s:aldric:Mining": t * 1000}
            mc.merge_progress(q, {"levels": {"aldric": {"level": 20, "lastSeenEpoch": later}}, "skills": {"aldric": {"Mining": 100}}})
            self.assertEqual(q["skills"]["aldric"]["Mining"], want, later)
        r = mc.empty_progress(EX); r["skills"]["aldric"] = {"Mining": 120}
        mc.merge_progress(r, {"skills": {"aldric": {"Mining": 100}}})
        self.assertEqual(r["skills"]["aldric"]["Mining"], 120, "no ordering evidence: higher wins")

    def test_non_finite_numbers(self):
        # #65
        for txt in ('{"stamp":{"c:a":1e309}}', '{"levels":{"aldric":{"level":1e309}}}', '{"skills":{"aldric":{"Mining":-1e309}}}',
                    '{"stamp":{"c:a":NaN}}', '{"levels":{"aldric":{"pctToNext":Infinity}}}'):
            with self.assertRaises(ValueError):
                mc.loads_strict(txt)
        for blob in ({"stamp": {"c:a": float("inf")}}, {"levels": {"aldric": {"level": float("inf")}}},
                     {"skills": {"aldric": {"Mining": float("nan")}}}, {"levels": {"aldric": {"lastSeenEpoch": float("inf")}}}):
            self.assertTrue(mc.progress_errors(blob), blob)
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                mc.write_json(os.path.join(d, "x.json"), {"stamp": {"c:a": float("inf")}})
        p = mc.empty_progress(EX)
        with tempfile.TemporaryDirectory() as d:
            f = os.path.join(d, "x.json")
            open(f, "w").write('{"stamp":{"c:acct-explorer":1e309}}')
            with self.assertRaises(SystemExit) as cm:
                ProgressProtocol.cli(ProgressProtocol(), p, "progress", "merge", f)
            self.assertIn("out of range", str(cm.exception.code))
        self.assertNotIn("c:acct-explorer", p.get("stamp") or {})

class StatusAndNotes(unittest.TestCase):
    def test_racials_status_kept(self):
        # #66: racial ability status travels into the plan, separate from the combination status
        p = mc.build_plan(EX, G)
        c = p["characters"][0]
        self.assertEqual((c["racials_status"], c["racials_source"]), ("unverified", G.races["Human"]["racials_source"]))
        self.assertEqual(G.races["Human"]["status"], "beta")
        md = mc.plan_markdown(p)
        self.assertRegex(md, r"Aldric \(\[Human\]\([^)]*\)\) racials: .*The Human Spirit.*`Unverified`")
        g2 = mc.Game(); g2.races["Human"] = dict(g2.races["Human"], racials_status="confirmed")
        p2 = mc.build_plan(EX, g2)
        self.assertEqual(p2["characters"][0]["racials_status"], "confirmed")
        line = [l for l in mc.plan_markdown(p2).splitlines() if l.startswith("- Aldric (")][0]
        self.assertNotIn("`", line.split("racials:")[1].replace("](", ""))

    def tasks(self, plan, cid):
        return {t["text"]: t for b in plan["brackets"] for t in b["tasks"][cid]}

    def test_milestone_notes_in_tasks_and_markdown(self):
        # #67: recorded costs and trainer notes reach the checklist and Markdown, with their status
        p = mc.build_plan(EX, G)
        t = self.tasks(p, "aldric")
        self.assertEqual(t["Riding at 40"]["detail"], "Apprentice Riding: 100 gold, first mount included")
        self.assertEqual(t["Riding at 40"]["status"], "beta")
        self.assertEqual(t["Journeyman Riding at 60"]["detail"], "1,000 gold")
        self.assertEqual(t["Dual Specialization at 40"]["detail"], "Class trainer in a major city")
        self.assertNotIn("gold", t["Dual Specialization at 40"]["detail"])  # no invented price
        self.assertEqual(self.tasks(p, "brannoc")["Taming the Beast at 10"]["detail"], "Tame Beast and Call Pet at 10")
        md = mc.plan_markdown(p)
        self.assertRegex(md, r"Riding\]\([^)]*\) at 40 `Class`: Apprentice .*100 gold, first mount included `Seen in beta`")
        self.assertIn("1,000 gold `Seen in beta`", md)
        self.assertIn("Class trainer in a major city", md)
        # faction-specific class milestone note (Alliance Paladin), with its Classic data status
        pal = mc.build_plan(cfg_with(chars={0: {"class": "Paladin", "leveling_spec": "Retribution", "endgame_spec": "Holy"}}), G)
        vf = self.tasks(pal, "aldric")["Verigan's Fist at 20"]
        self.assertEqual((vf["detail"], vf["status"]), ("The Test of Righteousness chain", "classic"))
        self.assertRegex(mc.plan_markdown(pal), r"Test of Righteousness\]\([^)]*\) chain `Classic data`")
        # milestones without a note stay plain
        self.assertNotIn("detail", self.tasks(p, "aldric")["Defensive Stance at 10"])


class Safety(unittest.TestCase):
    EVIL = "Test</script><script>alert(1)</script><!-- & \u2028"

    def test_plan_js_cannot_break_out_of_script(self):
        c = cfg_with(roster_name=self.EVIL, chars={0: {"display": self.EVIL, "notes": self.EVIL}})
        plan = mc.build_plan(c, G)
        js = mc.web_js(plan)
        for bad in ("</script", "<script", "<!--", "\u2028"):
            self.assertNotIn(bad, js)
        self.assertEqual(json.loads(js.split("window.MC_PLAN = ", 1)[1].rstrip().rstrip(";"))["roster"]["name"], self.EVIL)

    def test_canvas_cannot_break_out(self):
        c = cfg_with(roster_name=self.EVIL)
        plan = mc.build_plan(c, G)
        plan["progress"] = mc.empty_progress(c)
        plan["progress"]["notes"] = self.EVIL
        tsx = mc.canvas_tsx(plan)
        self.assertNotIn("</script", tsx)
        self.assertNotIn("<!--", tsx)

    def addon(self, *recs):
        body = ",\n".join('["%s"] = {name="%s", level=%d, lastSeen=%d}' % r for r in recs)
        return "LegacyTrackerDB = {\n chars = {\n" + body + "\n }\n}\n"

    def test_realm_mapping_beats_bare_name(self):
        # #51
        p = mc.empty_progress(EX)
        p["map"]["OtherRealm-Aldric"] = "brannoc"
        mc.import_addon(EX, p, self.addon(("OtherRealm-Aldric", "Aldric", 50, 1800000000)))
        self.assertEqual(p["levels"]["brannoc"]["level"], 50)
        self.assertNotEqual(p["levels"]["aldric"].get("level"), 50)

    def test_realm_mapping_and_home_realm(self):
        p = mc.empty_progress(EX)
        p["map"]["OtherRealm-Aldric"] = "brannoc"
        mc.import_addon(EX, p, self.addon(("OtherRealm-Aldric", "Aldric", 50, 1800000000), ("Home-Aldric", "Aldric", 20, 1700000000)))
        self.assertEqual((p["levels"]["brannoc"]["level"], p["levels"]["aldric"]["level"]), (50, 20))

    def test_bare_alias_still_works(self):
        p = mc.empty_progress(EX)
        p["map"]["Renamed"] = "aldric"
        mc.import_addon(EX, p, self.addon(("Realm-Renamed", "Renamed", 12, 1800000000)))
        self.assertEqual(p["levels"]["aldric"]["level"], 12)

    def test_same_name_two_realms_is_ambiguous(self):
        p = mc.empty_progress(EX)
        _, out = mc.import_addon(EX, p, self.addon(("A-Aldric", "Aldric", 50, 1800000000), ("B-Aldric", "Aldric", 20, 1700000000)))
        self.assertTrue(any("ambiguous" in x for x in out))
        self.assertNotIn(p["levels"]["aldric"].get("level"), (50, 20))

    def test_scrub_uses_saved_mappings(self):
        # #52: renamed and realm-qualified mappings select characters; nothing else leaks
        text = self.addon(("Realm-Renamed", "Renamed", 12, 1800000000), ("Other-Elowen", "Elowen", 30, 1800000000), ("Realm-Stranger", "Stranger", 40, 1800000000))
        out, lines = mc.scrub_addon(EX, text, mapping={"Renamed": "aldric", "Other-Elowen": "brannoc"})
        self.assertEqual(out["levels"]["aldric"]["level"], 12)
        self.assertEqual(out["levels"]["brannoc"]["level"], 30)
        self.assertNotIn("elowen", out["levels"])
        blob = json.dumps(out)
        for bad in ("Stranger", "Realm", "Other-", "map", "checks", "notes"):
            self.assertNotIn(bad, blob)

    def test_scrub_addon_keeps_only_roster_progress(self):
        sample = open(os.path.join(ROOT, "addon", "test", "SavedVariables.sample.lua"), encoding="utf-8").read()
        sample = sample.replace('["level"] = 12,', '["level"] = 12,\n\t\t\t["money"] = 999999,\n\t\t\t["timePlayed"] = 77777,', 1)
        out, _ = mc.scrub_addon(EX, sample)
        text = json.dumps(out)
        for bad in ("money", "999999", "timePlayed", "77777", "ExampleRealm", "checks"):
            self.assertNotIn(bad, text)
        self.assertEqual(out["levels"]["aldric"]["level"], 12)
        p = mc.empty_progress(EX)
        p["checks"]["keep-me"] = True
        mc.merge_progress(p, out)
        self.assertTrue(p["checks"]["keep-me"], "a scrubbed share must not wipe ticks")
        self.assertEqual(p["levels"]["aldric"]["level"], 12)


class CLI(unittest.TestCase):
    def run_mc(self, *args):
        return subprocess.run([sys.executable, os.path.join(ROOT, "mc"), *args], capture_output=True, text=True, cwd=ROOT)

    def test_validate_strict_examples(self):
        for f in ("alliance", "horde"):
            r = self.run_mc("validate", "--strict", "--config", f"config/examples/{f}.json")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_init_answers(self):
        answers = {"roster_name": "Test", "faction": "Horde", "ruleset": "PvP"}
        for i, (n, r, c, pr) in enumerate([("Aa", "Orc", "Warrior", "Mining, Blacksmithing"), ("Bb", "Tauren", "Druid", "Herbalism, Alchemy"),
                                           ("Cc", "Undead", "Paladin", "Skinning, Leatherworking 10"), ("Dd", "Troll", "Mage", "Tailoring, Enchanting")]):
            answers.update({f"c{i + 1}.name": n, f"c{i + 1}.race": r, f"c{i + 1}.class": c, f"c{i + 1}.professions": pr})
        cfg = mc.normalize(mc.interview(answers))
        e, w, _ = mc.validate(cfg, G)
        self.assertEqual(e, [])
        self.assertTrue(any("Engineering" in x for x in w))
        self.assertEqual(cfg["characters"][2]["professions"][1], {"name": "Leatherworking", "from": 10})

    def test_doctor(self):
        r = self.run_mc("doctor")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


class Data(unittest.TestCase):
    def test_56_combos(self):
        self.assertEqual(sum(len(r["classes"]) for r in G.races.values()), 56)
        for fac in ("Alliance", "Horde"):
            self.assertEqual(sum(len(r["classes"]) for r in G.races.values() if r["faction"] == fac), 28)

    def test_every_class_playable_both_factions(self):
        for fac in ("Alliance", "Horde"):
            cls = {c for r in G.races.values() if r["faction"] == fac for c in r["classes"]}
            self.assertEqual(cls, set(G.classes))

    def test_legacy_totals(self):
        ch = G.legacy["challenges"]
        self.assertEqual(ch["class"]["total"], 27)
        self.assertEqual(ch["craft"]["total"], 18)
        self.assertEqual(sum(v["total"] for v in ch.values()), 65)

    def test_wowhead_ids_shape(self):
        for n, e in G.ids.items():
            self.assertIn(e["type"], {"quest", "npc", "item", "spell", "zone", "class", "race", "skill", "faction"}, n)
            self.assertIsInstance(e["id"], int)


if __name__ == "__main__":
    unittest.main()
