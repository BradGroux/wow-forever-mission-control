# LegacyTracker

Silent WoW Forever addon (Interface 16001) that records level, XP, rested XP, profession skill and zone for every character on the account (gold and time played only after `/ltrack extras on`), for [WoW Forever Legacy Mission Control](../README.md). No UI, no chat output except `/ltrack`.

Install: copy the `LegacyTracker` folder into `World of Warcraft\_forever_\Interface\AddOns\`.

Data: `World of Warcraft\_forever_\WTF\Account\<ACCOUNT>\SavedVariables\LegacyTracker.lua`, written at logout or `/reload`. Import it on the page (**Import progress**) or with `./mc import-addon <path>`.

Full instructions: [docs/addon.md](../docs/addon.md). Tests: `addon/test/harness.lua` (see the same doc).
