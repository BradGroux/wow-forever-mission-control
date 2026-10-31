# The LegacyTracker addon

LegacyTracker is a tiny addon that silently records, for every character you log in on the account:

- level, plus the time each level was reached
- XP, XP to next level, and rested XP
- profession skill for every profession
- zone and resting state
- class, race, faction, realm, last seen

It does **not** record gold or time played unless you turn that on with `/ltrack extras on` (`/ltrack extras off` turns it off again and erases what was recorded). Nothing Mission Control does needs them.

It has no window, no minimap button and no chat messages. Type `/ltrack` to print a one-line summary per character. It works with any character names, on any realm, and needs no setup. Data stays on your computer in a SavedVariables file until you import it.

- Interface version: **16001** (WoW Forever)
- Files: [addon/LegacyTracker/](../addon/LegacyTracker)
- Lua 5.1, no libraries

## Install

1. Get the files. Either clone your copy of this repo, or on GitHub open **Code > Download ZIP** and unzip it.
2. Copy the folder `addon/LegacyTracker` (the folder itself, containing `LegacyTracker.toc` and `LegacyTracker.lua`) into the WoW Forever AddOns folder:

   **Windows** (default install):
   ```
   C:\Program Files (x86)\World of Warcraft\_forever_\Interface\AddOns\LegacyTracker\
   ```
   **macOS** (default install):
   ```
   /Applications/World of Warcraft/_forever_/Interface/AddOns/LegacyTracker/
   ```
   If WoW is installed elsewhere, open the Battle.net app, pick WoW Forever, and use **Options (gear) > Show in Explorer/Finder** to find the `_forever_` folder. Create `Interface\AddOns` if it doesn't exist.

   The result must be `...\AddOns\LegacyTracker\LegacyTracker.toc`, not `...\AddOns\LegacyTracker\LegacyTracker\LegacyTracker.toc`.
3. Start the game (or `/reload`). On the character select screen, open **AddOns** and make sure **LegacyTracker** is checked. If it shows "out of date", tick **Load out of date AddOns**.
4. Log in and type `/ltrack`. You should see your character, level and rested XP.

## Use it to track progress

1. Play normally. The addon updates on login, level up, XP gain, rested changes, zone changes, skill ups and logout.
2. **Log out or `/reload`** before importing. WoW only writes SavedVariables to disk at logout or reload.
3. Find the file:

   **Windows:**
   ```
   C:\Program Files (x86)\World of Warcraft\_forever_\WTF\Account\<ACCOUNT>\SavedVariables\LegacyTracker.lua
   ```
   **macOS:**
   ```
   /Applications/World of Warcraft/_forever_/WTF/Account/<ACCOUNT>/SavedVariables/LegacyTracker.lua
   ```
   `<ACCOUNT>` is a folder named after your account (often a number like `123456789#1`). There is one file per WoW account, covering all characters on it. Use the file directly under `SavedVariables`, not the per-character folders.
4. Import it, either way:
   - **Page:** click **Import progress**, choose `LegacyTracker.lua` (or paste its contents), and click **Import**. Levels, rested state and profession skills update in that browser.
   - **CLI** (updates `progress/progress.json`, so the whole group sees it after a commit):
     ```sh
     ./mc import-addon "C:\Program Files (x86)\World of Warcraft\_forever_\WTF\Account\<ACCOUNT>\SavedVariables\LegacyTracker.lua" --dry-run
     ./mc import-addon "<same path>"
     ./mc generate
     ```
     `make import SV="<path>"` does the same.
5. If your group plays on several accounts, each player imports their own file. Imports merge: the higher level wins and profession skills keep the highest value.

### Sharing with your group

`LegacyTracker.lua` holds data for **every character on your account**, not only the roster ones. Don't send the raw file. Send a scrubbed copy instead:

```sh
./mc scrub-addon "<path>\LegacyTracker.lua"     # writes progress-share-YYYY-MM-DD.json
```

It contains only the roster characters' level, rested state, zone and profession skill. The keeper merges it with `./mc progress merge progress-share-YYYY-MM-DD.json`; it never changes anyone's ticked checklist items. No Python? Import the file on the page and use **Export progress**: the page keeps only roster characters, so its export is just as clean.

### Rules the import follows

- Characters are matched by in-game name. Characters not on the roster are skipped and listed.
- A renamed character, or one whose in-game name differs from the roster: `./mc map <roster-id> <InGameName>`, then import again.
- An import never lowers a level and skips data that isn't newer than the last import. `--force` overrides both.
- Rested state: **Full** at 1.5 levels of rested XP (the cap), **Partial** above zero, **Empty** otherwise.
- A renamed copy of the addon (different SavedVariables table name) imports with `--db <TableName>`, for example `./mc import-addon OldTracker.lua --db OldTrackerDB`. The page's **Import progress** finds the table on its own.
- Gold and time played are never imported, even with `/ltrack extras on`.

## With an agent

Give your agent the `LegacyTracker.lua` file and say "import our addon data". Agents follow [AGENTS.md](../AGENTS.md): `./mc import-addon <file> --dry-run`, show you the result, then import and `./mc generate`.

## Troubleshooting

| Problem | Fix |
| --- | --- |
| `/ltrack` does nothing | The addon isn't loaded. Check the folder layout in step 2 and the AddOns list at character select. |
| File not found | Log out or `/reload` once after installing; the file is created at the first logout. |
| Import says "not on the roster" | Use `./mc map`, or fix the `name` in `config/roster.json`. |
| Level didn't change | The file is older than your last import. Log out to save, or use `--force`. |
| Skills missing | Open the game once after training; skills are read on `SKILL_LINES_CHANGED`. |

## Developing the addon

```sh
luac5.1 -p addon/LegacyTracker/LegacyTracker.lua
lua5.1 addon/test/harness.lua addon/LegacyTracker/LegacyTracker.lua > /tmp/sv.lua
diff -u addon/test/SavedVariables.sample.lua /tmp/sv.lua
```

The harness mocks the WoW API, logs in two characters, checks the addon stays silent outside `/ltrack`, and serializes `LegacyTrackerDB` like the client does. CI runs all three, then imports the result with `./mc import-addon`. If you change what the addon records on purpose, regenerate the sample with the second command and commit it.
