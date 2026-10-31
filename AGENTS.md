# AGENTS.md

Instructions for any AI agent working in this repository (Grok Bot, Muse, ChatGPT/Codex, Claude, Cursor, Copilot, Gemini, and others). This file is canonical: `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md` and `.cursor/rules/` only point here.

## What this is

WoW Forever Legacy Mission Control plans and tracks a roster of characters (1 to 10; four recommended) leveling together in World of Warcraft: Forever (launch 2026-11-04) to earn the most Legacy points. One config (`config/roster.json`) drives everything. All work goes through one CLI, `./mc` (Python 3.9+, standard library only; on Windows use `python mc ...`). Never hand-edit generated files.

## Two kinds of repository

Check which one you are in before changing anything:

```sh
git remote -v
```

- **Upstream** (`BradGroux/wow-forever-mission-control`): the shared template. It contains no personal data. Changes here are data fixes, features and docs, made through pull requests.
- **A personal copy** (template copy or fork): it may contain the owner's `config/roster.json`, `progress/progress.json`, `web/data/plan.js` and `adapters/grokbot/mission-control.canvas.tsx`. These are personal files.

## Workflows

| Task | Command |
| --- | --- |
| Setup interview | `./mc init` (interactive), or write answers to a JSON file and run `./mc init --answers answers.json` |
| Validate | `./mc validate` (add `--strict` to fail on warnings) |
| Generate outputs | `./mc generate` |
| Read the plan | `./mc plan` |
| Record a level | `./mc level <char> <level> [--rested Empty\|Partial\|Full]` |
| Record a profession skill | `./mc skill <char> <profession> <skill>` |
| Find checklist ids | `./mc ids [text] [--open]` |
| Tick or untick items | `./mc check <id> [<id> ...] [--off]` |
| Merge a page export | `./mc progress merge <file.json> --dry-run` first, then without `--dry-run` (or `-` for stdin) |
| Clear all progress | `./mc progress reset --force` (only when the user asks; a backup is written) |
| Import addon data | `./mc import-addon <path/to/LegacyTracker.lua> [--dry-run] [--force]` |
| Make a shareable copy of addon data | `./mc scrub-addon <path/to/LegacyTracker.lua> [-o file.json]` (roster characters only; no gold or time played) |
| Map an in-game name | `./mc map <char> <InGameName>` |
| Show progress | `./mc progress show` |
| Serve the page | `./mc serve --port 8000` |
| Run every check | `./mc doctor` and `python3 -m unittest discover -s tests` |
| Pre-PR privacy check | `./mc leakcheck` |
| Show the release version | `./mc version` (`--check`: VERSION, addon .toc and CHANGELOG agree) |
| Cut a release (maintainers only) | follow [docs/releasing.md](docs/releasing.md) |

`<char>` is a character id or name from the roster. After any progress change, run `./mc generate` so the page and canvas pick it up, then commit if the user keeps progress in git.

### Setup interview

Ask the user for: a roster name, faction (Alliance or Horde), ruleset (Normal, PvP, Roleplay, Hardcore), how many characters (1 to 10; four is the default and recommended), and for each character: name, race, class, leveling spec, endgame spec, and professions. Offer `config/examples/*.json` as a starting point. Allowed values are in `config/roster.schema.json` and [docs/config.md](docs/config.md). The answers file format:

```json
{"roster_name": "Our Group", "faction": "Alliance", "ruleset": "Normal", "count": 4,
 "c1.name": "Aldric", "c1.race": "Human", "c1.class": "Warrior", "c1.leveling_spec": "Arms", "c1.endgame_spec": "Protection",
 "c1.professions": "Mining, Blacksmithing, Engineering 60-"}
```

A profession entry may carry a level window: `Engineering 60-` starts at 60, `Mining 1-60` drops it at 60. Repeat `c2.*` up to `c<count>.*`; `count` defaults to 4. Spec keys are optional (class defaults are used).

Help the user cover all six crafts (Alchemy, Blacksmithing, Enchanting, Engineering, Leatherworking, Tailoring) across the roster, with at most two primary professions per character at any level. `./mc validate` reports gaps.

### Progress updates

Users report progress in plain language ("Aldric is 23 with full rested, Elowen hit 150 Alchemy, we finished Deadmines"). Translate to commands: `./mc level`, `./mc skill`, `./mc ids deadmines` then `./mc check <ids>`. If the user uploads a page export, use `./mc progress merge`. If they upload `LegacyTracker.lua`, use `./mc import-addon` (try `--dry-run` first and show the result). Then `./mc generate`. If a user wants to send their addon data to someone else, use `./mc scrub-addon` and send its output, never the raw `LegacyTracker.lua`.

The addon reports names exactly as in game. If a name does not match the roster (for example a renamed character), run `./mc map <char> <InGameName>` and import again.

### Answering questions

Use `./mc plan` and the files in `data/` (each fact cites a source in `data/sources.json`). Say when something is marked `unverified` or `classic`. Link game names to Wowhead using `data/wowhead.json` or a `https://www.wowhead.com/forever/search?q=` link. Do not invent quest names, levels or rewards.

## Syncing with upstream

In a personal copy:

```sh
make sync     # or:
git remote add upstream https://github.com/BradGroux/wow-forever-mission-control.git   # once
git fetch upstream
git merge upstream/main --allow-unrelated-histories --no-edit
./mc generate && ./mc doctor
```

Personal files never exist upstream, so a merge does not overwrite them. If the merge conflicts, it is in a shared file the user edited (often README.md); resolve in favor of upstream unless the user's change was deliberate. The `Sync from upstream` workflow does the same weekly and opens a pull request. Details: [docs/updating.md](docs/updating.md).

## Preparing an upstream pull request without leaking personal data

Never put the user's character names, account name, realm, progress, SavedVariables, or roster into an upstream pull request.

1. Branch from upstream, not from the personal main:
   ```sh
   git fetch upstream
   git switch -c fix/short-name upstream/main
   ```
2. Make the change only in shared files (`data/`, `scripts/`, `web/` except `web/data/plan.js`, `addon/`, `docs/`, `tests/`, `adapters/grokbot/template.canvas.tsx`, `config/examples/`, `.github/`). Cherry-pick from personal main only commits that touch nothing else.
3. Run `./mc generate && ./mc doctor && python3 -m unittest discover -s tests && ./mc leakcheck`.
4. Check the diff by eye: `git diff upstream/main --stat` must list no personal file, and no personal names may appear (`git diff upstream/main | grep -i <each name>` returns nothing).
5. Push to the user's fork (or a fork of upstream) and open the PR against `BradGroux/wow-forever-mission-control:main` using the PR template. Ask the user before pushing or opening the PR.

Data changes must follow the sourcing rules in [CONTRIBUTING.md](CONTRIBUTING.md#data-sourcing-rules): a Wowhead or Blizzard link per fact, and `"status": "unverified"` when unsure.

## Rules

- Never commit secrets, tokens, Battle.net account names, or raw `WTF/` folders.
- Don't hand-edit `web/data/*.js`, `docs/examples/*`, or `adapters/grokbot/mission-control.canvas.tsx`; they are generated.
- Keep `./mc` standard-library-only Python 3.9+ and the page plain HTML/CSS/JS with no build step.
- Keep the addon silent outside `/ltrack`, Interface 16001, Lua 5.1 compatible, and run `addon/test/harness.lua` after changes.
- Ask before any externally visible action: pushing, opening issues or PRs, deploying.
