# Security Trio v0.3.0-rc4: 2026-11-11 release checklist

> Scope: Windows x64, **UNSIGNED prerelease**, no code-signing certificate.
> Internal release decision: ResoArc accepts AI review in place of an optional outside reviewer for this limited unsigned preview. **This does not replace any SignPath Foundation eligibility or genuine human-signature approval requirements.**

## Unsigned public prerelease gate

- [x] Original three offline, static, user-selected file scanners and Python source in public PR #91
- [x] Security behavior review: read-only input, bounded files, no ZIP extraction, explicit scan incompleteness, output overwrite protections, token/IP/URL masking and CSV formula safety reviewed as implemented
- [x] Windows source unit regression **177 tests run, 1 skipped**, completed with exit 0 on Python **3.10, 3.13, 3.14**
- [x] Windows non-GUI source acceptance across all three engines **3/3 pass**
- [x] Public GitHub Actions historical unsigned Windows x64 build, source SHA `3656fc73de7f9ad0ea59957835398e9d647c3b4b`, includes verified EXE build, metadata, negative Authenticode gate, native inventory, license notices; 163 tests on that earlier code
- [x] Historical CI artifact `13677393414`: **exact three unsigned EXEs** with matching checksums both inside its distribution ZIP and in the outer CI artifact; **12 original third-party license notices** and MIT license present
- [x] [AI reviewer decision and known residual risks](AI_UNSIGNED_RELEASE_REVIEW_20261111.md): approves **limited, explicitly unsigned RC4 public prerelease only**
- [x] [Unsigned release workflow](../../.github/workflows/security-trio-unsigned-release.yml) designed to re-run the Windows CI and fail closed on runtime inventory, Authenticode, manifest, exact files and dependency license notices before publishing
- [ ] **New** GitHub-hosted Windows CI passed for the merged `main` commit and the exact final unsigned release artifact
- [ ] GitHub Release created, unique immutable `security-trio-v0.3.0-rc4-unsigned` tag verified; assets downloadable with expected hashes
- [ ] Official product page links to that verified release URL and differentiates previous RC4 preview downloads from newer CI-produced unsigned assets

**Unsigned distribution policy:** Publishing a clearly marked RC4 pre-release may proceed under the project's AI review policy *only after* the new Windows and distribution checksum gates pass. Release may not silently replace old download files. Do not claim GA, antivirus protection, SmartScreen clearance, external review, independent human review, full reproducible builds or signature.

## Engineering verification not yet established and therefore disclosed

- GUI and Explorer drag-and-drop for the **exact** final GitHub-hosted Windows EXEs on independent standard-user machines
- UNC / OneDrive / very long paths, accessibility/multimonitor issues and full adversarial performance
- Coverage against real malicious documents and production logs; heuristic false negatives are inevitable
- Verified Windows Defender/SmartScreen vendor reputation for the final EXE hashes
- Full source-to-binary reproducibility and qualified legal third-party review

These limitations are not erased by AI review. The release must remain an **unsigned prerelease** rather than a safety-certified general-purpose security product.

## Separate SignPath Foundation and signed-release gates (HOLD)

- [ ] SignPath formal project eligibility approval, including the three security-tool exceptions and acceptable component license requirements
- [ ] SignPath-recognized independently verifiable project reputation
- [ ] Approved real humans with MFA and per-request **manual** signing approval
- [ ] Branch protections, actual GitHub Origin Verification, protected environment, safe secrets and SignPath organization/project setup
- [ ] Real signed EXEs, pinned approved signer certificate, trustworthy timestamp, post-sign hash and provenance verification

**No signature certificate exists; the project's AI review does not satisfy or bypass these requirements.**

## RC5 experimental fork

A separate RC5 build using CPython 3.14/Tk 9 was evaluated on two Windows hosts, but the migration is **not merged into this PR** and has different dependency/license evidence. Do not substitute it for the RC4 release artifact.

## Historical records

Earlier rc1-specific requirements and test counts were superseded by [README.md](README.md), [release review evidence](signpath/REVIEW_KIT_ACCEPTANCE_20261111.md), [native third-party review](THIRD_PARTY.md) and [public Windows CI record](signpath/READINESS_20261108.md).
