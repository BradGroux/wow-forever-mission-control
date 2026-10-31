# Setup

## 1. Get your own copy

Pick one:

| Option | Private? | Pulls upstream updates | Best for |
| --- | --- | --- | --- |
| **Use this template** (green button on GitHub) | Yes, you choose | Yes, with the sync workflow or `make sync` | Most groups |
| **Fork** | No, forks of a public repo are public | Yes (GitHub's "Sync fork" button also works) | Contributing back often |
| **Download ZIP** | Local only | Manually | Trying it out |

Then clone your copy:

```sh
git clone https://github.com/<you>/<your-copy>.git
cd <your-copy>
```

You need **Python 3.9 or newer**. Nothing to install with pip. On Windows, replace `./mc` with `python mc` in every command.

## 2. Make your roster

Interactive:

```sh
./mc init
```

It asks for a roster name, faction, ruleset, and for each of four characters a name, race, class, leveling and endgame spec, and professions. Press Enter to accept a default. It writes `config/roster.json`.

Or copy an example and edit it:

```sh
cp config/examples/alliance.json config/roster.json     # or horde.json
```

Every field is described in [config.md](config.md).

## 3. Validate

```sh
./mc validate
```

Errors (must fix): illegal race and class combos, a race from the other faction, a spec that doesn't belong to the class, more or fewer than four characters, three primary professions at once, duplicate names or ids.

Warnings (worth fixing): a crafting profession nobody takes (that costs 3 Legacy points), two characters on the same craft, two characters of the same class, names that are not 2 to 12 letters.

Notes: Skyborne needs the Heroic Pack; a craft with no matching gatherer in the group.

## 4. Generate and open

```sh
./mc generate
./mc serve          # http://localhost:8000
```

Or double-click `web/index.html`. The page works from a local file.

`./mc generate` writes:

| File | What | Commit it? |
| --- | --- | --- |
| `web/data/plan.js` | your plan, read by the page | Yes, if you host the page |
| `adapters/grokbot/mission-control.canvas.tsx` | Grok Bot canvas with your plan and saved progress | Optional |
| `build/plan.json`, `build/PLAN.md` | the plan as JSON and Markdown | No (ignored) |

## 5. Share it with your group

Host the page for free: [hosting.md](hosting.md). Each player's checkboxes and levels are saved in their own browser. To combine them, see [progress.md](progress.md).

## 6. Optional: the addon

Install [LegacyTracker](addon.md) so levels, rested XP and profession skill fill themselves in.
