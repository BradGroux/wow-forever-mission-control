/* WoW Forever Legacy Mission Control: static page, no build step, no backend.
   Reads window.MC_PLAN (web/data/plan.js or plan.example.js, written by ./mc generate).
   Progress lives in localStorage; Export/Import move it as JSON. */
(function () {
  "use strict";
  var P = window.MC_PLAN;
  if (!P) { document.getElementById("view").textContent = "No plan data. Run ./mc generate."; return; }

  // ---------- fixed colors (also used inside SVG, where CSS variables are avoided)
  var C = { t1: "#ECECEC", t2: "#BEBEBE", t3: "#9C9C9C", f2: "#2B2B2B", b1: "#4A4A4A", b0: "#353535", bg: "#070707", gold: "#C9A227" };
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
    if (st === "classic") return h("span", { class: "pill warn", title: "Classic data, unconfirmed for Forever" }, "Classic data");
    if (st === "unverified") return h("span", { class: "pill warn" }, "Unverified");
    if (st === "beta") return h("span", { class: "pill" }, "Seen in beta");
    return null;
  }
  function icon(c, size) {
    var z = size || 26;
    var img = h("img", { class: "icon", src: c.icon, alt: c["class"], width: z, height: z, style: { "--cc": c.color, width: z + "px", height: z + "px" } });
    img.addEventListener("error", function () { img.replaceWith(h("span", { class: "icon", style: { "--cc": c.color, width: z + "px", height: z + "px", display: "inline-grid", "place-items": "center", color: c.color, "font-weight": "700" } }, c["class"].charAt(0))); });
    return img;
  }
  function ticks(cls) {
    return P.brackets.slice(1).map(function (b) { return h("i", { class: cls, style: { left: (b.from / 60 * 100) + "%" } }); });
  }
  function bar(value, max, color, cls) {
    return h("div", { class: "bar " + (cls || ""), style: { "--cc": color } }, h("b", { style: { width: Math.max(0, Math.min(100, value / max * 100)) + "%" } }));
  }
  function nm(c) { return h("span", { class: "nm", style: { "--cc": c.color } }, c.display); }

  // ---------- components (look of the Grok Bot canvas)
  function sec(title, body, actions, id) {
    return h("section", { class: "sec", id: id },
      title ? h("div", { class: "sec-head" }, h("h2", null, title), actions ? h("div", { class: "acts" }, actions) : null) : null,
      h("div", { class: "sec-body" }, body));
  }
  function panel(head) { return h("div", { class: "panel" }, head, [].slice.call(arguments, 1)); }
  function charHead(c, title) {
    return h("div", { class: "phead", style: { "--cc": c.color } }, icon(c, 30), h("div", null, h("span", { class: "nm" }, c.display), h("span", { class: "pt" }, title)));
  }
  function checklist(items, color) {
    var done = items.filter(function (i) { return S.checks[i.id]; }).length;
    return h("div", { class: "cl", style: { "--cc": color || C.gold } },
      h("div", { class: "cl-prog" }, h("div", { class: "track" }, h("b", { style: { width: (items.length ? done / items.length * 100 : 0) + "%" } })), h("span", null, done + " / " + items.length)),
      h("div", { role: "list" }, items.map(function (it) {
        var on = !!S.checks[it.id];
        function toggle() { if (on) delete S.checks[it.id]; else S.checks[it.id] = true; save(); }
        return h("div", { class: "ck", role: "checkbox", tabindex: "0", "aria-checked": on ? "true" : "false",
          onclick: function (e) { if (e.target.tagName !== "A") toggle(); }, onkeydown: function (e) { if (e.key === " " || e.key === "Enter") { e.preventDefault(); toggle(); } } },
          h("span", { class: "box", "aria-hidden": "true" }, on ? "✓" : ""),
          h("span", { class: "tx" }, L(it.text), it.detail ? h("span", { class: "dt" }, L(it.detail)) : null),
          it.tag ? h("span", { class: "tg" }, it.tag) : null);
      })));
  }
  function steps(items) {
    return h("ol", { class: "steps" }, items.map(function (it, i) {
      return h("li", null, h("div", { class: "rail" }, h("span", { class: "sn" }, String(i + 1)), h("span", { class: "line" })),
        h("div", { class: "st" }, h("p", { class: "t" }, L(it.title), " ", it.tag || null), it.sub ? h("p", { class: "s" }, L(it.sub)) : null));
    }));
  }
  function segmented(options, value, onpick) {
    return h("div", { class: "seg", role: "group" }, options.map(function (o) {
      return h("button", { type: "button", "aria-pressed": o.value === value ? "true" : "false", onclick: function () { onpick(o.value); } }, o.label);
    }));
  }
  function table(cols, rows, numCols) {
    numCols = numCols || [];
    return h("div", { class: "tbl" }, h("table", null, h("thead", null, h("tr", null, cols.map(function (c, i) { return h("th", { class: numCols.indexOf(i) >= 0 ? "num" : null }, c); }))),
      h("tbody", null, rows.map(function (r) { return h("tr", null, r.map(function (c, i) { return h("td", { class: numCols.indexOf(i) >= 0 ? "num" : null }, typeof c === "string" ? L(c) : c); })); }))));
  }
  function bullets(list) { return h("ul", { class: "bul" }, list.map(function (x) { return h("li", null, typeof x === "string" ? L(x) : x); })); }

  function rosterCards() {
    var nu = nextUp();
    return h("div", { class: "roster", role: "radiogroup", "aria-label": "Select a character" }, CHARS.map(function (c) {
      var l = lv(c.id), b = bracketOf(l), st = S.levels[c.id] || {};
      return h("button", { type: "button", class: "rc", role: "radio", "aria-checked": UI.char === c.id ? "true" : "false", style: { "--cc": c.color },
        onclick: function () { UI.char = c.id; render(); } },
        h("div", { class: "rc-top" }, icon(c), h("span", { class: "nm" }, c.display), h("span", { class: "meta" }, c.race + " " + c["class"]),
          c.id === nu.id ? h("span", { class: "upnext" }, "Up next") : null),
        h("div", { class: "rc-row" }, h("span", null, "Level " + l + " of 60"), h("span", null, b.from + "–" + b.to + " target " + b.to)),
        h("div", { class: "rc-bar" }, h("b", { style: { width: (l / 60 * 100) + "%" } }), ticks()),
        h("div", { class: "rc-row q" }, h("span", null, "Rested: " + (st.updated ? (st.rested || "Empty").toLowerCase() : "none yet")),
          h("span", null, c.professions.filter(function (p) { return !p.until; }).map(function (p) { return p.name; }).join(" + "))));
    }));
  }
  function levelRows(edit) {
    return h("div", { class: "lvls" }, CHARS.map(function (c) {
      var l = lv(c.id), st = S.levels[c.id] || {}, b = bracketOf(l);
      return h("div", { class: "lvrow", style: { "--cc": c.color } },
        h("div", { class: "who" }, icon(c, 22), h("span", { class: "nm" }, c.display),
          edit ? h("input", { type: "number", class: "lvin", min: "1", max: "60", value: String(l), "aria-label": c.display + " level",
            onchange: function (e) { var v = Math.max(1, Math.min(60, parseInt(e.target.value, 10) || 1)); S.levels[c.id] = Object.assign({}, S.levels[c.id], { level: v, updated: today() }); save(); } })
            : h("span", { class: "lvn" }, String(l))),
        h("div", { class: "lvbar", "aria-label": c.display + " level " + l + " of 60" }, h("b", { style: { width: (l / 60 * 100) + "%" } }), ticks()),
        h("div", { class: "lvmeta" }, h("span", { class: "br" }, b.from + "–" + b.to),
          edit ? h("select", { class: "rsel", "aria-label": c.display + " rested", onchange: function (e) { S.levels[c.id] = Object.assign({}, S.levels[c.id], { rested: e.target.value, updated: today() }); save(); } },
            ["Empty", "Partial", "Full"].map(function (r) { return h("option", { value: r, selected: r === (st.rested || "Empty") }, "Rested " + r.toLowerCase()); }))
            : h("span", { class: "q" }, "Rested " + (st.rested || "Empty").toLowerCase()),
          h("span", null, st.updated || "")));
    }), h("div", { class: "lvaxis" }, [1, 10, 20, 30, 40, 50, 60].map(function (n) { return h("span", { style: { left: (n / 60 * 100) + "%" } }, String(n)); })));
  }

  // ---------- Road to 60 timeline (SVG, fixed hex colors)
  var SHORT = { "Ragefire Chasm": "RFC", "Wailing Caverns": "WC", "Shadowfang Keep": "SFK", "Blackfathom Deeps": "BFD", "Razorfen Kraul": "RFK", "Razorfen Downs": "RFD",
    "Scarlet Monastery": "SM", "Zul'Farrak": "ZF", "Sunken Temple": "ST", "Blackrock Depths": "BRD", "Lower Blackrock Spire": "LBRS", "Upper Blackrock Spire": "UBRS",
    "Dire Maul": "DM", "Scholomance": "Scholo", "Stratholme": "Strat", "City of Dalaran": "Dalaran", "Excavation Site: Wetlands": "Excavation", "The Hall of Thanes": "Thanes",
    "Ruins of Lordaeron": "Lordaeron", "Krol'dok Stronghold": "Krol'dok", "The Drowned City": "Drowned", "Alcaz Prison": "Alcaz", "Blackmaw Hold": "Blackmaw", "Shaper's Terrace": "Shaper's" };
  function short(n) { if (SHORT[n]) return SHORT[n]; n = n.replace(/^The /, "").split(":")[0]; return n.length > 16 ? n.split(" ").slice(0, 2).join(" ") : n; }
  function timeline() {
    var W = 1120, left = 132, right = 28, top = 8, bandH = 34, tierH = 19, fs = 14.5;
    var x = function (l) { return left + (l - 1) / 59 * (W - left - right); };
    var c0 = byId[UI.char];
    var rows = [{ label: "Dungeons", fill: "#FCFCFC", marks: P.dungeons.map(function (d) { return { lv: Math.round((d.min + d.max) / 2), name: d.name, label: short(d.name) }; }) }];
    CHARS.forEach(function (c) { rows.push({ label: "Class · " + c.display, fill: c.color, id: c.id, dim: c.id !== c0.id, marks: c.milestones.map(function (m) { return { lv: Math.max(1, m.level), name: m.name, label: short(m.name) }; }) }); });
    rows.push({ label: "Legacy", fill: C.gold, marks: [{ lv: 25, name: "Novice class points (25)", label: "Class 25" }, { lv: 45, name: "Experienced class points (45)", label: "Class 45" }, { lv: 60, name: "Master class points (60)", label: "Class 60" },
      { lv: 25, name: "Crafts to 150 by 25", label: "Crafts 150" }, { lv: 32, name: "Crafts to 225 by 32", label: "Crafts 225" }, { lv: 52, name: "Crafts to 300 by 52", label: "Crafts 300" }] });
    // place labels in tiers above the dot: tier 0 sits on the dot, higher tiers get a connector line
    rows.forEach(function (r) {
      var ends = [];
      r.marks.sort(function (a, b) { return a.lv - b.lv; }).forEach(function (m) {
        var cx = x(m.lv), w = m.label.length * fs * 0.52 + 10;
        m.cx = cx; m.tier = -1;
        for (var t = 0; t < 3; t++) { if ((ends[t] === undefined || cx - w / 2 > ends[t]) && cx + w / 2 < W + 30) { m.tier = t; ends[t] = cx + w / 2; break; } }
      });
      r.tiers = Math.max(1, 1 + Math.max.apply(null, r.marks.map(function (m) { return m.tier; }).concat([0])));
      r.h = 24 + r.tiers * tierH;
    });
    var H = top + bandH + 12 + rows.reduce(function (a, r) { return a + r.h; }, 0) + 22;
    var svg = s("svg", { viewBox: "0 0 " + W + " " + H, width: "100%", role: "img", "aria-label": "Level 1 to 60 timeline with brackets and milestones" });
    P.brackets.forEach(function (b) {
      var on = UI.bracket === b.id, bw = x(b.to) - x(b.from) - 3;
      svg.appendChild(s("g", { style: { cursor: "pointer" }, onclick: function () { UI.bracket = b.id; UI.tab = "brackets"; setHash(); render(); } },
        s("title", null, "Levels " + b.from + "–" + b.to),
        s("rect", { x: x(b.from) + 1.5, y: top, width: bw, height: bandH, rx: 6, fill: on ? "#ECECEC" : C.f2, stroke: on ? "#ECECEC" : C.b1 }),
        s("text", { x: (x(b.from) + x(b.to)) / 2, y: top + bandH / 2 + 5.5, "text-anchor": "middle", style: { "font-size": (bw < 70 ? 15 : 16) + "px", "font-weight": 600 }, fill: on ? "#070707" : C.t1 }, b.from + "–" + b.to)));
    });
    var y0 = top + bandH + 12;
    rows.forEach(function (r, i) {
      var y = y0 + r.h - 12;
      if (i > 0) svg.appendChild(s("line", { x1: 8, x2: W - 8, y1: y0 - 2, y2: y0 - 2, stroke: C.b0, "stroke-dasharray": "2 4" }));
      svg.appendChild(s("text", { x: 8, y: y + 5, fill: C.t3, style: { "font-size": "15px" } }, r.label));
      svg.appendChild(s("line", { x1: left, x2: W - right, y1: y, y2: y, stroke: C.b1 }));
      if (r.id) svg.appendChild(s("rect", { x: left, y: y - 1.5, width: Math.max(0, x(lv(r.id)) - left), height: 3, rx: 1.5, fill: r.fill }));
      r.marks.forEach(function (m) {
        var g = s("g", { opacity: r.dim ? 0.55 : 1 }, s("title", null, m.name + " · level " + m.lv));
        var ly = y - 14 - m.tier * tierH;
        if (m.tier > 0) g.appendChild(s("line", { x1: m.cx, x2: m.cx, y1: ly + 4, y2: y - 8, stroke: C.b1 }));
        g.appendChild(s("circle", { cx: m.cx, cy: y, r: 6, fill: r.fill }));
        var tw = m.label.length * fs * 0.52, anchor = m.cx + tw / 2 > W - 4 ? "end" : "middle", tx = anchor === "end" ? Math.min(W - 4, m.cx + 8) : m.cx;
        if (m.tier >= 0) g.appendChild(s("text", { x: tx, y: ly, "text-anchor": anchor, fill: r.dim ? C.t3 : C.t2, style: { "font-size": fs + "px" } }, m.label));
        svg.appendChild(g);
      });
      y0 += r.h;
    });
    [1, 10, 20, 30, 40, 50, 60].forEach(function (n) { svg.appendChild(s("text", { x: x(n), y: H - 4, "text-anchor": "middle", fill: C.t3, style: { "font-size": "13px" } }, String(n))); });
    return svg;
  }

  function rewardTrack(points) {
    var W = 1120, L0 = 24, R0 = 24, y = 50, max = 65;
    var x = function (p) { return L0 + p / max * (W - L0 - R0); };
    var svg = s("svg", { viewBox: "0 0 " + W + " 110", width: "100%", role: "img", "aria-label": "Legacy reward track" },
      s("rect", { x: L0, y: y - 5, width: W - L0 - R0, height: 10, rx: 5, fill: C.f2 }),
      s("rect", { x: L0, y: y - 5, width: Math.max(0, x(points) - L0), height: 10, rx: 5, fill: C.gold }),
      s("rect", { x: x(P.legacy.spend_cap) - 1, y: y - 14, width: 2, height: 28, fill: C.t1 }),
      s("text", { x: x(P.legacy.spend_cap), y: y - 20, "text-anchor": "middle", fill: C.t1, style: { "font-size": "13px", "font-weight": 600 } }, P.legacy.spend_cap + " spend cap"),
      s("rect", { x: x(P.coverage.legacy_from_plan) - 1, y: y - 14, width: 2, height: 28, fill: C.t3 }),
      s("text", { x: x(P.coverage.legacy_from_plan), y: y - 20, "text-anchor": "middle", fill: C.t2, style: { "font-size": "13px" } }, P.coverage.legacy_from_plan + " in the plan"));
    P.legacy.rewards.forEach(function (r) {
      svg.appendChild(s("circle", { cx: x(r.points), cy: y, r: 8, fill: C.bg, stroke: C.gold, "stroke-width": 3 }));
      svg.appendChild(s("text", { x: x(r.points), y: y + 30, "text-anchor": "middle", fill: C.t1, style: { "font-size": "13px", "font-weight": 600 } }, String(r.points)));
      svg.appendChild(s("a", { href: (LINKS[r.name] || {}).url || "#", target: "_blank" }, s("text", { x: x(r.points), y: y + 48, "text-anchor": "middle", fill: C.t2, style: { "font-size": "13px" } }, r.name)));
    });
    return svg;
  }

  // ---------- views
  var UI = { tab: (location.hash || "#today").slice(1), char: CHARS[0].id, bracket: bracketOf(lv(nextUp().id)).id };
  var ALIAS = { road: "brackets", levels: "brackets" };
  if (ALIAS[UI.tab]) UI.tab = ALIAS[UI.tab];
  var TABS = [["today", "Today"], ["brackets", "Brackets"], ["rested", "Rested"], ["legacy", "Legacy"], ["profs", "Professions"], ["dungeons", "Dungeons + bag"], ["classes", "Classes"], ["world", "World"], ["reference", "Reference"]];
  function setHash() { try { history.replaceState(null, "", "#" + UI.tab); } catch (e) { /* file:// */ } }

  function vToday() {
    var c = byId[UI.char], l = lv(c.id), b = bracketOf(l), nu = nextUp(), nb = bracketOf(lv(nu.id));
    var next = c.milestones.filter(function (m) { return m.level >= l; }).slice(0, 5);
    return [
      sec("Status", h("div", { class: "metrics" },
        h("div", null, h("b", null, nu.display), h("span", null, "Up next"), h("i", null, nu["class"] + " · level " + lv(nu.id))),
        h("div", null, h("b", null, nb.from + "–" + nb.to), h("span", null, "Current bracket"), h("i", null, "Target " + nb.to)),
        h("div", null, h("b", null, earned() + " / " + P.coverage.legacy_from_plan), h("span", null, "Legacy points"), h("i", null, "Spend cap " + P.legacy.spend_cap)),
        h("div", null, h("b", null, fmtDate(P.roster.launch)), h("span", null, "Launch"), h("i", null, P.roster.ruleset))),
        [h("button", { type: "button", class: "ob", onclick: exportJSON }, "Export progress"), h("button", { type: "button", class: "ob", onclick: importJSON }, "Import progress")]),
      sec("Levels", levelRows(true)),
      h("div", { class: "grid2 gap-top" },
        panel(charHead(c, "Next milestones"), next.length ? steps(next.map(function (m) { return { title: m.name, sub: "Level " + m.level + " · " + m.kind, tag: statusTag(m.status) }; })) : h("p", { class: "q" }, "All milestones reached")),
        panel(charHead(c, b.from + "–" + b.to + " to-do"), checklist(b.tasks[c.id] || [], c.color))),
      sec("Road to 60", h("div", { class: "hscroll" }, timeline()))
    ];
  }
  function vBrackets() {
    var b = P.brackets.filter(function (x) { return x.id === UI.bracket; })[0] || P.brackets[0];
    return [
      sec("Levels " + b.from + "–" + b.to, [
        segmented(P.brackets.map(function (x) { return { value: x.id, label: x.from + "–" + x.to }; }), b.id, function (v) { UI.bracket = v; render(); }),
        h("div", { class: "grid2 gap-top" },
          h("div", null, b.why.length ? [h("h3", null, "Why this bracket"), bullets(b.why)] : null, h("h3", null, "Zones"), h("p", null, b.zones.map(function (z, i) { return [i ? " · " : "", wl(z)]; }))),
          h("div", null, h("h3", null, "Rotation"), table(["Character", "Target", "Zones", "Log out"], b.rotation.map(function (r) {
            var c = byId[r["char"]]; return [nm(c), String(r.target), r.zones.join(", "), r.logout];
          }), [1])))]),
      h("div", { class: "grid2 gap-top" }, CHARS.map(function (c) { return panel(charHead(c, b.from + "–" + b.to), checklist(b.tasks[c.id] || [], c.color)); }))
    ];
  }
  function vRested() {
    return [sec("Levels", levelRows(true)),
      sec("From the addon", table(["Character", "Level", "To next", "Rested", "Zone", "Updated"], CHARS.map(function (c) {
        var st = S.levels[c.id] || {};
        return [nm(c), String(lv(c.id)), st.pctToNext != null ? st.pctToNext + "%" : "", st.restedBubbles != null ? st.restedBubbles + " bubbles" : (st.rested || "Empty"), st.zone || "", st.updated || ""];
      }), [1, 2]))];
  }
  function vClasses() {
    return [h("div", { class: "grid2" }, CHARS.map(function (c) {
      return panel(charHead(c, c.race + " " + c["class"] + " · " + c.leveling_spec + " → " + c.endgame_spec),
        steps(c.milestones.map(function (m) { return { title: m.name, sub: "Level " + m.level + " · " + m.kind, tag: statusTag(m.status) }; })),
        c.racials && c.racials.length ? h("p", { class: "q" }, "Racials: ", c.racials.map(function (r, i) { return [i ? ", " : "", wl(r)]; })) : null);
    }))];
  }
  function vProfs() {
    var crafts = Object.keys(P.coverage.crafts);
    return [
      sec("Craft coverage", table(["Craft"].concat(CHARS.map(function (c) { return nm(c); })),
        crafts.map(function (cr) {
          return [cr].concat(CHARS.map(function (c) { return P.coverage.crafts[cr].indexOf(c.id) >= 0 ? h("span", { class: "dot", style: { "--cc": c.color }, title: c.display }) : ""; }));
        }))),
      h("div", { class: "grid2 gap-top" }, CHARS.map(function (c) {
        return panel(charHead(c, "Professions"), h("div", { class: "profs" }, c.professions.map(function (p) {
          var isCraft = !!P.professions.crafting[p.name], v = skill(c.id, p.name);
          return h("div", { class: "prof", style: { "--cc": c.color } },
            h("div", { class: "pr" }, wl(p.name), h("span", { class: "q" }, p.until ? p.from + "–" + p.until : p.from > 1 ? "from " + p.from : ""),
              h("input", { type: "number", class: "skin", min: "0", max: "300", value: String(v), "aria-label": c.display + " " + p.name,
                onchange: function (e) { S.skills[c.id] = S.skills[c.id] || {}; S.skills[c.id][p.name] = Math.max(0, Math.min(300, parseInt(e.target.value, 10) || 0)); save(); } }),
              h("span", { class: "q" }, "/ 300")),
            h("div", { class: "pbar" }, h("b", { style: { width: (v / 300 * 100) + "%" } }), isCraft ? [150, 225].map(function (t) { return h("i", { style: { left: (t / 300 * 100) + "%" } }); }) : null));
        })));
      })),
      sec("Pairings", [table(["Craft", "Uses", "Note"], Object.keys(P.professions.crafting).map(function (k) { var x = P.professions.crafting[k]; return [k, x.uses.join(", "), x.note || ""]; })),
        P.professions.notes.length ? bullets(P.professions.notes) : null])
    ];
  }
  function vLegacy() {
    var ch = P.legacy.challenges;
    return [
      sec("Legacy points", [h("div", { class: "metrics" },
        h("div", null, h("b", null, String(earned())), h("span", null, "Earned")),
        h("div", null, h("b", null, String(P.coverage.legacy_from_plan)), h("span", null, "In the plan"), h("i", null, P.coverage.distinct_classes + " classes · " + P.coverage.crafts_covered + " crafts")),
        h("div", null, h("b", null, String(P.legacy.spend_cap)), h("span", null, "Spend cap at launch")),
        h("div", null, h("b", null, "65"), h("span", null, "All challenges"))), h("div", { class: "hscroll" }, rewardTrack(earned()))]),
      h("div", { class: "grid2 gap-top" },
        panel(h("h3", { class: "ph3" }, "Challenges"), table(["Category", "Points", "How"], [
          ["Classes", String(ch["class"].total), "Each class at 25, 45, 60"], ["Crafts", String(ch.craft.total), "Each craft at 150, 225, 300"],
          ["PvP", String(ch.pvp.total), ch.pvp.items.join(", ")], ["Dungeons", String(ch.dungeon.total), ch.dungeon.items.join(", ")],
          ["Raids", String(ch.raid.total), ch.raid.items.join(", ")], ["Adventure", String(ch.adventure.total), ch.adventure.items.join(", ")]], [1])),
        panel(h("h3", { class: "ph3" }, "Account"), checklist(P.account))),
      sec("Perk trees", h("div", { class: "grid3" }, Object.keys(P.legacy.trees).map(function (t) {
        return h("div", null, h("h3", null, t), table(["Perk", "Ranks", "Effect"], P.legacy.trees[t].map(function (p) { return [p[0], String(p[1]), p[2]]; }), [1]));
      }))),
      sec("Projection", table(["By the end of", "Points"], P.coverage.projection.map(function (p) { return [p.at.replace("-", "–"), String(p.points)]; }), [1]))
    ];
  }
  function vDungeons() {
    var fac = P.roster.faction, bag = P.sleeping_bag;
    return [
      sec("Dungeons", table(["Dungeon", "Levels", "Zone", "Spelunker", ""], P.dungeons.map(function (d) {
        return [d.name, d.min + "–" + d.max, d.zone, d.spelunker || "", h("span", { class: "pills" }, d["new"] ? h("span", { class: "pill new" }, "New") : null, d.access && d.access !== fac && d.access !== "both" && d.access !== "Both" ? h("span", { class: "pill" }, "Enemy territory") : null, statusTag(d.status))];
      }), [1])),
      sec(bag.name + " · from " + bag.min_level, [h("p", { class: "lead" }, L(bag.reward)), steps(bag.steps.map(function (st) { return { title: st.quest, sub: st[fac] || st.where }; }))])
    ];
  }
  function vWorld() {
    var fac = P.roster.faction;
    return [
      sec("Zones", table(["Zone", "Levels", "Quests", ""], P.zones.map(function (z) {
        return [z.name, z.min + "–" + z.max, z.quests[fac] == null ? "" : String(z.quests[fac]), h("span", { class: "pills" }, z["new"] ? h("span", { class: "pill new" }, "New") : null, statusTag(z.status))];
      }), [1, 2])),
      h("div", { class: "grid2 gap-top" },
        panel(h("h3", { class: "ph3" }, "Boats, zeppelins and trams"), table(["From", "To", "Type", ""], P.transport.map(function (t) { return [t.from, t.to, t.kind, statusTag(t.status) || ""]; }))),
        panel(h("h3", { class: "ph3" }, "Flight paths"), h("p", { class: "flow" }, P.flight_paths.map(function (f, i) { return [i ? " · " : "", wl(f)]; }))))
    ];
  }
  function vReference() {
    var v = P.validation, unv = [];
    CHARS.forEach(function (c) { c.milestones.forEach(function (m) { if (m.status === "unverified" || m.status === "classic") unv.push([m.name, c["class"], m.status]); }); });
    return [
      v.warnings.length || v.info.length ? sec("Roster notes", bullets(v.warnings.concat(v.info))) : null,
      sec("Open questions", table(["Item", "Class", "Data"], unv.map(function (u) { return [u[0], u[1], statusTag(u[2])]; }))),
      sec("Sources", h("ul", { class: "bul" }, Object.keys(P.sources).map(function (k) {
        var x = P.sources[k]; return h("li", null, h("a", { href: x.url, target: "_blank", rel: "noopener noreferrer" }, x.title), h("span", { class: "q" }, " · " + x.site));
      })))
    ];
  }
  function fmtDate(iso) {
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso || ""); if (!m) return iso;
    return ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][+m[2] - 1] + " " + (+m[3]);
  }

  // ---------- export / import
  function exportJSON() {
    var json = JSON.stringify(S, null, 2);
    var a = h("a", { href: URL.createObjectURL(new Blob([json], { type: "application/json" })), download: "progress-" + today() + ".json" });
    document.body.appendChild(a); a.click(); a.remove();
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
      h("h1", null, P.roster.name),
      h("p", { class: "sub" }, wl(P.roster.faction), " · " + P.roster.ruleset + " · " + CHARS.length + " characters"),
      rosterCards());
    if (!TABS.some(function (t) { return t[0] === UI.tab; })) UI.tab = "today";
    nav.replaceChildren.apply(nav, TABS.map(function (t) {
      return h("button", { type: "button", role: "tab", "aria-selected": UI.tab === t[0] ? "true" : "false", onclick: function () { UI.tab = t[0]; setHash(); render(); } }, h("span", null, t[1]));
    }));
    var v = { today: vToday, brackets: vBrackets, rested: vRested, legacy: vLegacy, profs: vProfs, dungeons: vDungeons, classes: vClasses, world: vWorld, reference: vReference }[UI.tab]();
    view.replaceChildren.apply(view, [].concat(v).filter(Boolean));
    document.getElementById("foot").replaceChildren(h("span", null, "Progress saved " + (S.updated || "never") + " · ",
      h("a", { href: "https://github.com/BradGroux/wow-forever-mission-control", target: "_blank", rel: "noopener noreferrer" }, "WoW Forever Legacy Mission Control")));
  }
  render();
})();
