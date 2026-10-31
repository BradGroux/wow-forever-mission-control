// node tests/web_import.test.js — checks the page's LegacyTracker.lua import.
const fs = require("fs"), path = require("path"), assert = require("assert");
const root = path.join(__dirname, "..");
const src = fs.readFileSync(path.join(root, "web", "app.js"), "utf8");
const body = src.slice(src.indexOf("  function parseLua"), src.indexOf("  function importJSON"));
const CHARS = [{ id: "aldric", name: "Aldric" }, { id: "elowen", name: "Elowen" }, { id: "brannoc", name: "Brannoc" }];
const P = { progress: { map: { Brannocalt: "brannoc" } } }, S = {};
function today() { return "2026-11-04"; }
eval(body);
const sv = fs.readFileSync(path.join(root, "addon", "test", "SavedVariables.sample.lua"), "utf8");
const r = fromAddon(sv);
assert.strictEqual(r.matched, 2);
assert.strictEqual(r.extra.levels.aldric.level, 12);
assert.strictEqual(r.extra.levels.elowen.level, 10);
assert.strictEqual(r.extra.skills.aldric.Mining, 45);
const mapped = fromAddon(sv.split("Elowen").join("Brannocalt"));
assert.strictEqual(mapped.extra.levels.brannoc.level, 10);
assert.deepStrictEqual(parseLua('X = { "a", ["k"] = "q\\"x", n = -1.5e2, t = true, -- c\n }').X, { 1: "a", k: 'q"x', n: -150, t: true });
console.log("web import: ok");
