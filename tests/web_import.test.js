// node tests/web_import.test.js — checks the page's progress merge and LegacyTracker.lua import.
const fs = require("fs"), path = require("path"), assert = require("assert");
const root = path.join(__dirname, "..");
const src = fs.readFileSync(path.join(root, "web", "app.js"), "utf8");
const cut = (a, b) => src.slice(src.indexOf(a), src.indexOf(b));
const body = cut("  function blank()", "  var S = load();") + cut("  function parseLua", "  function importJSON");
const CHARS = [{ id: "aldric", name: "Aldric" }, { id: "elowen", name: "Elowen" }, { id: "brannoc", name: "Brannoc" }];
let P = { roster: { key: "k" }, progress: { map: { Brannocalt: "brannoc" } } }, S = {};
function today() { return "2026-11-04"; }
const KEY = "mc:k:v1", store = {};
global.localStorage = { getItem: (k) => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); } };
console.warn = () => {};
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

// realm-qualified mapping beats bare name; same name on two realms is ambiguous (#51)
const two = 'LegacyTrackerDB = { chars = { ["OtherRealm-Aldric"] = {name="Aldric", level=50, lastSeen=1800000000} } }';
S = { map: { "OtherRealm-Aldric": "brannoc" }, levels: {} };
r = fromAddon(two);
assert.strictEqual(r.extra.levels.brannoc.level, 50); assert.ok(!r.extra.levels.aldric);
S = { levels: {} };
r = fromAddon('LegacyTrackerDB = { chars = { ["A-Aldric"] = {name="Aldric", level=50, lastSeen=2}, ["B-Aldric"] = {name="Aldric", level=20, lastSeen=1} } }');
assert.strictEqual(r.ambiguous.length, 1); assert.ok(!r.extra.levels.aldric);
S = {};

// map survives and is exported (#19)
const m = merge(merge(blank(), { map: { Aldricthebold: "aldric" } }), { map: { SomeAlt: "elowen" } });
assert.deepStrictEqual(m.map, { Aldricthebold: "aldric", SomeAlt: "elowen" });
assert.ok("map" in JSON.parse(JSON.stringify(m)));

// CLI edit stamps (#50): a later ./mc check --off (newer baked stamp) beats an older local stamped tick
{
  const t1 = Date.parse("2026-11-06T10:00:00Z");
  const loc = { updated: "2026-11-06", checks: { a: true }, levels: {}, skills: {}, map: {}, stamp: { "c:a": t1 } };
  const bk = JSON.parse(JSON.stringify(loc)); delete bk.checks.a; bk.stamp["c:a"] = t1 + 60000;
  assert.ok(!merge(bk, loc).checks.a, "CLI untick lost to an older browser stamp");
  loc.stamp["c:a"] = t1 + 120000;
  assert.ok(merge(bk, loc).checks.a, "a later browser edit must still win");
  // manual level over a record with addon metadata
  const lb = { levels: { aldric: { level: 28, lastSeenEpoch: 1700000000, updated: "2026-11-06", source: "manual" } }, stamp: { "l:aldric": t1 } };
  const ll = { levels: { aldric: { level: 30, lastSeenEpoch: 1700000500, updated: "2023-11-14" } } };
  assert.strictEqual(merge(merge(blank(), lb), ll).levels.aldric.level, 28);
}

// canvas Copy progress tombstones (#56): a stamped false unticks a baked tick
{
  const t2 = Date.parse("2026-11-06T12:00:00Z");
  const bakedU = merge(blank(), { updated: "2026-11-05", checks: { a: true, b: true } });  // unstamped (e.g. ./mc check)
  const canvas = { updated: "2026-11-06", checks: { a: true, b: false }, stamp: { "c:b": t2 } };
  let pg = merge(bakedU, canvas);
  assert.ok(!pg.checks.b && pg.checks.a, "canvas untick lost on page import");
  assert.ok(!merge(merge(blank(), { updated: "2026-11-05", checks: { a: true, b: true } }), pg).checks.b, "untick lost after reload");
  const bakedS = merge(blank(), { updated: "2026-11-05", checks: { b: true }, stamp: { "c:b": t2 - 1000 } });
  assert.ok(!merge(bakedS, canvas).checks.b, "untick lost against an older stamped tick");
  const newer = merge(blank(), { updated: "2026-11-06", checks: { b: true }, stamp: { "c:b": t2 + 1000 } });
  assert.ok(merge(newer, canvas).checks.b, "a newer destination edit must win");
  assert.ok(merge(blank(), { checks: { c: true } }).checks.c && merge(merge(blank(), { checks: { c: true } }), canvas).checks.c, "ids the file doesn't address are kept");
}

// progress validation (#54)
assert.deepStrictEqual(checkProgress({ levels: { aldric: { level: 12, rested: "Partial" } }, skills: { aldric: { Mining: 45 } } }), []);
[[{ levels: { aldric: { level: 1, updated: "2026-11-06", rested: {} } } }, "rested"], [{ levels: [] }, "levels: must be an object"],
 [{ levels: { aldric: { level: 0 } } }, "1-60"], [{ skills: { aldric: { Mining: "x" } } }, "0-300"], [{ checks: { a: 1 } }, "checks.a"],
 [{ version: 9 }, "version"], [[1], "JSON object"], [null, "JSON object"]].forEach(([o, frag]) => {
  assert.ok(checkProgress(o).some((e) => e.indexOf(frag) >= 0), JSON.stringify(o));
});
// a malformed saved record loads what is valid and keeps the original
{
  const badRaw = JSON.stringify({ checks: { a: true }, levels: { aldric: { level: 14, rested: {}, updated: "2026-11-06" } } });
  store[KEY] = badRaw;
  const L = load();
  assert.ok(L.checks.a); assert.strictEqual(L.levels.aldric.level, 14); assert.strictEqual(typeof (L.levels.aldric.rested || ""), "string");
  assert.strictEqual(store[KEY + ":invalid"], badRaw);
  assert.strictEqual(store[KEY], badRaw, "load must not overwrite the saved copy");
  store[KEY] = "{not json"; delete store[KEY + ":invalid"];
  assert.ok(load()); assert.strictEqual(store[KEY + ":invalid"], "{not json");
}

// addon ranges (#61): out-of-range records are skipped and reported, valid ones import
{
  const lua = (lv, rk) => 'LegacyTrackerDB = { chars = { ["R-Aldric"] = {name="Aldric", level=' + lv + ', lastSeen=1800000000, professions={Mining={rank=' + rk + '}}} } }';
  S = { levels: {} };
  [[0, 10], [61, 10], [999, 10], [20, 301], [20, 999], [20, -5]].forEach(([lv, rk]) => {
    const x = fromAddon(lua(lv, rk));
    assert.strictEqual(x.invalid.length, 1, lv + "/" + rk); assert.strictEqual(x.matched, 0); assert.ok(!x.extra.levels.aldric);
  });
  const ok = fromAddon(lua(20, 75));
  assert.strictEqual(ok.extra.levels.aldric.level, 20); assert.strictEqual(ok.extra.skills.aldric.Mining, 75);
  S = {};
}

// addon skill ordering (#62): a newer snapshot advances a manually edited skill, an older one doesn't
{
  const t = Date.parse("2026-11-06T10:00:00Z");
  const edited = merge(blank(), { skills: { aldric: { Blacksmithing: 10 } }, stamp: { "s:aldric:Blacksmithing": t } });
  const snap = (sec) => ({ levels: { aldric: { level: 20, lastSeenEpoch: sec } }, skills: { aldric: { Blacksmithing: 100 } } });
  assert.strictEqual(merge(edited, snap(Date.parse("2026-11-07T11:00:00Z") / 1000)).skills.aldric.Blacksmithing, 100);
  assert.strictEqual(merge(edited, snap(Date.parse("2026-11-05T11:00:00Z") / 1000)).skills.aldric.Blacksmithing, 10);
  assert.strictEqual(merge(merge(blank(), { skills: { aldric: { Mining: 120 } } }), { skills: { aldric: { Mining: 100 } } }).skills.aldric.Mining, 120);
  // through fromAddon too
  S = edited;
  const r2 = fromAddon('LegacyTrackerDB = { chars = { ["R-Aldric"] = {name="Aldric", level=20, lastSeen=' + Date.parse("2026-11-07T11:00:00Z") / 1000 + ', professions={Blacksmithing={rank=100}}} } }');
  assert.strictEqual(merge(S, r2.extra).skills.aldric.Blacksmithing, 100);
  S = {};
}

// non-finite numbers are rejected (#65 parity)
assert.ok(checkProgress({ stamp: { "c:a": Infinity } }).length && checkProgress({ levels: { aldric: { level: NaN } } }).length);

assert.deepStrictEqual(parseLua('X = { "a", ["k"] = "q\\"x", n = -1.5e2, t = true, -- c\n }').X, { 1: "a", k: 'q"x', n: -150, t: true });
console.log("web import: ok");
