# Game data

Everything Mission Control knows about WoW Forever is in `data/`. Each record cites a source id from [data/sources.json](../data/sources.json) and carries a status.

| File | Contents |
| --- | --- |
| `classes.json` | 9 classes: color, icon, specs and roles, recommended leveling spec and tier, endgame specs, milestones by level (class quests, key spells, pets, forms, mounts) |
| `races.json` | 10 races: faction, allowed classes (56 combos, 28 per faction), start zone and area, first hub, capital, racials |
| `world.json` | factions (capitals, supply faction, starter dungeon), 41 leveling zones with level ranges and quest counts, 29 dungeons with levels, location, access and Spelunker tier, boats, zeppelins and trams, flight paths, rulesets |
| `professions.json` | gathering, crafting and secondary professions, two-primary limit, skill cap, Legacy thresholds |
| `legacy.json` | Legacy challenges (class 27, craft 18, PvP 12, dungeons 3, raids 3, adventure 2), reward track, perk trees, spend cap, where to claim; Spelunker criteria per tier (every listed dungeon is required; Scarlet Monastery, Stratholme and Dire Maul wings count separately) |
| `chains.json` | quest chains (the Cozy Sleeping Bag) |
| `wowhead.json` | verified Wowhead ids for names used on the page |
| `sources.json` | every source: title, site, URL |

## Status values

| Status | Meaning | On the page |
| --- | --- | --- |
| `blizzard` | Confirmed by Blizzard (news post, patch notes, in-game) | no tag |
| `beta` | Seen on the Forever beta, may change at launch | no tag |
| `classic` | Carried over from Classic Era data, not yet confirmed for Forever | **Classic data** |
| `unverified` | Reported by one community source, or inferred | **Unverified** |

## Wowhead links

Names with an entry in `wowhead.json` link straight to the Wowhead Forever page (`https://www.wowhead.com/forever/<type>=<id>`). Anything else links to a Wowhead search, shown with a dotted underline. Maintainers can look up and verify missing ids with:

```sh
python3 tools/wowhead_lookup.py --missing          # report
python3 tools/wowhead_lookup.py --missing --write  # add verified ids
```

The tool accepts only exact name matches confirmed by Wowhead's tooltip service.

## Known gaps

Open questions are tracked as [issues labeled `data`](https://github.com/BradGroux/wow-forever-mission-control/labels/data). At the time of writing:

- Racials changed during the beta; all are `unverified` until launch.
- Riding and Dual Specialization at level 40 (and their cost) are `unverified`.
- Many class milestones and all flight paths are `classic` data.
- The Menethil Harbor to Southshore boat and the Skyborne skyship routes are `unverified`.
- Five of the nine new dungeons were not playable in the beta; their levels come from Blizzard's announcement only.
- Ragefire Chasm levels come from community data.
- Around 75 names have no verified Wowhead id yet and use search links.

See [CONTRIBUTING.md](../CONTRIBUTING.md#data-sourcing-rules) to fix any of these.
