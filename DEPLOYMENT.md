# ResoArc site publication rules

Cloudflare Pages project `resoarc` uses **Direct Upload** (`Git Provider: No`). Pushing to GitHub does **not** deploy the site. The **only source of truth** for production website files is `site/` in the official [resoarc/resoarc-site](https://github.com/resoarc/resoarc-site) repository.

## Required workflow

1. Fast-forward the official `main` branch locally. Do not replace its current `site/` with an older `dist/`, `os-release-stage-*`, or a single-project preview.
2. Apply changes inside `site/`, preserving all existing web and kintone tools, and regenerate `site-manifest.sha256` with `python scripts/update_manifest.py`.
3. Run `python scripts/verify_site.py`. This requires the ResoArcOS page, OS navigation on all HTML pages, and a pinned source ZIP digest.
4. Commit and publish the changes using the **ResoArc account only**. Do not mix in personal projects, untracked files, or private identities.
5. Run `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/deploy_canonical.ps1 -WranglerPath <path-to-wrangler.cmd>` from the repository checkout. The script refuses stale or dirty site trees, verifies the GitHub head, deploys the canonical `site/` and checks apex, www, Pages hostnames, and the source ZIP.
6. Do not declare a release complete until live smoke tests pass. If they fail, restore from the previous verified Git commit and redeploy it.

**ResoArcOS PC v0.1.0-dev is a developer preview, not a production operating system.** The Live ISO has no safe installer, persistent account security, signed OTA, or hardware certification. GitHub Actions may distribute the ISO only as a prerelease after its verification gates pass.

## Why this rule exists

On 2026-10-16 a manual Cloudflare deployment from an old `dist/` tree removed `/os/` and its download assets, even though the OS page existed in a different deployment. Another stale deployment reproduced the problem. The canonical `site/` integration and release checks prevent the same mistake when the guarded process is used.

Cloudflare Pages currently does not auto-publish from GitHub. Do not assume a successful Git commit has changed the live website.
