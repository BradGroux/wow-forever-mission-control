# Hosting the page

The page is static files in `web/`: `index.html`, `app.js`, `style.css` and `data/*.js`. No server code, no database, no build tools beyond `./mc generate`. Host it anywhere that serves files, or just open it locally.

Progress ticked on a hosted page is saved in each visitor's browser. To publish shared progress, commit `progress/progress.json` and regenerate ([progress.md](progress.md)).

## Local

- Double-click `web/index.html` (works from `file://`), or
- `./mc serve` and open http://localhost:8000 (`--port` to change).

## GitHub Pages

The repo ships [.github/workflows/pages.yml](../.github/workflows/pages.yml). It runs `./mc generate` (your `config/roster.json` if present, else the example) and deploys `web/`.

1. In your copy, open **Settings > Pages** and set **Source** to **GitHub Actions**.
2. Open **Settings > Secrets and variables > Actions > Variables** and add a repository variable `MC_PAGES` with value `true`. (The workflow skips copies without it, so nobody gets surprise failures.)
3. Push to `main`, or run the workflow from the **Actions** tab. The page appears at `https://<you>.github.io/<repo>/`.

GitHub Pages on a **private** repository needs a paid GitHub plan, and the published site is public either way. If your copy is private on a free plan, use Cloudflare Pages. Docs: [Configuring a publishing source](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site), [GitHub Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits).

## Cloudflare Pages

Cloudflare Pages is free, works with public **and private** GitHub repositories, and serves `web/` as is. There are two ways to deploy. Pick one per project: Cloudflare does not let a project switch between Git integration and Direct Upload later.

### Option A: Git-connected (deploys on every push)

1. In the Cloudflare dashboard go to **Workers & Pages**, then **Create application > Pages > Connect to Git**.
2. Authorize GitHub and select your copy of the repo.
3. Set up builds and deployments:
   - **Production branch:** `main`
   - **Framework preset:** None
   - **Build command:** `python3 mc generate`
   - **Build output directory:** `web`
   - **Root directory:** leave blank (repository root)
4. **Save and Deploy.** The page is served at `https://<project>.pages.dev`. Every push to `main` redeploys; other branches get preview URLs.

The Pages v3 build image includes Python 3, so the build command needs nothing else. If you already commit `web/data/plan.js`, you can leave the build command blank instead.

Docs: [Git integration](https://developers.cloudflare.com/pages/get-started/git-integration/), [Build configuration](https://developers.cloudflare.com/pages/configuration/build-configuration/), [Build image (languages and versions)](https://developers.cloudflare.com/pages/configuration/build-image/).

### Option B: Direct Upload with Wrangler (deploy from your computer)

Needs Node.js with `npm`.

```sh
./mc generate
npx wrangler login
npx wrangler pages project create          # asks for a project name and production branch (main)
npx wrangler pages deploy web              # deploys to https://<project>.pages.dev
```

Run `./mc generate` and `npx wrangler pages deploy web` again whenever you update progress. Add `--branch=<name>` for a preview deployment at `<name>.<project>.pages.dev`. You can also drag and drop the `web` folder in the dashboard (**Create application > Pages > Drag and drop your files**).

To deploy from GitHub Actions instead, follow [Use Direct Upload with continuous integration](https://developers.cloudflare.com/pages/how-to/use-direct-upload-with-continuous-integration/); store the API token as a repository secret, never in the repo.

Docs: [Direct Upload](https://developers.cloudflare.com/pages/get-started/direct-upload/), [Wrangler `pages` commands](https://developers.cloudflare.com/workers/wrangler/commands/pages/).

### Keeping it private

Pages sites are public by default. To limit the page to your group, put [Cloudflare Access](https://developers.cloudflare.com/cloudflare-one/access-controls/policies/) in front of it: Pages project **Settings > Enable access policy** covers preview deployments, and Cloudflare's [steps for the `*.pages.dev` domain](https://developers.cloudflare.com/pages/platform/known-issues/#enable-access-on-your-pagesdev-domain) extend it to the production URL. See [Preview deployments](https://developers.cloudflare.com/pages/configuration/preview-deployments/).

## Anything else

Netlify, Vercel, an S3 bucket, a USB stick: upload the contents of `web/` after `./mc generate`.
