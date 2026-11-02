## What changed

<!-- One or two sentences. Link the issue: Fixes #123 -->

## Sources (data changes)

<!-- A Wowhead Forever or Blizzard link for each fact. Mark anything uncertain "unverified". -->

## Checklist

- [ ] Branched from upstream `main` (not from a personal copy's `main`)
- [ ] `./mc generate` run and generated files committed
- [ ] `./mc doctor` and `python3 -m unittest discover -s tests` pass
- [ ] `./mc leakcheck` passes: no `config/roster.json`, `progress/`, `web/data/plan.js`, personal canvas, or `WTF` files
- [ ] No personal character names, realm or account names in the diff
- [ ] UI changes follow [docs/design.md](https://github.com/BradGroux/wow-forever-mission-control/blob/main/docs/design.md) (no instructions, captions, state words or caveats in the page; level ranges; Wowhead links; class icons and colors; palette; both pages match)
- [ ] Docs updated if behavior changed
