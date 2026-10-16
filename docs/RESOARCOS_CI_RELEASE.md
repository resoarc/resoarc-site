# ResoArcOS developer preview: reproducible release path

更新: 2026-10-16

## Source of truth

The complete OS source snapshot is kept in `site/downloads/resoarcos-pc-v0.1.0-dev-source.zip` and is pinned by SHA-256 `72b427a8ef08ab388dc70ad2f1b14bcb2a7517b8f5edd0ebe67c8d934a93bb20`.

The release workflow checks out the exact triggering Git commit, verifies the pinned archive, refuses traversal and symbolic-link ZIP entries, and extracts it inside the runner before building. **It does not download its build input from the website.** This prevents a stale deployment or a transient HTTP 404 from breaking the ISO build.

The published website copy may be checked separately by `.github/workflows/site-integrity.yml`. The content must match the pinned digest.

## Release safety policy

- The generated PC image is a developer preview, not a production-ready or safe installer.
- The build tests source and ISO contents, BIOS/UEFI default boot parameters and QEMU's direct-kernel headless/GUI sequence; this is not equivalent to physical hardware certification.
- The workflow cannot publish a release unless tests and ISO verification pass.
- GitHub Actions `GITHUB_TOKEN` needs Contents: write to create the prerelease. No personal GitHub token should be stored in source.
- The fixed tag `resoarcos-pc-v0.1.0-dev-20261016` must not be overwritten without an explicit, audited release policy. Running the same release after successful publication can fail at the final create step. Do not delete or overwrite a published artifact to hide a mismatch.

## Local audit

```powershell
python scripts/update_manifest.py
python scripts/verify_site.py
python scripts/verify_resoarcos_snapshot.py
```

For changes to the snapshot, deliberately create a new pinned source digest and new preview version; do not replace bytes while keeping the same digest. Run the OS-specific unit tests and full CI to validate a new release.

## Prior failures

- 2026-10-16: OS preview workflow encountered HTTP 404 while fetching site-hosted source.
- An earlier release attempt built and boot-tested the ISO but referred to `source.zip` from the `source/` working directory rather than `../source.zip`, so GitHub CLI could not find the file.
- The source path issue was corrected. This change additionally removes the network/website fetch from the build path.
