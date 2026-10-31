# Releasing

Maintainers cut releases from `main` of [BradGroux/wow-forever-mission-control](https://github.com/BradGroux/wow-forever-mission-control). Personal copies don't need to release anything; they pick up releases through [Updating](updating.md).

## Versions

A version is the release date: `YYYY.MM.DD` (for example `2026.10.31`), in US Central time, the maintainer's zone.

- A second release on the same day adds `.N`, starting at 1: `2026.11.04`, then `2026.11.04.1`, `2026.11.04.2`.
- The tag is the version with no prefix (`2026.10.31`, not `v2026.10.31`).
- Around launch, expect a release the day before (`2026.11.03`) and on launch day (`2026.11.04`, plus `.N` hotfixes) with whatever changes at launch.

The version lives in four places, and CI fails if they disagree:

| Where | What |
| --- | --- |
| `VERSION` | the version, one line |
| `CHANGELOG.md` | newest entry `## [VERSION] - YYYY-MM-DD` (date = the version's date) |
| `addon/LegacyTracker/LegacyTracker.toc` | `## Version: VERSION` |
| `web/data/plan.example.js` (generated) | `"release"`, shown in the page footer with a link to the release |

`./mc version` prints it; `./mc version --check` (also part of `./mc doctor`) checks the first three; the generated-files check in CI covers the fourth.

## Checklist

1. **Backlog.** `gh issue list --state open`. Any new bug or audit issue is fixed (or consciously deferred and listed under Known limitations) before release.
2. **Green main.** The latest CI run on `main` passed.
3. **Release branch.** `git switch -c release/YYYY.MM.DD`, then:
   - `VERSION`: the new version.
   - `addon/LegacyTracker/LegacyTracker.toc`: `## Version:` the new version.
   - `CHANGELOG.md`: move everything from `## [Unreleased]` into `## [YYYY.MM.DD] - YYYY-MM-DD` with Added / Changed / Fixed / Security / Known limitations / Upgrade sections; link each fixed issue and its pull request; update the compare links at the bottom.
   - `./mc generate` (puts the version into `web/data/plan.example.js`, which the page footer reads).
4. **Checks.** `./mc version --check && ./mc doctor && python3 -m unittest discover -s tests && node tests/web_import.test.js && python3 tools/package_release.py --check`.
5. **Pull request.** Title `Release YYYY.MM.DD`; CI green; merge.
6. **Tag** the merge commit on `main`:
   ```sh
   git switch main && git pull
   git tag -a YYYY.MM.DD -m "WoW Forever Mission Control YYYY.MM.DD"
   git push origin YYYY.MM.DD
   ```
7. **Assets.** `python3 tools/package_release.py` writes to `dist/` (git-ignored):
   - `LegacyTracker-YYYY.MM.DD.zip`: the `LegacyTracker/` folder, ready to drop into `Interface/AddOns`.
   - `mission-control-web-YYYY.MM.DD.zip`: the static page with the example roster, ready for any static host.
   - `SHA256SUMS.txt`.
8. **GitHub Release** titled `WoW Forever Mission Control YYYY.MM.DD`, notes from the template below:
   ```sh
   gh release create YYYY.MM.DD dist/*.zip dist/SHA256SUMS.txt \
     --title "WoW Forever Mission Control YYYY.MM.DD" --notes-file notes.md --verify-tag
   ```
9. **After.** Check the release page and the demo page footer; add a fresh empty `## [Unreleased]` section if the release PR removed it. Maintainers with a personal copy sync it (merge, not squash) and may tag it with the same version.

## Release notes template

```markdown
WoW Forever Mission Control YYYY.MM.DD: one-line summary.

## Highlights
- ...

## Install / quick start
- New group: **Use this template**, then `./mc init`, `./mc validate`, `./mc generate`, open `web/index.html`.
- Addon: unzip `LegacyTracker-YYYY.MM.DD.zip` into `World of Warcraft/_forever_/Interface/AddOns/`.
- Static page only: unzip `mission-control-web-YYYY.MM.DD.zip`, add your `data/plan.js`, upload.

## What's included
- ...

## Fixes
- #N title (PR #M)

## Known issues
- ...

## Upgrade notes
- Existing copies: merge the Sync from upstream PR (or `make sync`), `./mc generate`, commit.

Full changelog: https://github.com/BradGroux/wow-forever-mission-control/blob/main/CHANGELOG.md
```

## Same-day hotfix

1. Fix on a branch with a regression test, PR, CI green, merge.
2. Bump to the next suffix (`2026.11.04` → `2026.11.04.1`) in `VERSION`, the `.toc` and a new `CHANGELOG.md` entry `## [2026.11.04.1] - 2026-11-04` that lists only the hotfix.
3. `./mc generate`, release PR, merge, tag, assets, release, as above. Never move or reuse a published tag; publish a new suffix instead.

## Data-only releases

Game data changes (new Wowhead ids, launch corrections) follow the same steps. List them under **Changed** with the source and the issue they close; status tags (Seen in beta, Classic data, Unverified) change only with a cited source.
