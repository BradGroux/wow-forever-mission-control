"""Unit tests for the mc CLI. Run: python3 -m unittest discover -s tests -v"""
import copy, json, os, subprocess, sys, tempfile, unittest

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

    def test_four_characters(self):
        c = copy.deepcopy(EX)
        c["characters"] = c["characters"][:3]
        e, _, _ = mc.validate(c, G)
        self.assertTrue(any("exactly four" in x for x in e))

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
