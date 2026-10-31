/* WoW Forever Legacy Mission Control: static page, no build step, no backend.
   Reads window.MC_PLAN (web/data/plan.js or plan.example.js, written by ./mc generate).
   Progress lives in localStorage; Export/Import move it as JSON. */
(function () {
  "use strict";
  var P = window.MC_PLAN;
  if (!P) { document.getElementById("view").textContent = "No plan data. Run ./mc generate."; return; }

  // ---------- fixed colors (also used inside SVG, where CSS variables are avoided)
  var C = { t1: "#ECECEC", t2: "#BEBEBE", t3: "#9C9C9C", f2: "#2B2B2B", b1: "#4A4A4A", b0: "#353535", bg: "#141414", gold: "#C9A227" };
  var CHARS = P.characters;
  var byId = {}; CHARS.forEach(function (c) { byId[c.id] = c; });

  // ---------- DOM helper
  function h(tag, attrs) {
    var el = tag === "svg" || attrs && attrs.svg ? document.createElementNS("http://www.w3.org/2000/svg", tag) : document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) {
      var v = attrs[k];
      if (k === "svg" || v === undefined || v === null || v === false) return;
      if (k.slice(0, 2) === "on") el.addEventListener(k.slice(2), v);
      else if (k === "style" && typeof v === "object") Object.keys(v).forEach(function (s) { el.style.setProperty(s, v[s]); });
      else if (k === "text") el.textContent = v;
      else el.setAttribute(k, v === true ? "" : v);
    });
    for (var i = 2; i < arguments.length; i++) add(el, arguments[i]);
    return el;
  }
  function add(el, c) {
    if (c === null || c === undefined || c === false) return;
    if (Array.isArray(c)) { c.forEach(function (x) { add(el, x); }); return; }
    el.appendChild(typeof c === "string" || typeof c === "number" ? document.createTextNode(String(c)) : c);
  }
  function s(tag, attrs) { attrs = attrs || {}; attrs.svg = true; var a = [tag, attrs].concat([].slice.call(arguments, 2)); return h.apply(null, a); }

  // ---------- links: every known game name becomes a Wowhead link
  var LINKS = P.links || {};
  var KEYS = Object.keys(LINKS).sort(function (a, b) { return b.length - a.length; });
  var RE = KEYS.length ? new RegExp("(" + KEYS.map(function (k) { return k.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); }).join("|") + ")", "g") : null;
  function wl(name, label) {
    var e = LINKS[name];
    if (!e) return document.createTextNode(label || name);
    return h("a", { href: e.url, target: "_blank", rel: "noopener noreferrer", class: e.direct ? null : "search", title: e.direct ? "Wowhead" : "Wowhead search" }, label || name);
  }
  function L(text) {
    var frag = document.createDocumentFragment();
    if (!RE || !text) { frag.appendChild(document.createTextNode(text || "")); return frag; }
    var last = 0, m; RE.lastIndex = 0;
    while ((m = RE.exec(text))) {
      var a = m.index, b = a + m[0].length;
      if (/[A-Za-z0-9]/.test(text.charAt(a - 1) || " ") || /[A-Za-z0-9]/.test(text.charAt(b) || " ")) { RE.lastIndex = a + 1; continue; }
      if (a > last) frag.appendChild(document.createTextNode(text.slice(last, a)));
      frag.appendChild(wl(m[0]));
      last = b;
    }
    if (last < text.length) frag.appendChild(document.createTextNode(text.slice(last)));
    return frag;
  }

  // ---------- progress store
  var KEY = "mc:" + P.roster.key + ":v1";
  function today() { var d = new Date(); return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0"); }
  function blank() {
    var lv = {}; CHARS.forEach(function (c) { lv[c.id] = { level: 1, rested: "Empty", updated: "" }; });
    return { version: 1, roster: P.roster.key, updated: "", checks: {}, levels: lv, skills: {}, notes: "" };
  }
  function merge(base, extra) {
    var out = JSON.parse(JSON.stringify(base));
    if (!extra) return out;
    Object.keys(extra.checks || {}).forEach(function (k) { if (extra.checks[k]) out.checks[k] = true; else delete out.checks[k]; });
    Object.keys(extra.levels || {}).forEach(function (id) {
      var o = out.levels[id] || {}, n = extra.levels[id] || {};
      out.levels[id] = (n.level || 0) >= (o.level || 0) ? Object.assign({}, o, n) : o;
    });
    Object.keys(extra.skills || {}).forEach(function (id) {
      out.skills[id] = out.skills[id] || {};
      Object.keys(extra.skills[id]).forEach(function (p) { out.skills[id][p] = Math.max(+extra.skills[id][p] || 0, +out.skills[id][p] || 0); });
    });
    if (extra.notes) out.notes = extra.notes;
    out.updated = extra.updated || out.updated;
    return out;
  }
  function load() {
    var base = merge(blank(), P.progress);
    try { var raw = localStorage.getItem(KEY); if (raw) return merge(base, JSON.parse(raw)); } catch (e) { /* storage blocked */ }
    return base;
  }
  var S = load();
  function save() { S.updated = today(); try { localStorage.setItem(KEY, JSON.stringify(S)); } catch (e) { /* session only */ } render(); }
  function lv(id) { return (S.levels[id] && S.levels[id].level) || 1; }
  function skill(id, prof) { return (S.skills[id] && +S.skills[id][prof]) || 0; }

  // ---------- derived
  function bracketOf(level) {
    for (var i = 0; i < P.brackets.length; i++) { var b = P.brackets[i]; if (level >= b.from && level < b.to) return b; }
    return P.brackets[P.brackets.length - 1];
  }
  function nextUp() { return CHARS.slice().sort(function (a, b) { return lv(a.id) - lv(b.id); })[0]; }
  function earned() {
    var cls = {}, pts = 0;
    CHARS.forEach(function (c) { [25, 45, 60].forEach(function (t) { if (lv(c.id) >= t) cls[c["class"] + t] = 1; }); });
    pts += Object.keys(cls).length;
    var crafts = {};
    CHARS.forEach(function (c) { c.professions.forEach(function (p) { [150, 225, 300].forEach(function (t) { if (skill(c.id, p.name) >= t && P.professions.crafting[p.name]) crafts[p.name + t] = 1; }); }); });
    pts += Object.keys(crafts).length;
    P.account.forEach(function (a) { if (S.checks[a.id]) pts += 1; });
    return pts;
  }
  function statusTag(st) {
    if (st === "classic") return h("span", { class: "tag warn", title: "Classic data, unconfirmed for Forever" }, "Classic data");
    if (st === "unverified") return h("span", { class: "tag warn" }, "Unverified");
    return null;
  }
  function icon(c, size) {
    var img = h("img", { class: "icon", src: c.icon, alt: c["class"], width: size || 26, height: size || 26, style: { "--cc": c.color } });
    img.addEventListener("error", function () { img.replaceWith(h("span", { class: "icon", style: { "--cc": c.color, display: "inline-grid", "place-items": "center", color: c.color, "font-weight": "700" } }, c["class"].charAt(0))); });
    return img;
  }
  function bar(value, max, color) { return h("div", { class: "bar", style: { "--cc": color } }, h("i", { style: { width: Math.max(0, Math.min(100, value / max * 100)) + "%" } })); }

  // ---------- components
  function checklist(items, color) {
    var done = items.filter(function (i) { return S.checks[i.id]; }).length;
    return h("div", null,
      h("div", { style: { display: "flex", gap: "10px", "align-items": "center", "margin-bottom": "6px" } },
        h("div", { style: { flex: "1" } }, bar(done, Math.max(1, items.length), color || C.gold)),
        h("span", { class: "dim" }, done + " / " + items.length)),
      h("div", { class: "checklist", role: "list" }, items.map(function (it) {
        var on = !!S.checks[it.id];
        function toggle() { if (on) delete S.checks[it.id]; else S.checks[it.id] = true; save(); }
        return h("div", { class: "check", role: "checkbox", tabindex: "0", "aria-checked": on ? "true" : "false", style: { "--cc": color || C.gold },
          onclick: toggle, onkeydown: function (e) { if (e.key === " " || e.key === "Enter") { e.preventDefault(); toggle(); } } },
          h("span", { class: "box", "aria-hidden": "true" }, on ? "✓" : ""),
          h("span", { class: "txt" }, L(it.text), it.detail ? h("div", { class: "dim" }, L(it.detail)) : null),
          it.tag ? h("span", { class: "tag" }, it.tag) : null);
      })));
  }
  function charHead(c, title, right) {
    return h("div", { class: "head", style: { "--cc": c.color } }, icon(c, 28), h("span", { class: "name" }, c.display), h("span", { class: "title" }, title), right ? h("span", { class: "count" }, right) : null);
  }
  function seg(options, value, onpick) {
    return h("div", { class: "seg", role: "group" }, options.map(function (o) {
      return h("button", { type: "button", "aria-pressed": o.value === value ? "true" : "false", onclick: function () { onpick(o.value); } }, o.label);
    }));
  }
  function table(cols, rows) {
    return h("table", null, h("thead", null, h("tr", null, cols.map(function (c) { return h("th", null, c); }))),
      h("tbody", null, rows.map(function (r) { return h("tr", null, r.map(function (c) { return h("td", null, typeof c === "string" ? L(c) : c); })); })));
  }

  function cards() {
    var nu = nextUp();
    return h("div", { class: "cards" }, CHARS.map(function (c) {
      var l = lv(c.id), b = bracketOf(l), rest = (S.levels[c.id] || {}).rested || "Empty";
      return h("div", { class: "card", role: "button", tabindex: "0", "aria-pressed": UI.char === c.id ? "true" : "false", style: { "--cc": c.color },
        onclick: function () { UI.char = c.id; render(); } },
        h("div", { class: "row" }, icon(c), h("span", { class: "name" }, c.display), h("span", { class: "sub" }, L(c.race + " " + c["class"])),
          c.id === nu.id ? h("span", { class: "tag next", style: { "margin-left": "auto" } }, "Up next") : null),
        h("div", { class: "row sub" }, "Level ",
          h("input", { type: "number", min: "1", max: "60", value: String(l), "aria-label": c.display + " level", onclick: function (e) { e.stopPropagation(); },
            onchange: function (e) { var v = Math.max(1, Math.min(60, parseInt(e.target.value, 10) || 1)); S.levels[c.id] = Object.assign({}, S.levels[c.id], { level: v, updated: today() }); save(); } }),
          h("select", { "aria-label": c.display + " rested", onclick: function (e) { e.stopPropagation(); },
            onchange: function (e) { S.levels[c.id] = Object.assign({}, S.levels[c.id], { rested: e.target.value, updated: today() }); save(); } },
            ["Empty", "Partial", "Full"].map(function (r) { return h("option", { value: r, selected: r === rest }, "Rested " + r.toLowerCase()); })),
          h("span", { class: "dim", style: { "margin-left": "auto" } }, b.from + "–" + b.to)),
        bar(l, 60, c.color),
        h("div", { class: "row dim" }, c.leveling_spec + " → " + c.endgame_spec, h("span", { style: { "margin-left": "auto" } }, c.professions.map(function (p) { return p.name; }).join(" · "))));
    }));
  }

  // ---------- Road to 60 timeline (SVG, fixed colors)
  function timeline() {
    var W = 1120, left = 140, right = 30, top = 8, bandH = 32, rowH = 52;
    var x = function (l) { return left + (l - 1) / 59 * (W - left - right); };
    var rows = CHARS.map(function (c) { return { label: c.display, color: c.color, id: c.id, marks: c.milestones.map(function (m) { return { lv: m.level, name: m.name }; }) }; });
    rows.push({ label: "Dungeons", color: C.t2, marks: P.dungeons.map(function (d) { return { lv: Math.round((d.min + d.max) / 2), name: d.name }; }) });
    rows.push({ label: "Legacy", color: C.gold, marks: [{ lv: 25, name: "Novice class points" }, { lv: 45, name: "Experienced class points" }, { lv: 60, name: "Master class points" }] });
    var H = top + bandH + 16 + rows.length * rowH;
    var svg = s("svg", { viewBox: "0 0 " + W + " " + H, width: "100%", role: "img", "aria-label": "Levels 1 to 60" });
    P.brackets.forEach(function (b) {
      var on = UI.bracket === b.id, bw = x(b.to) - x(b.from) - 3;
      var g = s("g", { style: { cursor: "pointer" }, onclick: function () { UI.bracket = b.id; UI.tab = "levels"; render(); } },
        s("rect", { x: x(b.from) + 1.5, y: top, width: bw, height: bandH, rx: 6, fill: on ? C.gold : C.f2, stroke: on ? C.gold : C.b1 }),
        s("text", { x: (x(b.from) + x(b.to)) / 2, y: top + bandH / 2 + 5, "text-anchor": "middle", "font-size": bw < 70 ? 13 : 15, "font-weight": 600, fill: on ? "#1A1405" : C.t1 }, b.from + "–" + b.to));
      svg.appendChild(g);
    });
    rows.forEach(function (r, i) {
      var y = top + bandH + 16 + i * rowH + rowH / 2 + 6;
      if (i > 0) svg.appendChild(s("line", { x1: 8, x2: W - 8, y1: y - rowH / 2 - 2, y2: y - rowH / 2 - 2, stroke: C.b0, "stroke-dasharray": "2 4" }));
      svg.appendChild(s("text", { x: 8, y: y + 5, "font-size": 14, fill: r.id ? r.color : C.t3, "font-weight": r.id ? 700 : 400 }, r.label));
      svg.appendChild(s("line", { x1: left, x2: W - right, y1: y, y2: y, stroke: C.b1 }));
      if (r.id) {
        var l = lv(r.id);
        svg.appendChild(s("rect", { x: left, y: y - 2, width: Math.max(0, x(l) - left), height: 4, rx: 2, fill: r.color }));
      }
      var labelEnd = -1e9;
      r.marks.slice().sort(function (a, b) { return a.lv - b.lv; }).forEach(function (m) {
        var cx = x(m.lv), done = r.id && lv(r.id) >= m.lv;
        var g = s("g", null, s("title", null, m.name + " · " + m.lv),
          s("circle", { cx: cx, cy: y, r: 6, fill: done ? r.color : C.bg, stroke: r.color, "stroke-width": 2 }));
        var w = m.name.length * 6.2;
        if (cx - w / 2 > labelEnd + 8 && cx + w / 2 < W) {
          g.appendChild(s("text", { x: cx, y: y - 12, "text-anchor": "middle", "font-size": 11, fill: C.t2 }, m.name));
          labelEnd = cx + w / 2;
        }
        svg.appendChild(g);
      });
    });
    [1, 10, 20, 30, 40, 50, 60].forEach(function (n) { svg.appendChild(s("text", { x: x(n), y: H - 2, "text-anchor": "middle", "font-size": 11, fill: C.t3 }, String(n))); });
    return svg;
  }

  function rewardTrack(points) {
    var W = 1120, L0 = 24, R0 = 24, y = 50, max = 65;
    var x = function (p) { return L0 + p / max * (W - L0 - R0); };
    var svg = s("svg", { viewBox: "0 0 " + W + " 110", width: "100%", role: "img", "aria-label": "Legacy reward track" },
      s("rect", { x: L0, y: y - 6, width: W - L0 - R0, height: 12, rx: 6, fill: C.f2 }),
      s("rect", { x: L0, y: y - 6, width: Math.max(0, x(points) - L0), height: 12, rx: 6, fill: C.gold }),
      s("rect", { x: x(P.legacy.spend_cap) - 1, y: y - 14, width: 2, height: 28, fill: C.t1 }),
      s("text", { x: x(P.legacy.spend_cap), y: y - 20, "text-anchor": "middle", "font-size": 12, "font-weight": 600, fill: C.t1 }, P.legacy.spend_cap + " spend cap"),
      s("rect", { x: x(P.coverage.legacy_from_plan) - 1, y: y - 14, width: 2, height: 28, fill: C.t3 }),
      s("text", { x: x(P.coverage.legacy_from_plan), y: y - 20, "text-anchor": "middle", "font-size": 12, fill: C.t2 }, P.coverage.legacy_from_plan + " from leveling and crafts"));
    P.legacy.rewards.forEach(function (r) {
      svg.appendChild(s("circle", { cx: x(r.points), cy: y, r: 9, fill: C.bg, stroke: C.gold, "stroke-width": 3 }));
      svg.appendChild(s("text", { x: x(r.points), y: y + 30, "text-anchor": "middle", "font-size": 12, "font-weight": 600, fill: C.t1 }, String(r.points)));
      var a = s("a", { href: (LINKS[r.name] || {}).url || "#", target: "_blank" }, s("text", { x: x(r.points), y: y + 46, "text-anchor": "middle", "font-size": 11, fill: C.t1, "text-decoration": "underline" }, r.name));
      svg.appendChild(a);
    });
    return svg;
  }

  // ---------- views
  var UI = { tab: (location.hash || "#today").slice(1), char: CHARS[0].id, bracket: bracketOf(lv(nextUp().id)).id };
  var TABS = [["today", "Today"], ["road", "Road to 60"], ["levels", "Levels"], ["profs", "Professions"], ["legacy", "Legacy"], ["dungeons", "Dungeons"], ["world", "World"], ["reference", "Reference"]];

  function vToday() {
    var c = byId[UI.char], b = bracketOf(lv(c.id)), nu = nextUp();
    var mine = b.tasks[c.id] || [];
    return [
      h("section", null, h("h2", null, "Roster"), cards()),
      h("section", null, h("div", { class: "metrics" },
        h("div", { class: "metric" }, h("b", { style: { color: nu.color } }, nu.display), h("span", null, "Up next · level " + lv(nu.id))),
        h("div", { class: "metric" }, h("b", null, bracketOf(lv(nu.id)).from + "–" + bracketOf(lv(nu.id)).to), h("span", null, "Current range")),
        h("div", { class: "metric" }, h("b", null, earned() + " / " + P.coverage.legacy_from_plan), h("span", null, "Legacy points")),
        h("div", { class: "metric" }, h("b", null, P.roster.launch), h("span", null, "Launch")))),
      h("div", { class: "grid" },
        h("section", null, charHead(c, "Levels " + b.from + "–" + b.to), checklist(mine, c.color)),
        h("section", null, charHead(c, "Next milestones"), h("ul", { class: "plain" },
          c.milestones.filter(function (m) { return m.level >= lv(c.id); }).slice(0, 6).map(function (m) {
            return h("li", null, L(m.name), " · " + m.level + " ", statusTag(m.status));
          })))),
      h("section", null, h("h2", null, "Road to 60"), timeline())
    ];
  }
  function vRoad() {
    return [h("section", null, h("h2", null, "Road to 60"), timeline()),
      h("section", null, h("h2", null, "Milestones"), table(["Level", "Character", "Milestone", "Type", ""],
        CHARS.reduce(function (acc, c) { return acc.concat(c.milestones.map(function (m) { return [m.level, c, m]; })); }, []).sort(function (a, b) { return a[0] - b[0]; })
          .map(function (r) { return [String(r[0]), h("span", { class: "name", style: { "--cc": r[1].color } }, r[1].display), r[2].name, r[2].kind, statusTag(r[2].status) || ""]; })))];
  }
  function vLevels() {
    var b = P.brackets.filter(function (x) { return x.id === UI.bracket; })[0] || P.brackets[0];
    return [
      seg(P.brackets.map(function (x) { return { value: x.id, label: x.from + "–" + x.to }; }), b.id, function (v) { UI.bracket = v; render(); }),
      h("div", { class: "grid" },
        h("section", null, h("h2", null, "Levels " + b.from + "–" + b.to), b.why.length ? h("ul", { class: "plain" }, b.why.map(function (w) { return h("li", null, L(w)); })) : null,
          h("p", null, h("span", { class: "dim" }, "Zones "), b.zones.map(function (z, i) { return [i ? ", " : "", wl(z)]; }))),
        h("section", null, h("h2", null, "Rotation"), table(["Character", "Target", "Zones", "Log out"], b.rotation.map(function (r) {
          var c = byId[r["char"]];
          return [h("span", { class: "name", style: { "--cc": c.color } }, c.display), String(r.target), r.zones.join(", "), r.logout];
        })))),
      h("div", { class: "grid" }, CHARS.map(function (c) {
        return h("section", null, charHead(c, c.race + " " + c["class"]), checklist(b.tasks[c.id] || [], c.color));
      }))
    ];
  }
  function vProfs() {
    var crafts = Object.keys(P.coverage.crafts);
    return [
      h("section", null, h("h2", null, "Craft coverage"), table(["Craft"].concat(CHARS.map(function (c) { return c.display; })),
        crafts.map(function (cr) {
          return [cr].concat(CHARS.map(function (c) {
            var on = P.coverage.crafts[cr].indexOf(c.id) >= 0;
            return on ? h("span", { class: "dot", style: { "--cc": c.color }, title: c.display }) : "";
          }));
        }))),
      h("div", { class: "grid" }, CHARS.map(function (c) {
        return h("section", null, charHead(c, "Professions"), c.professions.map(function (p) {
          var isCraft = !!P.professions.crafting[p.name], v = skill(c.id, p.name);
          return h("div", { style: { margin: "8px 0" } },
            h("div", { class: "row", style: { display: "flex", gap: "8px", "align-items": "center" } },
              wl(p.name), h("span", { class: "dim" }, p.until ? p.from + "–" + p.until : p.from > 1 ? "from " + p.from : ""),
              h("input", { type: "number", min: "0", max: "300", value: String(v), "aria-label": c.display + " " + p.name, style: { "margin-left": "auto" },
                onchange: function (e) { S.skills[c.id] = S.skills[c.id] || {}; S.skills[c.id][p.name] = Math.max(0, Math.min(300, parseInt(e.target.value, 10) || 0)); save(); } }),
              h("span", { class: "dim" }, "/ 300")),
            bar(v, 300, c.color), isCraft ? h("div", { class: "dim" }, "Legacy at 150 · 225 · 300") : null);
        }));
      })),
      h("section", null, h("h2", null, "Pairings"), table(["Craft", "Uses", "Note"], Object.keys(P.professions.crafting).map(function (k) {
        var x = P.professions.crafting[k]; return [k, x.uses.join(", "), x.note || ""];
      })), h("ul", { class: "plain" }, P.professions.notes.map(function (n) { return h("li", null, L(n)); })))
    ];
  }
  function vLegacy() {
    var ch = P.legacy.challenges;
    return [
      h("section", null, h("h2", null, "Legacy points"), h("div", { class: "metrics" },
        h("div", { class: "metric" }, h("b", null, String(earned())), h("span", null, "Earned")),
        h("div", { class: "metric" }, h("b", null, String(P.coverage.legacy_from_plan)), h("span", null, P.coverage.distinct_classes + " classes · " + P.coverage.crafts_covered + " crafts")),
        h("div", { class: "metric" }, h("b", null, String(P.legacy.spend_cap)), h("span", null, "Spend cap at launch"))), rewardTrack(earned())),
      h("div", { class: "grid" },
        h("section", null, h("h2", null, "Challenges"), table(["Category", "Points", "How"], [
          ["Classes", String(ch["class"].total), "Each class at 25, 45, 60"], ["Crafts", String(ch.craft.total), "Each craft at 150, 225, 300"],
          ["PvP", String(ch.pvp.total), ch.pvp.items.join(", ")], ["Dungeons", String(ch.dungeon.total), ch.dungeon.items.join(", ")],
          ["Raids", String(ch.raid.total), ch.raid.items.join(", ")], ["Adventure", String(ch.adventure.total), ch.adventure.items.join(", ")]])),
        h("section", null, h("h2", null, "Account"), checklist(P.account))),
      h("div", { class: "grid" }, Object.keys(P.legacy.trees).map(function (t) {
        return h("section", null, h("h2", null, t), table(["Perk", "Ranks", "Effect"], P.legacy.trees[t].map(function (p) { return [p[0], String(p[1]), p[2]]; })));
      })),
      h("section", null, h("h2", null, "Projection"), table(["By the end of", "Points"], P.coverage.projection.map(function (p) { return [p.at.replace("-", "–"), String(p.points)]; })))
    ];
  }
  function vDungeons() {
    return [h("section", null, h("h2", null, "Dungeons"), table(["Dungeon", "Levels", "Zone", "Spelunker", ""], P.dungeons.map(function (d) {
      return [d.name, d.min + "–" + d.max, d.zone, d.spelunker || "", h("span", null, d["new"] ? h("span", { class: "tag new" }, "New") : null, " ", d.travel ? h("span", { class: "tag" }, "Enemy territory") : null, " ", statusTag(d.status))];
    })))];
  }
  function vWorld() {
    var fac = P.roster.faction, bag = P.sleeping_bag;
    return [
      h("section", null, h("h2", null, "Zones"), table(["Zone", "Levels", "Quests", ""], P.zones.map(function (z) {
        return [z.name, z.min + "–" + z.max, z.quests[fac] == null ? "" : String(z.quests[fac]), h("span", null, z["new"] ? h("span", { class: "tag new" }, "New") : null, " ", statusTag(z.status))];
      }))),
      h("div", { class: "grid" },
        h("section", null, h("h2", null, "Boats, zeppelins and trams"), table(["From", "To", "Type", ""], P.transport.map(function (t) { return [t.from, t.to, t.kind, statusTag(t.status) || ""]; }))),
        h("section", null, h("h2", null, "Flight paths"), h("p", null, P.flight_paths.map(function (f, i) { return [i ? " · " : "", wl(f)]; })))),
      h("section", null, h("h2", null, bag.name + " · from " + bag.min_level), h("p", null, L(bag.reward)),
        table(["Quest", "Where"], bag.steps.map(function (st) { return [st.quest, st[fac] || st.where]; })))
    ];
  }
  function vReference() {
    var v = P.validation, unv = [];
    CHARS.forEach(function (c) { c.milestones.forEach(function (m) { if (m.status === "unverified" || m.status === "classic") unv.push([m.name, c["class"], m.status]); }); });
    return [
      v.warnings.length || v.info.length ? h("section", null, h("h2", null, "Roster notes"), h("ul", { class: "plain" }, v.warnings.concat(v.info).map(function (x) { return h("li", null, L(x)); }))) : null,
      h("section", null, h("h2", null, "Open questions"), table(["Item", "Class", "Data"], unv.map(function (u) { return [u[0], u[1], statusTag(u[2])]; }))),
      h("section", null, h("h2", null, "Sources"), h("ul", { class: "plain" }, Object.keys(P.sources).map(function (k) {
        var x = P.sources[k]; return h("li", null, h("a", { href: x.url, target: "_blank", rel: "noopener noreferrer" }, x.title), h("span", { class: "dim" }, " · " + x.site));
      })))
    ];
  }

  // ---------- export / import
  function exportJSON() {
    var json = JSON.stringify(S, null, 2);
    var a = h("a", { href: URL.createObjectURL(new Blob([json], { type: "application/json" })), download: "progress-" + today() + ".json" });
    document.body.appendChild(a); a.click(); a.remove();
    try { navigator.clipboard.writeText(json); } catch (e) { /* download is enough */ }
  }
  // LegacyTracker SavedVariables (WTF\Account\<ACCOUNT>\SavedVariables\LegacyTracker.lua) -> progress.
  function parseLua(src) {
    var i = 0, n = src.length;
    function ws() {
      for (;;) {
        while (i < n && /\s/.test(src[i])) i++;
        if (src.substr(i, 2) === "--") { while (i < n && src[i] !== "\n") i++; } else return;
      }
    }
    function str() {
      var q = src[i++], out = "";
      while (i < n && src[i] !== q) {
        if (src[i] === "\\") {
          i++; var c = src[i];
          if (/[0-9]/.test(c)) { var d = src.substr(i, 3).match(/^[0-9]{1,3}/)[0]; out += String.fromCharCode(+d); i += d.length; continue; }
          out += ({ n: "\n", t: "\t", r: "\r", "\n": "\n" })[c] || c; i++;
        } else out += src[i++];
      }
      i++; return out;
    }
    function val() {
      ws(); var c = src[i];
      if (c === "{") return tbl();
      if (c === '"' || c === "'") return str();
      var m = src.slice(i).match(/^(-?(?:0x[0-9a-fA-F]+|[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)|true|false|nil)/);
      if (!m) throw new Error("Lua parse error at " + i);
      i += m[0].length;
      return m[0] === "true" ? true : m[0] === "false" ? false : m[0] === "nil" ? null : Number(m[0]);
    }
    function tbl() {
      i++; var obj = {}, arr = [], next = 1;
      for (;;) {
        ws(); if (src[i] === "}") { i++; break; }
        var k;
        if (src[i] === "[") { i++; k = val(); ws(); i++; ws(); i++; }
        else { var m = src.slice(i).match(/^([A-Za-z_][A-Za-z0-9_]*)\s*=(?!=)/); if (m) { k = m[1]; i += m[0].length; } }
        var v = val();
        if (k === undefined) { k = next++; arr.push(v); }
        obj[k] = v; ws(); if (src[i] === "," || src[i] === ";") i++;
      }
      return obj;
    }
    var out = {};
    for (;;) {
      ws(); if (i >= n) break;
      var m = src.slice(i).match(/^([A-Za-z_][A-Za-z0-9_]*)\s*=/);
      if (!m) throw new Error("Lua parse error at " + i);
      i += m[0].length; out[m[1]] = val();
    }
    return out;
  }
  function fromAddon(text) {
    var db = parseLua(text).LegacyTrackerDB || {}, chars = db.chars || {}, byName = {}, best = {}, extra = { checks: {}, levels: {}, skills: {} }, skipped = [];
    CHARS.forEach(function (c) { byName[c.name.toLowerCase()] = c.id; });
    var map = Object.assign({}, (P.progress && P.progress.map) || {}, S.map || {});
    Object.keys(map).forEach(function (k) { byName[k.toLowerCase()] = map[k]; });
    Object.keys(chars).forEach(function (key) {
      var c = chars[key]; if (!c || typeof c !== "object") return;
      var nm = String(c.name || key.split("-").pop()).toLowerCase(), id = byName[nm] || byName[key.toLowerCase()];
      if (!id) { skipped.push(c.name || key); return; }
      if (!best[id] || (c.lastSeen || 0) > (best[id].lastSeen || 0)) best[id] = c;
    });
    Object.keys(best).forEach(function (id) {
      var c = best[id], xm = c.xpMax || 0, rs = c.rested || 0;
      extra.levels[id] = { level: c.level, rested: !rs || !xm ? "Empty" : rs / xm >= 1.495 ? "Full" : "Partial", source: "LegacyTracker",
        updated: c.lastSeen ? new Date(c.lastSeen * 1000).toISOString().slice(0, 10) : today() };
      if (xm) { extra.levels[id].pctToNext = Math.round((c.xp || 0) / xm * 1000) / 10; extra.levels[id].restedBubbles = Math.round(rs / xm * 200) / 10; }
      if (c.zone) extra.levels[id].zone = c.zone;
      extra.skills[id] = {};
      Object.keys(c.professions || {}).forEach(function (p) { var v = c.professions[p]; if (v && v.rank != null) extra.skills[id][p] = v.rank; });
    });
    return { extra: extra, matched: Object.keys(best).length, skipped: skipped };
  }
  function importJSON() {
    var ta = h("textarea", { "aria-label": "Progress JSON or LegacyTracker.lua" });
    var file = h("input", { type: "file", accept: "application/json,.json,.lua", onchange: function (e) { var f = e.target.files[0]; if (f) f.text().then(function (t) { ta.value = t; }); } });
    var dlg = h("dialog", null, h("h2", null, "Import progress"), file, ta,
      h("div", { class: "actions", style: { "justify-content": "flex-end", "margin-top": "8px" } },
        h("button", { type: "button", onclick: function () { dlg.close(); dlg.remove(); } }, "Cancel"),
        h("button", { type: "button", onclick: function () {
          try {
            if (/LegacyTrackerDB\s*=/.test(ta.value)) {
              var r = fromAddon(ta.value);
              if (!r.matched) throw new Error("No roster characters in LegacyTracker.lua" + (r.skipped.length ? ": " + r.skipped.join(", ") : ""));
              S = merge(S, r.extra);
            } else { var m = ta.value.match(/\{[\s\S]*\}/); S = merge(S, JSON.parse(m ? m[0] : ta.value)); }
            dlg.close(); dlg.remove(); save();
          } catch (e) { ta.setCustomValidity(e.message && /LegacyTracker/.test(e.message) ? e.message : "Not valid progress JSON or LegacyTracker.lua"); ta.reportValidity(); }
        } }, "Import")));
    document.body.appendChild(dlg); dlg.showModal();
  }

  // ---------- render
  function render() {
    var top = document.getElementById("top"), nav = document.getElementById("tabs"), view = document.getElementById("view");
    document.title = P.roster.name + " · Legacy Mission Control";
    top.replaceChildren(
      h("div", null, h("h1", null, P.roster.name), h("div", { class: "meta" }, h("span", null, wl(P.roster.faction)), h("span", null, P.roster.ruleset), h("span", null, CHARS.length + " characters"))),
      h("div", { class: "actions" },
        h("button", { type: "button", onclick: exportJSON }, "Export progress"),
        h("button", { type: "button", onclick: importJSON }, "Import progress")));
    nav.replaceChildren.apply(nav, TABS.map(function (t) {
      return h("button", { type: "button", role: "tab", "aria-selected": UI.tab === t[0] ? "true" : "false", onclick: function () { UI.tab = t[0]; try { history.replaceState(null, "", "#" + t[0]); } catch (e) { /* file:// */ } render(); } }, t[1]);
    }));
    if (!TABS.some(function (t) { return t[0] === UI.tab; })) UI.tab = "today";
    var v = { today: vToday, road: vRoad, levels: vLevels, profs: vProfs, legacy: vLegacy, dungeons: vDungeons, world: vWorld, reference: vReference }[UI.tab]();
    view.replaceChildren.apply(view, [].concat(v).filter(Boolean));
    document.getElementById("foot").replaceChildren(h("span", null, "Progress saved " + (S.updated || "never") + " · ",
      h("a", { href: "https://github.com/BradGroux/wow-forever-mission-control", target: "_blank", rel: "noopener noreferrer" }, "WoW Forever Legacy Mission Control")));
  }
  render();
})();
