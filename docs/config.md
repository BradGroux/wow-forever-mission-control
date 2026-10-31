# Config reference

Your roster lives in `config/roster.json`. The JSON Schema is [config/roster.schema.json](../config/roster.schema.json); editors like VS Code use it for autocomplete when the file starts with `"$schema": "./roster.schema.json"`. If `config/roster.json` doesn't exist, every command uses `config/examples/alliance.json`.

## Top level

`characters` holds 1 to 10 entries. Four is the default and the recommended goal.

| Field | Required | Values | Notes |
| --- | --- | --- | --- |
| `roster_name` | no | text | Page title |
| `faction` | yes | `Alliance`, `Horde` | All characters must match |
| `ruleset` | yes | `Normal`, `PvP`, `Roleplay`, `Hardcore` | Hardcore characters still earn Legacy points |
| `launch` | no | date | Default `2026-11-04` |
| `characters` | yes | 1 to 10 (4 recommended) | See below |

## Characters

| Field | Required | Values | Notes |
| --- | --- | --- | --- |
| `id` | no | `a-z`, `0-9`, `-`, up to 24 | Key for saved progress. Defaults to the name in lowercase. **Never change it once you have progress.** |
| `name` | yes | 2 to 12 letters | The in-game name, used to match addon data |
| `display` | no | text | Longer label on the page |
| `race` | yes | Alliance: `Human`, `Dwarf`, `Night Elf`, `Gnome`, `High Order Skyborne`. Horde: `Orc`, `Undead`, `Tauren`, `Troll`, `Windshaper Skyborne` | Skyborne needs the Heroic Pack |
| `class` | yes | `Warrior`, `Paladin`, `Hunter`, `Rogue`, `Priest`, `Shaman`, `Mage`, `Warlock`, `Druid` | Must be allowed for the race (`./mc validate` checks) |
| `leveling_spec` | no | a spec of the class | Defaults to the class's recommended leveling spec |
| `endgame_spec` | no | a spec of the class | |
| `role` | no | text | e.g. Tank, Healer, Damage |
| `notes` | no | text | |
| `professions` | no | list | See below |

All 56 race and class combinations are in [data/races.json](../data/races.json): 28 per faction, and every class is available to both factions.

## Professions

Each entry is `{"name": ..., "from": 1, "until": 60}`.

- `name`: a primary profession: `Alchemy`, `Blacksmithing`, `Enchanting`, `Engineering`, `Leatherworking`, `Tailoring` (crafting) or `Herbalism`, `Mining`, `Skinning` (gathering).
- `from`: the level you train it (default 1).
- `until`: the level you drop it, 2-60 and after `from` (omit to keep it).

A character can hold two primary professions at any level, so you can swap: `Mining 1-60` then `Engineering` from 60. Cooking, First Aid and Fishing are secondary and not tracked.

**Legacy goal:** each crafting profession earns Legacy points at 150, 225 and 300 skill (18 points for all six). Four characters with two primaries each can cover all six crafts if two of them pick two crafts, or if someone swaps a gatherer for a craft late. `./mc validate` warns about any craft nobody takes.

Mission Control schedules craft targets of 150 by level 25, 225 by 32 and 300 by 52. A craft you start at 52 or later gets all three targets at its start level. A craft you drop (`until`) before a target's level doesn't get that target, the plan doesn't count its point, and `./mc validate` warns.

`./mc validate` also checks the file against [config/roster.schema.json](../config/roster.schema.json): an unknown or misspelled field is an error, so a typo like `leveling_spac` can't be silently ignored. `./mc init` writes `config/roster.draft.json` instead of `config/roster.json` when the answers don't validate.

## Example

See [config/examples/alliance.json](../config/examples/alliance.json) and [config/examples/horde.json](../config/examples/horde.json). Both cover all six crafts.
