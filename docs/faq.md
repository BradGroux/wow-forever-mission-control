# FAQ

**Do I need four players?**
No. Four characters is the design (class and craft Legacy challenges reward spreading out), but one player with four alts works the same way.

**Can I use fewer or more than four characters?**
Yes. A roster can have 1 to 10 characters. Four stays the default and the recommended goal: `./mc validate` prints a note (not a warning) for other sizes. With one or two characters, missing crafts are notes too, since two primary professions each can't reach all six crafts. The page, canvas, timeline and addon import all follow the roster size, and checklist ids stay keyed by character id, so adding or removing a character later keeps everyone else's progress.

**Why four characters and all six crafts?**
Crafting Legacy challenges pay at 150, 225 and 300 skill in each of the six crafting professions (18 points). With two primary professions per character, four characters can cover all six if they plan it. Class challenges (27 points) also reward leveling different classes.

**Can we mix Alliance and Horde?**
No. One roster is one faction, so you can group. Make two rosters (two copies) if you need both.

**Is my data sent anywhere?**
No. The page has no backend; progress stays in your browser's localStorage unless you export it or commit it. The addon writes only to your own WoW folder.

**Does the addon break any rules?**
It only reads your own character's information through the normal addon API and saves it at logout, like any stat-tracking addon. It does not automate gameplay.

**The page says "Unverified" or "Classic data". Is it wrong?**
Maybe not, but nobody has confirmed it for Forever yet. If you can confirm or correct it in game, please open a [data correction](https://github.com/BradGroux/wow-forever-mission-control/issues/new?template=data-correction.yml).

**Two of us use different browsers. Whose checkboxes win?**
Each browser keeps its own. Export from one and import into the other, or have one person merge everything into `progress/progress.json`. See [progress.md](progress.md).

**I renamed a character in game.**
Keep the roster `id`, update the `name`, and run `./mc map <id> <NewName>` so the addon import still matches.

**I changed my roster after starting. Will I lose progress?**
Not if the character `id` stays the same. Items that no longer apply simply disappear.

**Can I use it without Python?**
For viewing and tracking, yes: open a hosted copy of the page. To build a page for your own roster you need `./mc generate` once, which needs Python 3.9+. Cloudflare Pages can run it for you (see [hosting.md](hosting.md)).

**Does it work with my AI assistant?**
Yes. Any agent that can read files and run commands can use it; see [agents/README.md](agents/README.md).

**Where do the facts come from?**
[data/sources.json](../data/sources.json): Blizzard news posts, Wowhead's Forever guides and database, and community guides. See [data.md](data.md).
