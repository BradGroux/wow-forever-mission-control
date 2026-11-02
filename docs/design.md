# Design standards

These rules apply to everything a player sees: the standalone page (`web/`), the Grok Bot Page (`adapters/grokbot/template.canvas.tsx`) and the Markdown plan (`./mc plan`). They are must-follow for people and agents alike. When the code and this file disagree, fix one of them in the same pull request.

Values below are taken from [`web/style.css`](../web/style.css), [`web/app.js`](../web/app.js), [`adapters/grokbot/template.canvas.tsx`](../adapters/grokbot/template.canvas.tsx), [`data/classes.json`](../data/classes.json) and [`scripts/mc.py`](../scripts/mc.py).

## Content rules

1. **No how-to or instruction text in the page body.** No "Click a card to…", "Tick items as you go", "Import your file here". Controls explain themselves through their labels. How-to belongs in `docs/`, the README and dialogs that the player opened on purpose (Import).
2. **No "Showing…" captions.** No "Showing levels 20–30 for Aldric". The selected tab, segment or card already says that.
3. **No invented shorthand or codes.** Brackets are level ranges written with an en dash: `1–12`, `20–30`, never `B1`, `Br3` or `L20-30`. Projections read "By the end of 20–30". Spell out game names (Legacy, Spelunker, Cozy Sleeping Bag). The one exception is the Road to 60 timeline, where dungeon dots may use the community's standard names (`RFC`, `SFK`, `BRD`, from the `SHORT` table in `web/app.js`) because space is tight; the full name is always in the dot's `<title>` tooltip and everywhere else on the page.
4. **No redundant state words.** No "Selected", "Active", "Current tab", "(checked)". State is shown visually: a gold border on the chosen card and a gold fill on the chosen bracket band, an underline on the chosen tab, a filled segment, a filled checkbox with strikethrough.
5. **No caveat or disclaimer sentences in the body.** No "This may change at launch" or "Data is unconfirmed". Data status goes in a small tag next to the thing it describes (see [Status tags](#status-tags)). Uncertain items are collected in the Reference tab's **Open questions** table.
6. **Every game name links to Wowhead's WoW Forever database.** Quests, NPCs, zones, items, dungeons, spells, factions, races and professions. See [Wowhead links](#wowhead-links).
7. **Class icons and class colors wherever a character or class appears.** Roster cards, panel heads, level rows, timeline rows, table cells naming a character, coverage dots and checklists. See [Classes](#class-colors-and-icons).
8. **Readable, fixed colors.** A dark theme with fixed hex values that keep text contrast high on every host. Don't depend on the host's light or dark mode, and don't add colors outside the palette below.
9. **The standalone page and the Grok Bot Page look the same.** Same roster cards, same tabs order where both have them, same timeline, same tags and labels. A visual change in one lands in the other in the same pull request.

## Palette

The standalone page uses CSS custom properties on `:root` (`color-scheme: dark`):

| Token | Hex | Use |
|---|---|---|
| `--bg` | `#070707` | Page ground |
| `--f1` | `#111111` | Cards, panels, metrics, table headers, segmented track |
| `--f2` | `#1A1A1A` | Hover fill, inputs, buttons |
| `--f3` | `#242424` | Progress bar tracks, chosen segment, button hover |
| `--b0` | `#232323` | Row dividers, footer rule |
| `--b1` | `#2F2F2F` | Card and panel borders, tab rule |
| `--b2` | `#444444` | Checkbox outline, dialog border, step numbers |
| `--t1` | `#FCFCFC` | Primary text |
| `--t2` | `#BEBEBE` | Secondary text |
| `--t3` | `#8E8E8E` | Muted text, inactive tabs, labels |
| `--gold` | `#C9A227` | Legacy and account accents |
| `--ok` | `#3FB950` | "New" tag |
| `--warn` | `#D29922` | "Unverified", "Classic data", "Not in beta" tags |
| `--link` | `#7AB7FF` | Links, focus ring |

Radii: `--r` 10px (cards, panels, tables, dialogs), `--r-sm` 6px (inputs, buttons, checklist rows), 999px for pills. Fonts: `--font` (system UI stack) at 15px/1.5, `--mono` for JSON. Numbers in tables and inputs use `font-variant-numeric: tabular-nums`.

SVG charts (timeline, reward track) can't read CSS variables reliably on every host, so they use the fixed constants `C` in `web/app.js`: `t1 #ECECEC`, `t2 #BEBEBE`, `t3 #9C9C9C`, `f2 #2B2B2B`, `b1 #4A4A4A`, `b0 #353535`, `bg #070707`, `gold #C9A227`.

The Grok Bot Page uses the same constants (`SV` in the canvas template, with `bg #141414` to sit on the canvas ground) plus `useGrokTheme()` for subtle dividers.

## Chosen items

One rule on both pages: **the chosen item is marked in gold (`#C9A227`)**.

- **Roster card:** every card has a 4px left edge in its class color. The chosen card's other three sides become a 2px gold border; the class-colored left edge stays. On the page, padding drops by 1px on the thicker sides so the content doesn't move.
- **Road to 60 bracket band:** the chosen band is filled and stroked gold with dark text (`#1A1405`); other bands are `f2` with a `b1` stroke and `t1` text.
- Tabs and segmented controls keep their own neutral style (underline, filled segment) on each host.

## Class colors and icons

Colors and icons come from `data/classes.json`; never hard-code them in the page. Colors are Blizzard's official class colors:

| Class | Hex |
|---|---|
| Warrior | `#C69B6D` |
| Paladin | `#F48CBA` |
| Hunter | `#AAD372` |
| Rogue | `#FFF468` |
| Priest | `#FFFFFF` |
| Shaman | `#0070DD` |
| Mage | `#3FC7EB` |
| Warlock | `#8788EE` |
| Druid | `#FF7C0A` |

Icons are Wowhead's class icons, `https://wow.zamimg.com/images/wow/icons/medium/classicon_<class>.jpg`, drawn with a 6px radius and a 1–1.5px border in the class color. If an icon fails to load, both pages swap in the class initial in the class color in the same box, so the layout never shifts.

How the class color is used:

- Character names are bold in the class color (`.nm`, `--cc`).
- Roster cards: class-colored name, progress bar and "Up next" pill (18% class-color tint); every card has a 4px class-colored left edge (see [Chosen items](#chosen-items) for the chosen card).
- Checklists tick to a class-colored box; account-wide lists use gold.
- Coverage tables mark a character with a class-colored dot.
- Timeline rows: class-colored progress line and milestone dots; rows for characters not chosen are dimmed to 55%.

## Wowhead links

- Link targets come from `data/wowhead.json`: `name -> { id, type }`. `./mc generate` turns each into `https://www.wowhead.com/forever/<type>=<id>` and writes them to `plan.links`. Every id must be checked with `tools/wowhead_lookup.py` (the tooltip has to return the same name).
- A name without an id still links, to `https://www.wowhead.com/forever/search?q=<name>`. Search links are shown with a dotted underline (`a.search` on the page, `textDecorationStyle: dotted` on the Grok Bot Page) so a missing id is visible. Add the id rather than leaving a search link.
- Links open in a new tab with `rel="noopener noreferrer"` and must not toggle a checklist row when clicked.
- Free text is linked automatically by `L()` (longest name first, whole words only). Put game names in data exactly as the game spells them so they match.
- Link styling: `--link` blue on the page; gold underline that brightens on hover on the Grok Bot Page.

## Status tags

Status is a property of the data record (`status` in `data/*.json`) and shows as a small pill, never a sentence:

| Status | Label | Style |
|---|---|---|
| `beta` | Seen in beta | neutral pill |
| `classic` | Classic data | warn pill, tooltip "Classic data, unconfirmed for Forever" |
| `unverified` | Unverified | warn pill |
| confirmed / Blizzard source | (no tag) | — |

Other tags: **New** (green, `.pill.new`) for content new in Forever, **Not in beta** (warn), **Enemy territory** (neutral). Pills are 12px, 18px line height, 0 8px padding, 999px radius, 1px border. On the Grok Bot Page the status is appended to the item's tag as `tag · Seen in beta`. Every record with `classic` or `unverified` also appears in Reference → Open questions on both pages.

## Layout

- **Centered body.** Everything sits in `.wrap`: `max-width: 1280px; margin: 0 auto; padding: 32px 32px 48px`. The Grok Bot Page uses `<Page width="wide">`.
- **Spacing scale:** 4 / 8 / 12 / 16 / 24 / 32 / 48 px only. Sections are 32px apart, items inside a section 16px, cards in a grid 12px. Panels pad 16px 20px 20px; roster cards and metrics 14px 16px; table cells 10px 14px.
- **Header:** roster name (28px, 600), a sub-line `Faction · Ruleset · N characters`, then the roster cards in an auto-fit grid (min 240px).
- **Tabs (standalone page),** in this order: Today, Brackets, Rested, Legacy, Professions, Dungeons + bag, Classes, World, Reference. The chosen tab has `--t1` text and a 2px `--t1` underline; others are `--t3`. The tab is kept in the URL hash. **Grok Bot Page** uses a segmented control with Today, Levels, Professions, Legacy, Reference; brackets inside Levels are a second segmented control labeled with level ranges.
- **Today** shows the status metrics, the next character's checklist for their current range and the **Road to 60** timeline. Clicking a bracket band on the timeline opens that range on Brackets (Levels on the Grok Bot Page).
- **Road to 60 timeline:** SVG, viewBox 1120 wide, levels 1–60 on the x axis, bracket bands across the top labeled `from–to`, one row per character plus Dungeons and Legacy rows on the page, axis ticks at 1, 10, 20 … 60. It sits in `.hscroll` with a 860px minimum width so it scrolls rather than shrinks on phones.
- **Mobile:** below 900px two- and three-column grids stack and level rows become one column; below 600px the wrap pads 20px 16px 32px, the title drops to 22px, roster cards and metrics go two across, tabs scroll edge to edge, and table cells pad 8px 10px. The page must work at 360px wide with no horizontal page scroll (tables and the timeline scroll inside their own boxes).
- **Accessibility:** checklist rows are `role="checkbox"` with `aria-checked` and toggle on Space and Enter; tabs use `role="tab"` with `aria-selected`; segmented buttons use `aria-pressed`; every SVG has `role="img"` and an `aria-label`; `:focus-visible` shows a 2px `--link` outline.
- **Footer:** `Progress saved <date> · WoW Forever Legacy Mission Control · <release>`, 13px `--t3`, 48px above.

## Pull request checklist

- [ ] No instructions, "Showing…" captions, state words like "Selected", or caveat sentences in the page body
- [ ] Brackets and ranges are level ranges with an en dash (`20–30`), no codes
- [ ] Every new game name is in `data/wowhead.json` with a verified id (or shows the dotted search link on purpose)
- [ ] Characters and classes use the icon and class color from `data/classes.json`
- [ ] Colors come from the palette tokens above; no new hex values; chosen cards and bracket bands are gold
- [ ] Data status is a tag (Seen in beta, Classic data, Unverified), not a sentence
- [ ] Spacing uses the 4 / 8 / 12 / 16 / 24 / 32 / 48 scale; body stays centered in `.wrap`
- [ ] Checked at desktop width and at 360px
- [ ] The standalone page and the Grok Bot Page still match; screenshots in `docs/images/` refreshed if the look changed
