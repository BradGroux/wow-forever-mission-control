# Grok Bot canvas adapter (optional)

The static page in `web/` is the main interface and works everywhere. This folder is an extra for Grok Bot users: the same plan as a live canvas Page inside Grok Bot.

| File | Upstream | Your copy |
| --- | --- | --- |
| `template.canvas.tsx` | yes | from upstream; don't edit unless you're contributing |
| `mission-control.canvas.tsx` | never | written by `./mc generate` from your roster and `progress/progress.json` |

The template has two generated blocks:

- `// ROSTER-START` ... `// ROSTER-END`: your plan (`const PLAN: Plan = {...}`)
- `// SAVED-START` ... `// SAVED-END`: saved progress (`const SAVED: Saved = {...}`), empty by default

`./mc doctor` checks that the SAVED block matches `progress/progress.json`.

## Use it

Ask Grok Bot:

> Clone my Mission Control repo, run `./mc generate`, and publish `adapters/grokbot/mission-control.canvas.tsx` as a Page.

Checkboxes on the Page last for the session. The **Copy progress** button copies the progress JSON; give it back to Grok Bot ("merge this progress") and it runs `./mc progress merge`, `./mc generate`, and republishes the Page with the new SAVED block. The same JSON also imports into the web page.

Without a personal roster, `./mc generate` writes an example canvas to `build/mission-control.canvas.tsx`.
