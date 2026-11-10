# ResoArc Open Source License Compliance Program (ISO/IEC 5230:2020 preparation)

**Status:** OPERATING PROCEDURE PROPOSED / NOT YET CONFORMANT
**Created:** 2026-11-06 JST
**Document owner:** ResoArc public maintainer account; the accountable human must acknowledge this procedure before first audited release.
**Normative references:** [OpenChain official checklist](https://openchainproject.org/licensecompliancespecification), [OpenChain reference material](https://github.com/OpenChain-Project/Reference-Material), [ISO/IEC 5230 conformance guide](https://openchain-project.github.io/OpenChain-KWG/en/guide/iso5230_guide/).

## 1. Purpose and strict scope

This program governs open source licensing, third-party attribution and accompanying artifacts for the following **initial narrow scope**, not for the whole ResoArc organization:

- Browser-only utilities implemented by `site/assets/tools/hash.js` and `site/assets/tools/csv.js`, their corresponding public tool pages and any specifically identified source release.
- The first-party HTML pages at `site/tools/hash/index.html` and `site/tools/csv/index.html`, plus their directly delivered assets: shared stylesheets, JavaScript, first-party SVG icons/screenshots, `site/assets/fonts/noto-serif-jp-v10.woff2` (OFL-1.1), and the referenced Unsplash hero image (separately licensed) where applicable. The source tree, build/runtime dependencies, user documentation and distribution metadata are in scope for these pages. Their rights must be inventoried and reviewed before conformance.
- The exact public repository is `resoarc/resoarc-site`; third-party rights remain subject to each rights holder's license.

**Out of scope pending separate review:** every signed kintone plugin ZIP, the remaining Web8 tools, ResoArcOS, TrapNet, unrelated pages/assets and other experimental releases. Third-party assets *actually used by the two in-scope tool pages remain in scope*. This is not an assertion that out-of-scope software is compliant. The separate ResoArc-wide OSPS Baseline work may cover a wider repository. Scope expansion requires an explicit change record, component inventory, release-by-release evidence and approval.

This document establishes a procedure. **Its existence alone does not demonstrate the procedure is in use**, staffed, funded, reviewed or self-certified. Do not submit OpenChain conformance while evidence items in the companion register remain unresolved.

## 2. Policy and responsibilities (ISO/IEC 5230 §3.1)

- Publish only components for which copyright, authorship, permissions, licenses and downstream redistribution obligations are understood and documented.
- Inspect direct and transitive dependencies, code copied from examples, assets, AI-assisted contributions and generated code before incorporation. No proprietary/restricted code may be silently relabeled MIT.
- Maintain the actual copyright notices, SPDX markers and relevant full license texts. When a component's obligations are uncertain, the release is **HOLD** until resolved with competent legal advice or the component is removed.
- Program functions: **maintainer/program owner** (decides scope and resources), **release steward** (performs inventory and release gate), **license reviewer** (resolves obligations), **inquiry coordinator** (handles external reports). In a one-person project these functions may be carried by one person, but independence must never be claimed; name, available time, resources and backup plan must be recorded privately.
- Competence required: read and distinguish common OSS license obligations and exceptions, inspect source and binary archives, maintain SPDX/SBOM data, perform reproducible release checks, recognize when to escalate for professional legal guidance.
- Identify an *actual* lawful source of competent legal advice before marking §3.2.2 fulfilled. An unanswered inquiry to OpenChain or an AI answer is **not** an engaged legal expert.
- Communicate the policy to each participant by linking this page in onboarding and requiring a dated acknowledgment (private record allowed). At least annually and on major policy changes, re-confirm awareness, training, assigned roles and consequences of noncompliant release.

## 3. Component identification, license assessment and approval (§3.1.5 / §3.3)

For each new source, package, graphic, snippet or dependency:

1. Record the source origin URL and revision, copyright owner, SPDX expression, direct dependency versions, use and redistribution role in the inventory. Generate an SBOM (SPDX or CycloneDX) when applicable.
2. Compare license conditions against the intended combination and distribution: source vs. binaries; dynamic/static linking; modifications; reciprocal/copyleft, attribution, patent and source-offer obligations; license incompatibilities; and nested dependencies.
3. Document the exact approved version, compatibility result, obligations, credits and required full license texts. Obtain competent legal review if obligations cannot be reasonably assessed.
4. Approve or hold with the accountable release steward; the release evidence must include the approving reviewer, time, SHA of source and decision.
5. When shipping changes to third-party OSS, preserve change notices and source availability obligations. Never overwrite an externally signed archive solely to insert a license; create a separately verifiable distribution wrapper or a clearly linked license sidecar as appropriate to the actual user download flow.
6. Reject unverifiable provenance, unresolved license incompatibility, or any asset with an unknown redistribution right.

**Initial audit:** the existing root `LICENSE`, `THIRD_PARTY_NOTICES.md`, `LICENSES/`, `REUSE.toml`, GitHub release assets and product-specific archives are inputs. A successful REUSE metadata scan is *supporting evidence*, not a substitute for package-by-package legal analysis.

## 4. Review of supplied software and compliance artifacts (§3.3 / §3.4)

Before any release in scope, the release steward must:

- Freeze the source revision and enumerate every file, direct dependency and transitive component where knowable.
- Inspect actual installable/binary and source archives, include appropriate copyright notices, license texts, notices, modifications, source offers and build instructions.
- Preserve signed package signatures; hash all release assets (SHA-256). A sidecar file does **not** prove the user received it; verify that each published download page directly exposes the specific license / notice link, or distribute a source/wrapper bundle.
- Ensure a project source URL and matching reproducible source revision are listed. Block release on missing mandatory artifacts, unknown component provenance or unresolved license restrictions.
- Archive the review log, source SHA, SBOM/dependency manifest, approved license matrix, published artifact checksums, compliance documents, approval and distribution URL, along with evidence that the URLs really served those files.
- Retain evidence through at least the later of the last offered distribution date and any longer period specified by the applicable license; retain adequate backup/restore procedures. Never promise a fixed deletion date that would violate a license.

This applies to web-served code as well as downloadable files. The website must expose notices applicable to assets actually delivered to users.

## 5. Inquiries and noncompliance (§3.2)

- **Public intake:** the project's documented contact `github@resoarc.com` and ordinary public GitHub Issues for non-sensitive questions; confidential reports must go through private email.
- Acknowledge an inquiry within **7 calendar days as a target**, not a contractual SLA. Record case ID, intake time, affected component/version, contact, alleged obligation and assigned role in a private log.
- Triage and reproduce the report, inspect the license and provenance, decide whether affected releases must be withheld, and communicate a factual remediation plan to the reporter. Do not publish private identities or confidential details in Issue comments.
- Correct missing notices, offer required source, replace incompatible dependencies, re-sign or re-release when necessary. Validate published links and record closure evidence. Escalate uncertain obligations to actual qualified legal expertise; pending escalation stays HOLD.
- Maintain a record of every rejected or exception-based contribution and resulting corrective action.

## 6. Community contributions (§3.5)

All source contributions follow `CONTRIBUTING.md`. Contributors must have rights to offer submitted code under its declared license; carry origin and any dependency notices; disclose modified third-party code; avoid private keys/personal information; and allow maintainers to perform a license review before merge. Public contributor discussion does **not** imply independent review.

## 7. Operations, evidence and conformance gate (§3.6)

- Each release in scope gets a completed copy of `OPENCHAIN_RELEASE_REVIEW_TEMPLATE.md` with an actual timestamp, revision, sources, artifacts, compliance decisions, qualified reviewer and evidence links.
- Each participant's competence and policy awareness must be assessed and dated; resources, legal escalation contact and continuity must actually exist.
- Maintain a separate evidence register and the precise mapping to each of the questions in the [official self-certification checklist](https://openchainproject.org/licensecompliancespecification).
- An authorized maintainer may self-declare conformity **only if every applicable question is supported by evidence, no open blocker remains, and a signed-off dated affirmation for this exact scope and ISO/IEC 5230:2020 is completed**. Do not use a public OpenChain certification mark or Community of Conformance claim before the applicable program steps are truthfully completed.
- Re-review the process and conformance claim no later than every **18 months**, and whenever scope, standard, material dependencies or team roles change.

## First action log (2026-11-06)

- Public baseline investigation: 20 tracked download ZIPs were inspected by filenames and entry listings; 11 signed installable kintone packages lacked an embedded `LICENSE` or `NOTICE`, while 9 source archives did contain a `LICENSE` entry. This does **not** prove rights compliance of any archive.
- A first-party MIT license and a limited notice index are being prepared alongside downloads without modifying signed packages.
- OpenChain support previously confirmed that a non-incorporated ResoArc project may pursue a **narrowly scoped self-certification**, with operator personal identity kept out of the public listing. Qualification advice is not approval.
- Program owner participation, legal expertise, awareness training, full component review and actual end-to-end release operations are **not established** by these documents. Initial disposition: **NOT READY TO SELF-CERTIFY**.
