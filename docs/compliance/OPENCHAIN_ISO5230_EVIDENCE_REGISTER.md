# OpenChain ISO/IEC 5230:2020 evidence register | ResoArc (2026-11-06)

**Formal conformity status: NOT READY. No self-declaration submitted.**
This tracker describes the narrowly scoped program in [OPENCHAIN_ISO5230_PROGRAM.md](OPENCHAIN_ISO5230_PROGRAM.md) for the two browser utilities only. It does not cover other ResoArc products.

Official checklist: https://openchainproject.org/licensecompliancespecification
Independent clause-level implementation guide: https://openchain-project.github.io/OpenChain-KWG/en/guide/iso5230_guide/
Local release record form: [OPENCHAIN_RELEASE_REVIEW_TEMPLATE.md](OPENCHAIN_RELEASE_REVIEW_TEMPLATE.md)

A documented policy is **not evidence of execution**. Only mark **VERIFIED** after a dated real release case, qualified reviewer and associated records exist.

| Clause | What must be demonstrated | Evidence available | Status / actual gap |
| --- | --- | --- | --- |
| §3.1.1 Policy | Document policy and distribution to participants | Draft program policy | **PARTIAL**: maintainer approval, communication and acknowledgments missing |
| §3.1.2 Competence | Defined roles and tested competencies of actual participants | Role descriptions and competency criteria | **PARTIAL**: individual assignment, training and assessment records missing |
| §3.1.3 Awareness | Participant awareness of policy, objectives, contributions and consequences | Public draft | **NOT VERIFIED**: no dated awareness record |
| §3.1.4 Program scope | Maintain precise, defensible scope | Two utility pages and delivered assets scoped in program | **PARTIAL**: formal owner signoff and observed source-to-live mapping missing |
| §3.1.5 License obligations | Procedure to identify rights, obligations and restrictions | Draft component review procedure, REUSE metadata | **PARTIAL**: actual review decisions for all shipped assets missing |
| §3.2.1 External inquiries | Public license-compliance intake and operational response | `SECURITY.md` private email; proposed inquiry workflow | **PARTIAL**: case tracking, accessible distinct license contact instructions and test case missing |
| §3.2.2 Resourcing/legal expertise | Roles properly staffed, resources provided, access to actual legal expertise | Role descriptions | **NOT VERIFIED**: resources/assigned people/legal support not evidenced |
| §3.3.1 Component inventory | Identify, track, approve, archive components of each release | [initial component inventory](OPENCHAIN_BROWSER_TOOLS_COMPONENTS.md) | **PARTIAL**: validated SBOM/version hashes/approvals missing |
| §3.3.2 Compliance review | Source and binary deliveries, modified OSS, incompatible and attribution cases | Policy flow, sample archive audit | **PARTIAL**: actual complete review not evidenced |
| §3.4.1 Artifacts and retention | Prepare and deliver required licenses, source offers and archive evidence | License files, review template, planned retention | **PARTIAL**: delivery and restoration evidence missing |
| §3.5.1 Community contributions | Publication and onboarding of contributor rights policy | `CONTRIBUTING.md`, policy procedure | **PARTIAL**: participant communication/acknowledgment missing |
| §3.6.1 Affirmation | Dated approval that **all** requirements are met | None | **UNMET**: do not self-declare |
| §3.6.2 Validity review | Review conformance at least every 18 months | Schedule requirement written | **PARTIAL**: owner acceptance, initial actual review and follow-up mechanism missing |

## Concrete next executions

1. Confirm owner and all contributors of the scoped program, keep non-public identifying evidence private, record 2FA/competence training/awareness acknowledgments with dates.
2. Produce a verified inventory / SPDX or CycloneDX SBOM for the exact two rendered tool pages and their delivered static files (including fonts and photo rights); record exact revision and source provenance.
3. Carry out one complete reviewed release with evidence that corresponding source, LICENSE, third-party notices, any source offers and served URLs match what end users actually receive. Retain SHA hashes and approval/retention records.
4. Designate actual competent legal escalation (not AI alone), document how inquiries are handled and test the response process without exposing contact data.
5. Complete every official checklist answer with supporting records; run an independent sanity review if available; execute a dated scope-specific affirmation **only after all criteria are true**.
6. Ask the official OpenChain contact to confirm any program-specific uncertainties, but do not treat their advice as approval or certification.

**Decision:** HOLD; self-certification and Community of Conformance submission prohibited until the register is entirely verified.
