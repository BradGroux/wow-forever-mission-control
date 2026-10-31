# Changelog

All notable changes to WoW Forever Legacy Mission Control are recorded here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions are release dates, `YYYY.MM.DD`; a second release on the same day adds `.N` (for example `2026.11.04.1`). See [docs/releasing.md](docs/releasing.md).

## [Unreleased]

## [2026.10.31] - 2026-10-31

First public release, four days before World of Warcraft: Forever launches on November 4, 2026.

### Added

- **Config-driven roster.** One file, `config/roster.json`, describes 1 to 10 characters (four recommended) in one faction: names, races, classes, leveling and endgame specs, and professions with optional `from`/`until` levels for swaps. A JSON schema ([config/roster.schema.json](config/roster.schema.json)), two example rosters (Alliance and Horde) and a guided interview (`./mc init`) are included ([#42](https://github.com/BradGroux/wow-forever-mission-control/pull/42)).
- **Validator.** `./mc validate` checks legal race/class combinations (56 combos, 28 per faction), roster size, profession limits, craft coverage across all six crafting professions, and the roster's structure and field types, with field-specific messages instead of tracebacks.
- **Plan generator.** `./mc generate` writes a level-by-level plan for each character: nine brackets from 1 to 60 with zones, dungeons, class quests and spell milestones, profession targets (150 by 25, 225 by 32, 300 by 52, never before the craft is trained), the Cozy Sleeping Bag chain, a rested rotation, and a Legacy points projection. Output: `web/data/plan.js`, `build/PLAN.md`, `build/plan.json` and the Grok Bot canvas. `./mc plan` prints the Markdown plan ([docs/examples](docs/examples/alliance-plan.md)).
- **Legacy tracking.** All 65 Legacy points: class (27), craft (18), PvP (12), dungeons (3), raids (3) and adventure (2), with the reward track, perk trees, spend cap, exact Spelunker criteria and where to claim rewards ([#35](https://github.com/BradGroux/wow-forever-mission-control/pull/35), [#37](https://github.com/BradGroux/wow-forever-mission-control/pull/37)).
- **Standalone web page** (`web/`): Today, Brackets, Rested, Legacy, Professions, Dungeons + bag, Classes, World and Reference tabs; checklists; editable levels, rested state and profession skills saved in the browser; JSON export and import; LegacyTracker import; responsive down to phone width; no build step and no dependencies ([#31](https://github.com/BradGroux/wow-forever-mission-control/pull/31)). Every game name links to Wowhead's WoW Forever database. Data status shows as small tags (**Seen in beta**, **Classic data**, **Unverified**), including racial abilities and recorded costs ([#35](https://github.com/BradGroux/wow-forever-mission-control/pull/35), [#71](https://github.com/BradGroux/wow-forever-mission-control/pull/71)). The footer shows the release version.
- **LegacyTracker addon** (`addon/LegacyTracker`, Interface 16001): silent; records level, XP, rested XP, zone and profession skill for every character on the account; gold and play time only after `/ltrack extras on` ([#32](https://github.com/BradGroux/wow-forever-mission-control/pull/32)). Ships with a Lua test harness.
- **`mc` CLI** (Python 3.9+, standard library only; `make` targets for each command): `init`, `validate`, `generate`, `plan`, `level`, `skill`, `check`, `ids`, `map`, `progress show|merge|reset`, `import-addon` (with `--db` for renamed copies, [#11](https://github.com/BradGroux/wow-forever-mission-control/pull/11)), `scrub-addon`, `serve`, `leakcheck`, `doctor` and `version`.
- **Progress protocol.** Progress lives in the browser or `progress/progress.json` and moves as JSON. Page and CLI edits are time-stamped so corrections survive reloads and stale exports; addon data that isn't newer is skipped; imports are validated before anything is saved; merges and resets have dry runs, safety checks and backups ([#33](https://github.com/BradGroux/wow-forever-mission-control/pull/33), [#48](https://github.com/BradGroux/wow-forever-mission-control/pull/48), [#60](https://github.com/BradGroux/wow-forever-mission-control/pull/60), [#70](https://github.com/BradGroux/wow-forever-mission-control/pull/70)). See [docs/progress.md](docs/progress.md).
- **Data coverage** (`data/`, every record with a source and a status): 9 classes with 43 class milestones plus Riding, Dual Specialization and Journeyman Riding; 10 races including High Order and Windshaper Skyborne and the Skyborne start on Zephras Isle; 41 leveling zones, 29 dungeons, 13 boat, zeppelin, tram and skyship routes, and 54 flight paths; professions; Legacy challenges and rewards; 29 cited sources; verified Wowhead ids ([#43](https://github.com/BradGroux/wow-forever-mission-control/pull/43), [#46](https://github.com/BradGroux/wow-forever-mission-control/pull/46)). See [docs/data.md](docs/data.md).
- **Hosting docs** ([docs/hosting.md](docs/hosting.md)): local, GitHub Pages (a Pages workflow is included and deploys the demo), Cloudflare Pages (Git-connected or Wrangler direct upload), ChatGPT Sites ([#12](https://github.com/BradGroux/wow-forever-mission-control/pull/12)). **Grok Bot**: an optional live canvas Page built from the same plan ([adapters/grokbot](adapters/grokbot/README.md)), with Copy progress that round-trips into the web page.
- **Agent-agnostic instructions.** [AGENTS.md](AGENTS.md) is the single source of instructions for any agent; `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md` and `.cursor/rules/` point to it; per-platform tips in [docs/agents](docs/agents/README.md).
- **Upstream sync.** The [Sync from upstream](.github/workflows/sync-upstream.yml) workflow opens a weekly pull request in your copy without touching your roster or progress ([#18](https://github.com/BradGroux/wow-forever-mission-control/pull/18)); `make sync` does the same by hand. See [docs/updating.md](docs/updating.md).
- **Contributing setup.** [CONTRIBUTING.md](CONTRIBUTING.md), [Code of Conduct](CODE_OF_CONDUCT.md), issue and pull request templates, data sourcing rules, `./mc leakcheck` to keep personal files out of upstream pull requests, `tools/wowhead_lookup.py` for verified ids, and a personal README tip ([#14](https://github.com/BradGroux/wow-forever-mission-control/pull/14)).
- **CI**: validator, doctor, unit tests and generated-file checks; Python 3.9 and 3.12 on Linux and Windows; web syntax, page import and canvas export tests; luac and luacheck for the addon ([#13](https://github.com/BradGroux/wow-forever-mission-control/pull/13), [#36](https://github.com/BradGroux/wow-forever-mission-control/pull/36)).
- **Releases.** `VERSION`, this changelog, the addon's `## Version` and the page footer carry the release version; `./mc version --check` (run by `./mc doctor` in CI) keeps them in step; `tools/package_release.py` builds the release zips; [docs/releasing.md](docs/releasing.md) documents the process.

### Fixed

Found in review and audits before release. Each links its issue and the pull request that fixed it.

- [#9](https://github.com/BradGroux/wow-forever-mission-control/issues/9) Rosters of 1 to 10 characters (four stays the default) ([#42](https://github.com/BradGroux/wow-forever-mission-control/pull/42)).
- [#10](https://github.com/BradGroux/wow-forever-mission-control/issues/10) README screenshots and diagrams ([#31](https://github.com/BradGroux/wow-forever-mission-control/pull/31)).
- [#15](https://github.com/BradGroux/wow-forever-mission-control/issues/15) Generated `plan.js` and the canvas allowed script breakout through roster names, display names or notes; generated JSON is now script-safe ([#32](https://github.com/BradGroux/wow-forever-mission-control/pull/32)).
- [#16](https://github.com/BradGroux/wow-forever-mission-control/issues/16) Page edits to baked progress (unticks, lowered levels) reverted on reload; page edits are now time-stamped and stick ([#33](https://github.com/BradGroux/wow-forever-mission-control/pull/33)).
- [#17](https://github.com/BradGroux/wow-forever-mission-control/issues/17) Page addon import lacked renamed SavedVariables support and the CLI's stale-import guard ([#33](https://github.com/BradGroux/wow-forever-mission-control/pull/33)).
- [#19](https://github.com/BradGroux/wow-forever-mission-control/issues/19) Progress merge and page export dropped character name mappings (`map`) ([#33](https://github.com/BradGroux/wow-forever-mission-control/pull/33)).
- [#20](https://github.com/BradGroux/wow-forever-mission-control/issues/20) Validation gaps: schema not enforced, `until` above 60 accepted, skills unchecked, unknown checklist ids accepted, `init` could write invalid rosters ([#34](https://github.com/BradGroux/wow-forever-mission-control/pull/34)).
- [#21](https://github.com/BradGroux/wow-forever-mission-control/issues/21) A profession trained at 60 had no Train task, and craft targets ignored the drop level (`until`) ([#34](https://github.com/BradGroux/wow-forever-mission-control/pull/34)).
- [#22](https://github.com/BradGroux/wow-forever-mission-control/issues/22) PvP Legacy points untracked, mismatched earned vs. plan denominators, claim location not shown ([#35](https://github.com/BradGroux/wow-forever-mission-control/pull/35)).
- [#23](https://github.com/BradGroux/wow-forever-mission-control/issues/23) Zone and dungeon notes not rendered; flight paths showed no status ([#35](https://github.com/BradGroux/wow-forever-mission-control/pull/35)).
- [#24](https://github.com/BradGroux/wow-forever-mission-control/issues/24) Sharing the addon file exposed gold and play time for every character; both are now opt-in and `./mc scrub-addon` writes a roster-only share ([#32](https://github.com/BradGroux/wow-forever-mission-control/pull/32)).
- [#25](https://github.com/BradGroux/wow-forever-mission-control/issues/25) CI now covers Python 3.9 and 3.12 on Linux and Windows and runs luacheck on the addon ([#36](https://github.com/BradGroux/wow-forever-mission-control/pull/36)).
- [#26](https://github.com/BradGroux/wow-forever-mission-control/issues/26) Spelunker starter-dungeon rule was hardcoded by name; it now comes from `data/world.json` ([#34](https://github.com/BradGroux/wow-forever-mission-control/pull/34)).
- [#28](https://github.com/BradGroux/wow-forever-mission-control/issues/28) `progress merge` gained `--dry-run` and an untick safety check; `progress reset` needs `--force`; both write a backup first ([#33](https://github.com/BradGroux/wow-forever-mission-control/pull/33)).
- [#29](https://github.com/BradGroux/wow-forever-mission-control/issues/29) Spelunker tiers record the exact dungeon criteria (Scarlet Monastery, Stratholme and Dire Maul wings count separately) ([#37](https://github.com/BradGroux/wow-forever-mission-control/pull/37)).
- [#30](https://github.com/BradGroux/wow-forever-mission-control/issues/30) Export progress no longer overwrites the clipboard; it downloads the file ([#32](https://github.com/BradGroux/wow-forever-mission-control/pull/32)).
- [#38](https://github.com/BradGroux/wow-forever-mission-control/issues/38) `./mc init` crashed on a faction other than exactly Alliance/Horde ([#47](https://github.com/BradGroux/wow-forever-mission-control/pull/47)).
- [#39](https://github.com/BradGroux/wow-forever-mission-control/issues/39) Spelunker criteria used dungeon names that did not match `world.json` ([#47](https://github.com/BradGroux/wow-forever-mission-control/pull/47)).
- [#40](https://github.com/BradGroux/wow-forever-mission-control/issues/40) Roster card showed not-yet-trained professions and hid current ones when a profession has an `until` ([#47](https://github.com/BradGroux/wow-forever-mission-control/pull/47)).
- [#41](https://github.com/BradGroux/wow-forever-mission-control/issues/41) Stale exports merged over stamped page edits brought old values back ([#48](https://github.com/BradGroux/wow-forever-mission-control/pull/48)).
- [#49](https://github.com/BradGroux/wow-forever-mission-control/issues/49) Craft targets and Legacy projections could come before the profession's training level ([#58](https://github.com/BradGroux/wow-forever-mission-control/pull/58)).
- [#50](https://github.com/BradGroux/wow-forever-mission-control/issues/50) CLI `level`, `skill` and `check` edits did not stamp, so an older browser copy could undo them ([#60](https://github.com/BradGroux/wow-forever-mission-control/pull/60)).
- [#51](https://github.com/BradGroux/wow-forever-mission-control/issues/51) Realm-qualified addon mappings lost to bare-name matching; same-name characters on two realms are now reported as ambiguous ([#59](https://github.com/BradGroux/wow-forever-mission-control/pull/59)).
- [#52](https://github.com/BradGroux/wow-forever-mission-control/issues/52) `scrub-addon` ignored saved name mappings ([#59](https://github.com/BradGroux/wow-forever-mission-control/pull/59)).
- [#53](https://github.com/BradGroux/wow-forever-mission-control/issues/53) Invalid roster structures crashed before validation could report errors ([#58](https://github.com/BradGroux/wow-forever-mission-control/pull/58)).
- [#54](https://github.com/BradGroux/wow-forever-mission-control/issues/54) Progress JSON was saved without validation and could break the page on every reload ([#60](https://github.com/BradGroux/wow-forever-mission-control/pull/60)).
- [#55](https://github.com/BradGroux/wow-forever-mission-control/issues/55) CLI `progress merge` let stale addon data overwrite newer data ([#60](https://github.com/BradGroux/wow-forever-mission-control/pull/60)).
- [#56](https://github.com/BradGroux/wow-forever-mission-control/issues/56) Canvas Copy progress dropped unticks, so importing it into the page kept completed checks ([#60](https://github.com/BradGroux/wow-forever-mission-control/pull/60)).
- [#57](https://github.com/BradGroux/wow-forever-mission-control/issues/57) Config reference still said exactly four characters ([#58](https://github.com/BradGroux/wow-forever-mission-control/pull/58)).
- [#61](https://github.com/BradGroux/wow-forever-mission-control/issues/61) Addon import accepted out-of-range levels and skills; `generate` baked them and `doctor` reported ok ([#70](https://github.com/BradGroux/wow-forever-mission-control/pull/70)).
- [#62](https://github.com/BradGroux/wow-forever-mission-control/issues/62) A newer addon snapshot could never update a manually edited profession skill ([#70](https://github.com/BradGroux/wow-forever-mission-control/pull/70)).
- [#63](https://github.com/BradGroux/wow-forever-mission-control/issues/63) Wrong-type roster fields (numbers, null, arrays) still crashed validation ([#69](https://github.com/BradGroux/wow-forever-mission-control/pull/69)).
- [#64](https://github.com/BradGroux/wow-forever-mission-control/issues/64) Craft projection counted a boundary-level target one bracket early ([#69](https://github.com/BradGroux/wow-forever-mission-control/pull/69)).
- [#65](https://github.com/BradGroux/wow-forever-mission-control/issues/65) Progress validation accepted infinite numbers and could write non-JSON progress ([#70](https://github.com/BradGroux/wow-forever-mission-control/pull/70)).
- [#66](https://github.com/BradGroux/wow-forever-mission-control/issues/66) Unverified racial abilities lost their status in generated plans ([#71](https://github.com/BradGroux/wow-forever-mission-control/pull/71)).
- [#67](https://github.com/BradGroux/wow-forever-mission-control/issues/67) Recorded milestone costs and trainer notes were missing from the plan ([#71](https://github.com/BradGroux/wow-forever-mission-control/pull/71)).
- [#68](https://github.com/BradGroux/wow-forever-mission-control/issues/68) Markdown Legacy breakdown assumed three points for crafts dropped before their targets ([#69](https://github.com/BradGroux/wow-forever-mission-control/pull/69)).

### Security

- Generated `plan.js` and canvas JSON escape `<`, `>`, `&` and line separators so roster text can't break out of the script block ([#15](https://github.com/BradGroux/wow-forever-mission-control/issues/15)).
- The addon records gold and play time only on request, and `./mc scrub-addon` shares only roster characters' level, rested state, zone and skills ([#24](https://github.com/BradGroux/wow-forever-mission-control/issues/24)).

### Known limitations

- Game data is pre-launch. Racial abilities are **Unverified**; six class milestones, all flight paths and most boats, zeppelins and the tram are **Classic data**; riding prices and many levels are **Seen in beta**. Dual Specialization's cost is not recorded yet. These are tagged on the page and tracked in the issues below.
- About 70 names on the example rosters have no verified Wowhead id yet and link to a Wowhead search.
- The addon declares Interface 16001; if the launch client uses a different number, the `.toc` needs an update ([#2](https://github.com/BradGroux/wow-forever-mission-control/issues/2)).
- There is no official Forever API or Armory yet, so levels come from the page, the CLI or the addon ([#2](https://github.com/BradGroux/wow-forever-mission-control/issues/2)).
- Progress is per browser unless you keep `progress/progress.json` in your copy or share exports.
- The ChatGPT Sites hosting steps follow OpenAI's documentation and have not been tested end to end with this project.

### Open launch-day issues

- [#1](https://github.com/BradGroux/wow-forever-mission-control/issues/1) Verify Horde data (class quests, hubs, zones, flight paths)
- [#2](https://github.com/BradGroux/wow-forever-mission-control/issues/2) Launch day: check for a Forever API or Armory, Interface version, Legacy changes
- [#3](https://github.com/BradGroux/wow-forever-mission-control/issues/3) Add verified Wowhead ids for names that use search links
- [#4](https://github.com/BradGroux/wow-forever-mission-control/issues/4) Confirm class milestones tagged Classic data
- [#5](https://github.com/BradGroux/wow-forever-mission-control/issues/5) Confirm boats, zeppelins, tram and flight paths
- [#6](https://github.com/BradGroux/wow-forever-mission-control/issues/6) Verify racials at launch
- [#7](https://github.com/BradGroux/wow-forever-mission-control/issues/7) Skyborne starting experience and class quests
- [#8](https://github.com/BradGroux/wow-forever-mission-control/issues/8) Confirm Riding and Dual Specialization level and cost

### Upgrade and sync

- **New copy:** use **Use this template** (or fork), then `./mc init`, `./mc validate` and `./mc generate`. See the [README](README.md#quick-start).
- **Existing copy:** merge the Sync from upstream pull request, or run `make sync` (equivalently `git fetch upstream && git merge upstream/main`), then `./mc generate`, `./mc validate` and `./mc doctor`, and commit. Your roster and progress files are never touched; checklist ids are stable, so ticks survive. See [docs/updating.md](docs/updating.md).
- **Addon:** replace `Interface/AddOns/LegacyTracker` with the folder from `LegacyTracker-2026.10.31.zip`. Saved data is kept.
- **Hosted page:** redeploy after `./mc generate`. To host without the repo, unzip `mission-control-web-2026.10.31.zip` and add your own `data/plan.js`.
- Progress files from earlier development builds keep working. `./mc generate` now refuses invalid values (for example a level above 60) and names the field: fix it with `./mc level` or `./mc skill`, or restore a copy from `progress/backups/`.

[Unreleased]: https://github.com/BradGroux/wow-forever-mission-control/compare/2026.10.31...HEAD
[2026.10.31]: https://github.com/BradGroux/wow-forever-mission-control/releases/tag/2026.10.31
