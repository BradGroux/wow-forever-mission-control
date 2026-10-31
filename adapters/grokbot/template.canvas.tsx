// Grok Bot canvas adapter for WoW Forever Legacy Mission Control.
// Optional: the main page is web/index.html. ./mc generate fills the ROSTER and SAVED blocks below
// and writes adapters/grokbot/mission-control.canvas.tsx (or build/ for the example). Do not edit the blocks by hand.
import {
  Page, Section, Table, Segmented, Metrics, Grid, LinkCards,
  useState, useEffect, Fragment, useGrokTheme,
} from "grok/canvas";
import type { ReactNode, KeyboardEvent } from "grok/canvas";

type Plan = any;
type Rested = "Empty" | "Partial" | "Full";
type Saved = { version: number; roster: string; updated: string; checks: Record<string, boolean>; levels: Record<string, { level: number; rested: Rested; updated: string }>; skills: Record<string, Record<string, number>>; map: Record<string, string>; notes: string };
type Item = { id: string; text: string; tag?: string; detail?: string };

// ROSTER-START
// ROSTER-END

// SAVED-START
// SAVED-END

const SV = { t1: "#ECECEC", t2: "#BEBEBE", t3: "#9C9C9C", f2: "#2B2B2B", b1: "#4A4A4A", b0: "#353535", bg: "#141414", gold: "#C9A227" };
const CHARS: any[] = PLAN.characters;
const LINKS: Record<string, { url: string; direct: boolean }> = PLAN.links;
const KEYS: string[] = Object.keys(LINKS).sort((a: string, b: string) => b.length - a.length);
const RE_SRC: string = KEYS.map((k: string) => k.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|");

function WL({ name }: { name: string }) {
  const [hov, setHov] = useState(false);
  const e = LINKS[name];
  return (
    <a href={e.url} target="_blank" rel="noopener noreferrer" onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)} onClick={(ev) => ev.stopPropagation()}
      style={{ color: hov ? SV.gold : "inherit", textDecorationLine: "underline", textDecorationStyle: e.direct ? "solid" : "dotted", textDecorationColor: hov ? SV.gold : "rgba(201, 162, 39, 0.5)", textUnderlineOffset: 3 }}>
      {name}
    </a>
  );
}
const wordCh = (c: string | undefined): boolean => c !== undefined && /[A-Za-z0-9]/.test(c);
function L(text: string): ReactNode {
  if (!text || !RE_SRC) return text;
  const re = new RegExp(RE_SRC, "g");
  const out: ReactNode[] = [];
  let last = 0;
  let k = 0;
  let m: RegExpExecArray | null = re.exec(text);
  while (m !== null) {
    const s = m.index;
    const e = s + m[0].length;
    if (wordCh(text[s - 1]) || wordCh(text[e])) {
      re.lastIndex = s + 1;
    } else {
      if (s > last) out.push(text.slice(last, s));
      out.push(<WL key={`l${k}`} name={m[0]} />);
      k += 1;
      last = e;
    }
    m = re.exec(text);
  }
  if (k === 0) return text;
  if (last < text.length) out.push(text.slice(last));
  return <Fragment>{out}</Fragment>;
}
const LT = (rows: string[][]): ReactNode[][] => rows.map((r: string[]) => r.map((c: string) => L(c)));

// ---------- progress: SAVED (baked in by ./mc generate) + this session's clicks
const KEY = `mc-session-v${SAVED.version}-${SAVED.updated || "0"}-${PLAN.roster.key}`;
const store = (): any => { try { return (globalThis as any).localStorage ?? null; } catch { return null; } };
const loadChecks = (): Record<string, boolean> => {
  try { const s = store()?.getItem(KEY); return { ...SAVED.checks, ...(s ? JSON.parse(s) : {}) }; } catch { return { ...SAVED.checks }; }
};
let CHECKS: Record<string, boolean> = loadChecks();
const listeners = new Set<() => void>();
const setCheck = (k: string, v: boolean): void => {
  CHECKS = { ...CHECKS, [k]: v };
  try { store()?.setItem(KEY, JSON.stringify(CHECKS)); } catch { /* session only */ }
  listeners.forEach((f: () => void) => f());
};
function useChecks(): Record<string, boolean> {
  const [, force] = useState(0);
  useEffect(() => { const f = () => force((n: number) => n + 1); listeners.add(f); return () => { listeners.delete(f); }; }, []);
  return CHECKS;
}
const exportProgress = (): string => {
  const checks: Record<string, boolean> = {};
  Object.keys(CHECKS).sort().forEach((k: string) => { if (CHECKS[k]) checks[k] = true; });
  const d = new Date();
  const p2 = (n: number): string => String(n).padStart(2, "0");
  return JSON.stringify({ ...SAVED, updated: `${d.getFullYear()}-${p2(d.getMonth() + 1)}-${p2(d.getDate())}`, checks }, null, 2);
};
function CopyProgress() {
  useChecks();
  const [state, setState] = useState<"idle" | "copied" | "manual">("idle");
  const json = exportProgress();
  const copy = () => {
    const nav = (globalThis as any).navigator;
    try {
      if (nav?.clipboard?.writeText) { nav.clipboard.writeText(json).then(() => setState("copied"), () => setState("manual")); return; }
    } catch { /* blocked */ }
    setState("manual");
  };
  return (
    <div style={{ position: "relative" }}>
      <button onClick={copy} style={{ padding: "4px 10px", borderRadius: 6, border: `1px solid ${SV.gold}`, background: "transparent", color: state === "copied" ? SV.gold : SV.t1, fontSize: 12, fontWeight: 600, cursor: "pointer", fontFamily: "inherit" }}>
        {state === "copied" ? "Copied" : "Copy progress"}
      </button>
      {state === "manual" && (
        <div style={{ position: "absolute", right: 0, top: "calc(100% + 6px)", zIndex: 20, width: 360, padding: 8, borderRadius: 8, border: `1px solid ${SV.gold}`, background: "#1B1A17" }}>
          <textarea readOnly value={json} onFocus={(e: any) => e.target.select()} style={{ width: "100%", height: 180, background: "#121110", color: "#ECE8DF", border: "1px solid #3A3833", borderRadius: 6, fontFamily: "ui-monospace, monospace", fontSize: 11 }} />
          <button onClick={() => setState("idle")} style={{ marginTop: 6, padding: "2px 10px", borderRadius: 6, border: "1px solid #3A3833", background: "transparent", color: "#ECE8DF", fontSize: 12, cursor: "pointer" }}>Close</button>
        </div>
      )}
    </div>
  );
}

function ClassIcon({ c, size }: { c: any; size?: number }) {
  const [bad, setBad] = useState(false);
  const s = size ?? 24;
  if (bad) return <span style={{ width: s, height: s, borderRadius: 6, border: `1.5px solid ${c.color}`, color: c.color, display: "inline-grid", placeItems: "center", fontWeight: 700 }}>{c.class.charAt(0)}</span>;
  return <img src={c.icon} alt={c.class} width={s} height={s} onError={() => setBad(true)} style={{ width: s, height: s, borderRadius: 6, border: `1.5px solid ${c.color}`, boxShadow: "0 0 0 1px rgba(0,0,0,0.6)" }} />;
}

function Checklist({ items, color }: { items: Item[]; color: string }) {
  const t = useGrokTheme();
  const checks = useChecks();
  const done = items.filter((i: Item) => checks[i.id]).length;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <div style={{ flex: 1, height: 4, borderRadius: 2, background: SV.f2, overflow: "hidden" }}>
          <div style={{ width: `${items.length ? (done / items.length) * 100 : 0}%`, height: "100%", background: color }} />
        </div>
        <span style={{ fontSize: 12, color: SV.t2 }}>{`${done} / ${items.length}`}</span>
      </div>
      {items.map((it: Item, i: number) => {
        const on = !!checks[it.id];
        const toggle = () => setCheck(it.id, !on);
        return (
          <div key={it.id} role="checkbox" aria-checked={on} tabIndex={0} onClick={toggle}
            onKeyDown={(ev: KeyboardEvent) => { if (ev.key === " " || ev.key === "Enter") { ev.preventDefault(); toggle(); } }}
            style={{ display: "flex", gap: 10, padding: "7px 0", borderTop: i > 0 ? `1px solid ${t.border.subtle}` : "none", cursor: "pointer" }}>
            <span style={{ width: 18, height: 18, borderRadius: 5, border: `1.5px solid ${on ? color : SV.b1}`, background: on ? color : "transparent", color: "#111", fontSize: 12, fontWeight: 700, textAlign: "center", lineHeight: "15px", flex: "0 0 auto" }}>{on ? "✓" : ""}</span>
            <span style={{ flex: 1, color: on ? SV.t3 : SV.t1, textDecorationLine: on ? "line-through" : "none" }}>{L(it.text)}{it.detail ? <div style={{ fontSize: 12, color: SV.t3 }}>{L(it.detail)}</div> : null}</span>
            {it.tag ? <span style={{ fontSize: 11, color: SV.t2 }}>{it.tag}</span> : null}
          </div>
        );
      })}
    </div>
  );
}

function Head({ c, title }: { c: any; title: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "2px 0 8px 10px", borderLeft: `3px solid ${c.color}`, marginBottom: 6 }}>
      <ClassIcon c={c} size={28} />
      <span style={{ fontWeight: 700, color: c.color }}>{c.display}</span>
      <span style={{ fontWeight: 600, color: SV.t1 }}>{title}</span>
    </div>
  );
}

const level = (id: string): number => (SAVED.levels[id] && SAVED.levels[id].level) || 1;
const bracketOf = (lv: number): any => PLAN.brackets.find((b: any) => lv >= b.from && lv < b.to) ?? PLAN.brackets[PLAN.brackets.length - 1];

function Timeline({ selected, onSelect }: { selected: string; onSelect: (id: string) => void }) {
  const W = 1120; const left = 140; const right = 30; const top = 8; const bandH = 32; const rowH = 46;
  const x = (lv: number): number => left + ((lv - 1) / 59) * (W - left - right);
  const H = top + bandH + 16 + CHARS.length * rowH + 16;
  return (
    <svg width="100%" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Levels 1 to 60">
      {PLAN.brackets.map((b: any) => {
        const on = b.id === selected;
        const bw = x(b.to) - x(b.from) - 3;
        return (
          <g key={b.id} onClick={() => onSelect(b.id)} style={{ cursor: "pointer" }}>
            <rect x={x(b.from) + 1.5} y={top} width={bw} height={bandH} rx={6} fill={on ? SV.gold : SV.f2} stroke={on ? SV.gold : SV.b1} />
            <text x={(x(b.from) + x(b.to)) / 2} y={top + bandH / 2 + 5} textAnchor="middle" style={{ fontSize: 14, fontWeight: 600 }} fill={on ? "#1A1405" : SV.t1}>{`${b.from}–${b.to}`}</text>
          </g>
        );
      })}
      {CHARS.map((c: any, i: number) => {
        const y = top + bandH + 16 + i * rowH + rowH / 2;
        return (
          <g key={c.id}>
            <text x={8} y={y + 5} style={{ fontSize: 14, fontWeight: 700 }} fill={c.color}>{c.display}</text>
            <line x1={left} x2={W - right} y1={y} y2={y} stroke={SV.b1} />
            <rect x={left} y={y - 2} width={Math.max(0, x(level(c.id)) - left)} height={4} rx={2} fill={c.color} />
            {c.milestones.map((m: any, j: number) => (
              <g key={`${c.id}-${j}`}>
                <title>{`${m.name} · ${m.level}`}</title>
                <circle cx={x(m.level)} cy={y} r={6} fill={level(c.id) >= m.level ? c.color : SV.bg} stroke={c.color} strokeWidth={2} />
              </g>
            ))}
          </g>
        );
      })}
    </svg>
  );
}

type Tab = "today" | "levels" | "profs" | "legacy" | "reference";

export default function App() {
  const [tab, setTab] = useState<Tab>("today");
  const low = [...CHARS].sort((a: any, b: any) => level(a.id) - level(b.id))[0];
  const [char, setChar] = useState<string>(low.id);
  const [bid, setBid] = useState<string>(bracketOf(level(low.id)).id);
  const c = CHARS.find((x: any) => x.id === char) ?? CHARS[0];
  const b = PLAN.brackets.find((x: any) => x.id === bid) ?? PLAN.brackets[0];
  const cur = bracketOf(level(c.id));
  return (
    <Page title={PLAN.roster.name} summary={`${PLAN.roster.faction} · ${PLAN.roster.ruleset} · ${CHARS.length} characters`} width="wide">
      <Section>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12 }}>
          {CHARS.map((x: any) => (
            <button key={x.id} type="button" onClick={() => setChar(x.id)} aria-pressed={x.id === char}
              style={{ all: "unset", boxSizing: "border-box", cursor: "pointer", border: `${x.id === char ? 2 : 1}px solid ${x.id === char ? SV.gold : SV.b1}`, borderLeft: `4px solid ${x.color}`, borderRadius: 10, padding: 12, display: "flex", flexDirection: "column", gap: 8 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <ClassIcon c={x} size={26} />
                <span style={{ fontWeight: 700, color: x.color }}>{x.display}</span>
                <span style={{ fontSize: 12, color: SV.t2 }}>{`${x.race} ${x.class}`}</span>
                {x.id === low.id ? <span style={{ marginLeft: "auto", fontSize: 11, fontWeight: 700, color: "#111", background: SV.gold, borderRadius: 999, padding: "1px 7px" }}>Up next</span> : null}
              </div>
              <div style={{ fontSize: 12, color: SV.t2 }}>{`Level ${level(x.id)} · ${bracketOf(level(x.id)).from}–${bracketOf(level(x.id)).to}`}</div>
              <div style={{ height: 8, borderRadius: 4, background: SV.f2, overflow: "hidden" }}><div style={{ width: `${(level(x.id) / 60) * 100}%`, height: "100%", background: x.color }} /></div>
            </button>
          ))}
        </div>
      </Section>
      <Segmented<Tab> value={tab} onChange={setTab} options={[
        { value: "today", label: "Today" }, { value: "levels", label: "Levels" }, { value: "profs", label: "Professions" },
        { value: "legacy", label: "Legacy" }, { value: "reference", label: "Reference" }]} />
      {tab === "today" && (
        <Fragment>
          <Section heading="Status" actions={<CopyProgress />}>
            <Metrics metrics={[
              { value: low.display, label: "Up next", detail: `${low.class} · level ${level(low.id)}` },
              { value: `${bracketOf(level(low.id)).from}–${bracketOf(level(low.id)).to}`, label: "Current range" },
              { value: String(PLAN.coverage.legacy_from_plan), label: "Legacy points in the plan" },
              { value: PLAN.roster.launch, label: "Launch" },
            ]} />
          </Section>
          <Section><Head c={c} title={`Levels ${cur.from}–${cur.to}`} /><Checklist items={cur.tasks[c.id] ?? []} color={c.color} /></Section>
          <Section heading="Road to 60"><Timeline selected={bid} onSelect={(id: string) => { setBid(id); setTab("levels"); }} /></Section>
        </Fragment>
      )}
      {tab === "levels" && (
        <Fragment>
          <Segmented<string> value={bid} onChange={setBid} options={PLAN.brackets.map((x: any) => ({ value: x.id, label: `${x.from}–${x.to}` }))} />
          <Section heading={`Levels ${b.from}–${b.to}`}>
            <Table columns={["Character", "Target", "Zones", "Log out"]} rows={b.rotation.map((r: any) => {
              const who = CHARS.find((x: any) => x.id === r.char);
              return [<span key={r.char} style={{ color: who.color, fontWeight: 700 }}>{who.display}</span>, String(r.target), L(r.zones.join(", ")), L(r.logout)];
            })} />
          </Section>
          <Grid columns={2}>
            {CHARS.map((x: any) => (
              <Section key={x.id}><Head c={x} title={`${x.race} ${x.class}`} /><Checklist items={b.tasks[x.id] ?? []} color={x.color} /></Section>
            ))}
          </Grid>
        </Fragment>
      )}
      {tab === "profs" && (
        <Section heading="Craft coverage">
          <Table columns={["Craft", ...CHARS.map((x: any) => x.display)]} rows={Object.keys(PLAN.coverage.crafts).map((cr: string) => [
            L(cr), ...CHARS.map((x: any) => (PLAN.coverage.crafts[cr].includes(x.id) ? <span key={x.id} style={{ display: "inline-block", width: 12, height: 12, borderRadius: 6, background: x.color }} /> : "")),
          ])} />
        </Section>
      )}
      {tab === "legacy" && (
        <Fragment>
          <Section heading="Projection"><Table columns={["By the end of", "Points"]} rows={PLAN.coverage.projection.map((p: any) => [p.at.replace("-", "–"), String(p.points)])} /></Section>
          <Section heading="Account"><Checklist items={PLAN.account} color={SV.gold} /></Section>
        </Fragment>
      )}
      {tab === "reference" && (
        <Fragment>
          {PLAN.validation.warnings.length > 0 && <Section heading="Roster notes"><Table columns={["Note"]} rows={LT(PLAN.validation.warnings.map((w: string) => [w]))} /></Section>}
          <Section heading="Sources"><LinkCards links={Object.values(PLAN.sources).map((s: any) => ({ title: s.title, site: s.site, href: s.url }))} /></Section>
        </Fragment>
      )}
    </Page>
  );
}
