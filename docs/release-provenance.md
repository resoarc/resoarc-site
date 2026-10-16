# Verifying release provenance / リリースの来歴証明

ResoArc development previews are not production-ready. For a **future release made using the provenance-enabled workflow**, download the ISO, `SHA256SUMS` and `release-provenance.sigstore` assets from the *same release*. Also inspect the release notes for the matching source archive.

The bundle is signed using GitHub artifact attestations (Sigstore, keyless OIDC) by the `resoarc/resoarc-site` workflow. The attestation identifies the source repository and file digests. This is **not** an assertion of vulnerability-free software, secure-boot compatibility, a production OS, or signed Git tags.

## Verify on Linux or macOS

```bash
# Substitute the actual release filename.
gh attestation verify ./resoarcos-pc-RELEASE-amd64.iso \
  --repo resoarc/resoarc-site \
  --bundle ./release-provenance.sigstore
```

Compare the ISO's SHA-256 hash with the corresponding entry in `SHA256SUMS`. If using the source archive from that release, verify the archive against the same bundle.

On Windows, inspect the SHA-256 digest with `Get-FileHash <ISOFILE> -Algorithm SHA256` and verify the attestation with the GitHub CLI.

Do not accept a bundle from a different release, or treat a plain checksum without authenticated provenance as proof of origin.

## Historical releases

ResoArcOS PC v0.1.0-dev and v0.1.1-dev dated 2026-10-16 were published before this attestation flow. **They must not be represented as having signed build provenance** until fresh, independently verified releases are actually published. No signature is retroactively asserted.

The `publish` job is manual-only and refuses to overwrite an existing release tag. New version/tag/source checksums must be reviewed before triggering publication.
