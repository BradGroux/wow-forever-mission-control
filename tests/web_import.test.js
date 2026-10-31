// node tests/web_import.test.js — checks the page's progress merge and LegacyTracker.lua import.
const fs = require("fs"), path = require("path"), assert = require("assert");
const root = path.join(__dirname, "..");
const src = fs.readFileSync(path.join(root, "web", "app.js"), "utf8");
const cut = (a, b) => src.slice(src.indexOf(a), src.indexOf(b));
const body = cut("  function blank()", "  function load()") + cut("  function parseLua", "  function importJSON");
const CHARS = [{ id: "aldric", name: "Aldric" }, { id: "elowen", name: "Elowen" }, { id: "brannoc", name: "Brannoc" }];
let P = { roster: { key: "k" }, progress: { map: { Brannocalt: "brannoc" } } }, S = {};
function today() { return "2026-11-04"; }
eval(body);
const sv = fs.readFileSync(path.join(root, "addon", "test", "SavedVariables.sample.lua"), "utf8");

// addon import
let r = fromAddon(sv);
assert.strictEqual(r.matched, 2);
assert.strictEqual(r.db, "LegacyTrackerDB");
assert.strictEqual(r.extra.levels.aldric.level, 12);
assert.strictEqual(r.extra.levels.elowen.level, 10);
assert.strictEqual(r.extra.skills.aldric.Mining, 45);
assert.ok(r.extra.levels.aldric.lastSeenEpoch > 0);
assert.ok(!("checks" in r.extra), "addon import must not touch checks");
const mapped = fromAddon(sv.split("Elowen").join("Brannocalt"));
assert.strictEqual(mapped.extra.levels.brannoc.level, 10);
// renamed addon table (#17)
const ren = fromAddon(sv.replace("LegacyTrackerDB", "MyTrackerDB"));
assert.strictEqual(ren.db, "MyTrackerDB"); assert.strictEqual(ren.matched, 2);
// stale guard (#17): same file again is not newer
S = merge(blank(), r.extra);
r = fromAddon(sv);
assert.strictEqual(r.stale.length, 2);
assert.deepStrictEqual(Object.keys(r.extra.levels), []);
S = {};

// merge: page edits stick over baked progress (#16)
const baked = Object.assign(blank(), { updated: "2026-11-05", checks: { a: true, b: true }, skills: { aldric: { Mining: 120 } }, notes: "baked" });
baked.levels.aldric = { level: 20, updated: "2026-11-05" };
const base = merge(blank(), baked);
const t = Date.parse("2026-11-06");
const local = merge(base, {});
delete local.checks.a; local.levels.aldric = { level: 12, updated: "2026-11-06" }; local.skills.aldric.Mining = 80; local.notes = "";
local.stamp = { "c:a": t, "l:aldric": t, "s:aldric:Mining": t, n: t };
const reloaded = merge(base, JSON.parse(JSON.stringify(local)));
assert.ok(!reloaded.checks.a, "unticked baked check came back");
assert.ok(reloaded.checks.b);
assert.strictEqual(reloaded.levels.aldric.level, 12, "lowered level reverted");
assert.strictEqual(reloaded.skills.aldric.Mining, 80);
assert.strictEqual(reloaded.notes, "");
// a newer bake beats an older page edit
const newer = Object.assign({}, baked, { updated: "2026-11-08" }); newer.levels = Object.assign({}, baked.levels, { aldric: { level: 25, updated: "2026-11-08" } });
assert.strictEqual(merge(merge(blank(), newer), local).levels.aldric.level, 25);
// unstamped data keeps the old rules
assert.strictEqual(merge(base, { levels: { aldric: { level: 9 } } }).levels.aldric.level, 20);

// a stored page edit survives a stale, unstamped export (#41)
const stale = Object.assign(blank(), { updated: "2026-11-05", checks: { a: true, b: true }, skills: { aldric: { Mining: 120 } }, notes: "baked" });
stale.levels.aldric = { level: 20, updated: "2026-11-05" };
const kept = merge(reloaded, stale);
assert.ok(!kept.checks.a, "stale export re-ticked a stamped untick");
assert.strictEqual(kept.levels.aldric.level, 12, "stale export raised a stamped level");
assert.strictEqual(kept.skills.aldric.Mining, 80);
assert.strictEqual(kept.notes, "");
// newer unstamped data still applies
const fresh = merge(reloaded, { updated: "2026-11-09", levels: { aldric: { level: 30, updated: "2026-11-09" } } });
assert.strictEqual(fresh.levels.aldric.level, 30);

// map survives and is exported (#19)
const m = merge(merge(blank(), { map: { Aldricthebold: "aldric" } }), { map: { SomeAlt: "elowen" } });
assert.deepStrictEqual(m.map, { Aldricthebold: "aldric", SomeAlt: "elowen" });
assert.ok("map" in JSON.parse(JSON.stringify(m)));

assert.deepStrictEqual(parseLua('X = { "a", ["k"] = "q\\"x", n = -1.5e2, t = true, -- c\n }').X, { 1: "a", k: 'q"x', n: -150, t: true });
console.log("web import: ok");
