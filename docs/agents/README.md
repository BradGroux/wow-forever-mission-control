# Using Mission Control with AI agents

[AGENTS.md](../../AGENTS.md) is the single source of instructions. Every platform below reads it directly or through a pointer file, and every workflow is a plain `./mc` command, so no platform has special features the others lack.

## Prompts that work everywhere

- "Set up WoW Forever Legacy Mission Control for our group. Interview me for our four characters, validate, and generate the page."
- "Make sure our professions cover all six crafts and suggest swaps if not."
- "Aldric hit 23 with full rested; Elowen has 150 Alchemy; we cleared Deadmines. Update progress."
- "Here's my LegacyTracker.lua. Import it and show me what changed."
- "What should Brannoc do between 26 and 32?"
- "Sync with upstream." / "Prepare a pull request upstream with the Horde flight path fix, without any of our personal data."

## Platform notes

### ChatGPT and Codex (OpenAI)
- **Codex** (cloud, CLI, IDE) reads `AGENTS.md` automatically. Point it at your copy of the repo and use the prompts above.
- **ChatGPT** without repo access: upload `config/roster.json` (or ask it to interview you and produce one), plus `data/*.json` if you want answers about the game. Ask it to give you the `./mc` commands to run, then paste the output back. ChatGPT with a code environment can run `./mc` itself on an uploaded ZIP of the repo.
- **ChatGPT Sites** can host the page: see [hosting.md](../hosting.md#chatgpt-sites).

### Claude and Claude Code (Anthropic)
- **Claude Code** reads `CLAUDE.md`, which points to `AGENTS.md`. Run it in the repo folder.
- **Claude.ai** projects: add `AGENTS.md`, `config/roster.json` and `data/*.json` as project knowledge; it can draft roster changes and command lists for you.

### Cursor
`.cursor/rules/mission-control.mdc` (always applied) points to `AGENTS.md`. Cursor's agent also reads `AGENTS.md` directly. Open the folder and ask in chat.

### GitHub Copilot
`.github/copilot-instructions.md` points to `AGENTS.md`. Works in VS Code agent mode, Copilot Chat, and the Copilot coding agent: assign it an issue in your copy such as "Record Aldric at level 23 and regenerate."

### Gemini (Google)
**Gemini CLI** reads `GEMINI.md`, which points to `AGENTS.md`. Run it in the repo folder.

### Grok Bot
Grok Bot can clone your copy on its computer, run `./mc`, and keep your progress in git. It can also show your plan as a live canvas Page: see [adapters/grokbot/README.md](../../adapters/grokbot/README.md). Ask: "Set up Mission Control from my repo and make it a Page."

### Muse
Give Muse access to your copy of the repository (or upload the files) and ask it to follow `AGENTS.md`. If it can run commands, it uses `./mc` like any other agent; if not, have it produce the `config/roster.json` edits and the commands for you to run.

### Anything else
Any assistant that can read a file and run a shell command can follow `AGENTS.md`. Assistants that can't run commands can still help: give them `AGENTS.md` and `config/roster.json`, and run the commands they suggest.

## Safety

`AGENTS.md` tells agents to ask before pushing, opening pull requests or deploying, never to commit secrets or raw `WTF/` folders, and to run `./mc leakcheck` before any upstream pull request.
