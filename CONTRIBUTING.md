# Contributing

Thanks for helping. Every correction makes the plan better for every group leveling in WoW Forever, and you do not need to write code to help: an issue with a Wowhead link is a real contribution.

Please follow the [Code of Conduct](CODE_OF_CONDUCT.md).

## What we want most

| Area | Examples | Label |
| --- | --- | --- |
| **Data corrections** | wrong quest level, class quest name, dungeon level range, zone range, racial changes at launch | `data` |
| **Horde data** | Horde class quest chains, flight paths, boats and zeppelins, first hubs, supply faction details | `horde` |
| **Unverified and Classic data** | confirming anything tagged Unverified or Classic data on the page | `unverified` |
| **Launch day** | changes Blizzard ships on Nov 4, 2026; new Wowhead ids; an official API or Armory | `launch-day` |
| **Docs** | clearer setup steps, screenshots, translations, macOS and Linux paths | `docs` |
| **Page features** | better mobile layout, group views, charts, accessibility | `page` |
| **The addon** | more data worth recording, client API changes after launch | `addon` |
| **CLI** | flexible roster size, new checks, better interview | `cli` |

New here? Look for [good first issue](https://github.com/BradGroux/wow-forever-mission-control/labels/good%20first%20issue).

## Quick ways to help

- **Found something wrong in game?** Open a [data correction](https://github.com/BradGroux/wow-forever-mission-control/issues/new?template=data-correction.yml) with what you saw and a Wowhead link or screenshot. That's enough; someone will turn it into a fix.
- **Bug or idea?** Use the [bug](https://github.com/BradGroux/wow-forever-mission-control/issues/new?template=bug.yml) or [feature](https://github.com/BradGroux/wow-forever-mission-control/issues/new?template=feature.yml) forms.

## Data sourcing rules

All game facts live in `data/*.json`.

1. **Every fact needs a source.** Use a source id from `data/sources.json` in the record's `"source"` field. Add a new source (id, title, site, url) if needed. Preferred order: Blizzard (news posts, patch notes, in game), the [Wowhead Forever database](https://www.wowhead.com/forever) and guides, then community guides.
2. **Link names to Wowhead.** Add the verified id to `data/wowhead.json` (`"Name": {"type": "quest", "id": 12345}`), or run `python3 tools/wowhead_lookup.py --missing --write`. Use Forever pages (`wowhead.com/forever/...`), not Classic or retail ones.
3. **Mark uncertainty.** Set `"status"` to:
   - `blizzard`: confirmed by Blizzard or seen live after launch
   - `beta`: seen on the Forever beta
   - `classic`: copied from Classic Era and not yet confirmed for Forever
   - `unverified`: one community report, or an inference
   When in doubt, choose `unverified`. Never present a guess as fact, and never invent quest names, levels, ids or rewards.
4. **Keep Alliance and Horde both in mind.** Add the Horde side when you add an Alliance fact, or open a `horde` issue for it.
5. **Regenerate.** Run `./mc generate` and commit the regenerated `web/data/plan.example.js` and `docs/examples/*`.

## Contributing back from your personal copy

Your copy has personal files that must never reach upstream: `config/roster.json`, `progress/`, `web/data/plan.js`, `adapters/grokbot/mission-control.canvas.tsx`, and anything from your `WTF` folder. Your character names, realm and account name should not appear in a pull request either.

1. Make sure you have a fork of upstream to push to. (A template copy is a separate repo, not a fork; create a fork of [BradGroux/wow-forever-mission-control](https://github.com/BradGroux/wow-forever-mission-control/fork) for pull requests.)
2. Branch from **upstream** `main`, not your personal `main`:
   ```sh
   git remote add upstream https://github.com/BradGroux/wow-forever-mission-control.git   # once
   git remote add fork https://github.com/<you>/wow-forever-mission-control.git            # once
   git fetch upstream
   git switch -c fix/horde-flight-paths upstream/main
   ```
3. Make the change, or bring it over with `git cherry-pick <commit>` if the commit touches only shared files.
4. Check:
   ```sh
   ./mc generate
   ./mc doctor
   python3 -m unittest discover -s tests
   ./mc leakcheck
   git diff upstream/main --stat        # no personal files
   ```
5. Push and open the PR:
   ```sh
   git push fork fix/horde-flight-paths
   gh pr create --repo BradGroux/wow-forever-mission-control --base main
   ```
   Or use the "Compare & pull request" button on GitHub. Fill in the PR template.

Working directly in a fork of upstream (no personal data in it)? Branch, change, and open a PR as usual.

Agents: [AGENTS.md](AGENTS.md) has the same steps.

## Development

- `./mc` is Python 3.9+, standard library only. Keep it that way.
- The page (`web/`) is plain HTML, CSS and JavaScript with no build step and no dependencies. It must keep working from `file://`.
- Page style: every game name links to Wowhead; no instructions or captions in the page body; level ranges instead of codes.
- The addon is Lua 5.1, Interface 16001, silent outside `/ltrack`.
- Generated files (`web/data/*.js`, `docs/examples/*`) are committed; regenerate them, don't edit them.

Run everything CI runs:

```sh
./mc validate --strict --config config/examples/alliance.json
./mc validate --strict --config config/examples/horde.json
./mc doctor
python3 -m unittest discover -s tests -v
node tests/web_import.test.js
luac5.1 -p addon/LegacyTracker/LegacyTracker.lua
lua5.1 addon/test/harness.lua addon/LegacyTracker/LegacyTracker.lua | diff -u addon/test/SavedVariables.sample.lua -
```

## Pull requests

- One topic per PR. Small is great.
- CI must pass.
- Describe what changed and link sources for data changes.
- By contributing you agree your work is licensed under the [MIT License](LICENSE).
