// node tests/canvas_export.test.js [canvas.tsx] — the canvas Copy progress export carries untick tombstones (#56)
// that the page's Import progress honors. Needs npx (esbuild) like the canvas syntax check.
const fs = require("fs"), path = require("path"), os = require("os"), assert = require("assert"), cp = require("child_process");
const root = path.join(__dirname, "..");
const file = process.argv[2] || path.join(root, "build", "mission-control.canvas.tsx");
const s = fs.readFileSync(file, "utf8");
const saved = s.slice(s.indexOf("// SAVED-START"), s.indexOf("// SAVED-END"));
const prog = s.slice(s.indexOf("// ---------- progress"), s.indexOf("function CopyProgress"));
assert.ok(saved && prog, "SAVED block or progress section not found in " + file);
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "mc-canvas-"));
fs.writeFileSync(path.join(tmp, "cv.ts"), saved + "\nconst PLAN: any = { roster: { key: \"k\" } };\n" + prog + "\nexport { setCheck, exportProgress, SAVED };\n");
cp.execSync(`npx --yes esbuild@0.24.0 cv.ts --loader:.ts=ts --format=cjs --log-level=warning --outfile=cv.js`, { cwd: tmp, stdio: "inherit" });
global.useState = () => [0, () => {}]; global.useEffect = () => {};
const cv = require(path.join(tmp, "cv.js"));

// page merge from web/app.js
const src = fs.readFileSync(path.join(root, "web", "app.js"), "utf8");
const cut = (a, b) => src.slice(src.indexOf(a), src.indexOf(b));
const CHARS = [{ id: "aldric", name: "Aldric" }];
const P = { roster: { key: "k" }, progress: {} };
function today() { return "2026-11-04"; }
eval(cut("  function blank()", "  function touch("));

const baked = merge(blank(), { updated: "2026-01-05", checks: { "t-a": true, "t-b": true, "t-keep": true } });  // unstamped ticks
cv.setCheck("t-a", false); cv.setCheck("t-new", true);
const out = JSON.parse(cv.exportProgress());
assert.strictEqual(out.checks["t-a"], false, "untick must be exported");
assert.ok(out.stamp["c:t-a"] > 0 && out.stamp["c:t-new"] > 0, "edits must be stamped");
const pg = merge(baked, out);
assert.ok(!pg.checks["t-a"], "canvas untick lost on page import");
assert.ok(pg.checks["t-new"], "canvas tick lost on page import");
assert.ok(pg.checks["t-keep"] && pg.checks["t-b"], "ids the canvas did not touch are kept");
const later = merge(blank(), { updated: "2026-01-05", checks: { "t-a": true }, stamp: { "c:t-a": out.stamp["c:t-a"] + 1000 } });
assert.ok(merge(later, out).checks["t-a"], "a newer destination edit must win");
fs.rmSync(tmp, { recursive: true, force: true });
console.log("canvas export: ok " + path.relative(root, file));
