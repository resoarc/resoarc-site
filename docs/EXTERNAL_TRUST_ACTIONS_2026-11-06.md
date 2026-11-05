# ResoArc: External Trust & Recognition Action Register

**Reviewed:** 2026-11-06 (JST)  
**Owner:** ResoArc independent OSS project  
**Parent tracking issue:** [#6](https://github.com/resoarc/resoarc-site/issues/6)  
**Scope:** Public project-wide trust evidence and external community engagement. A project's registration, mailing-list subscription, machine score, self-assessment, or conformance statement must not be described as an independent security audit, safety guarantee, accreditation, sponsorship, or official endorsement.

## 1. Confirmed public technical evidence

| Evidence | Factual status | Claim boundary |
| --- | --- | --- |
| [FSFE REUSE report](https://api.reuse.software/info/github.com/resoarc/resoarc-site) | REUSE 3.3 compliant on the documented scan of the public repository | License metadata only, not product safety |
| [OpenSSF Scorecard](https://scorecard.dev/viewer/?uri=github.com/resoarc/resoarc-site) | Project has published machine-readable automated security evaluations; prior recorded score 5.8/10 on 2026-10-17 | Dynamic score, not a certification; recheck before posting a current numeric score |
| [OpenSSF Best Practices project #15597](https://www.bestpractices.dev/projects/15597/baseline-1) | Registration documented in [the existing assessment](OSPS_BASELINE1_15597_ASSESSMENT.md), with 0% and no badge at last recorded check (2026-10-17) | No Baseline Level 1 / Metal badge earned; current issuer state should be reverified before any new claim |
| [Software Heritage](https://archive.softwareheritage.org/) | Repository's recognition page contains archived source snapshot identifier | Archival record is not a code-quality endorsement |
| [SECURITY.md](../SECURITY.md) and [CONTRIBUTING.md](../CONTRIBUTING.md) | Public vulnerability-reporting and contribution processes | Publication does not prove operational response or an independent code review |

**Production caution:** GitHub source files and current public deployment can differ. Verify the deployed recognition page separately; do not infer a successful Cloudflare Direct Upload deployment from merged commits alone.

## 2. External organization correspondence: factual decision register

These are brief project-level summaries of private correspondence. Do **not** publish correspondent identities, private email excerpts, operator identity, or thread IDs.

| Program | Factual status | Decision / next step |
| --- | --- | --- |
| OpenChain ISO/IEC 5230 (Linux Foundation) | Support replied 2026-10-19: an unincorporated project may pursue project-named **self-certification**; private administrative contact can be kept out of public listing; self-certification and Community of Conformance listing have no fee. No conformance achieved or declared. | Start narrowly-scoped compliance process; complete every requirement before self-declaration. Asked follow-up on access to legal expertise and suitable small-project community channels 2026-11-06. |
| OpenChain Japan community | Mailing-list welcome confirmations received in October 2026 | Participate with real technical questions and documented practice, not an implication of OpenChain membership certification. |
| OSSAJ | Secretariat replied 2026-10-22: a multi-person unincorporated group can be eligible for supporting membership; fee is **JPY 120,000/year per unit**; the project name can be listed without representative name. No membership applied for or obtained. | **No paid application** without separate budget approval; keep low priority. Individual membership is a different category. |
| Tokyo Kodomo Smile Movement | Secretariat replied 2026-10-19: application may be possible with required organizational documents, private personal details, and **already implemented Tokyo child-related activities**. Not approved. | Create genuine relevant activity evidence first; do not claim participation now. |
| Japan OSS Promotion Forum | Eligibility, personal-information and application-form inquiry sent in October; no confirmed answer in checked correspondence | Sent **one follow-up on 2026-11-06** in the existing thread; await actual conditions before applying. |
| OSPN / Open Source Conference | OSS community exhibiting eligibility inquiry sent October; no confirmed response in checked correspondence | Followed up 2026-11-06 concerning 2027 Osaka community exhibit eligibility. No application, travel commitment, or paid sponsorship. |
| OSPN Press | Project introduction sent October; no confirmed selection/publication in checked correspondence | Await editorial decision; do not send duplicate unsolicited pitches. |
| OSHWA open-hardware certification | Eligibility/privacy inquiry sent October; no confirmed product certification | Prepare an actually reproducible open hardware design (sources, BOM, build instructions, licensing) before any certification. |
| IPA SECURITY ACTION | Public identity and eligibility concern | No application or claimed declaration; verify the public listing effect first. |

## 3. Outreach performed on 2026-11-06

Sent from the established ResoArc project mailbox in **existing threads**:

1. Japan OSS Promotion Forum: one polite eligibility/privacy/fees follow-up.
2. OSPN / OSC: 2027 Osaka community exhibitor eligibility, public project name and private administration question, expressly not a formal application.
3. OpenChain support: acknowledged its positive qualification reply; requested guidance for tiny-project access to license-law expertise and authentic community contributions.

All three sends returned a successful sent-message result. **Sending is not a received answer, invitation, approval, or accreditation.** Do not automate further reminders without a reasonable interval and a reply check.

## 4. Highest-leverage remediation before badges or conformance claims

### Priority A: OpenSSF Baseline 1 readiness

Track under [#24](https://github.com/resoarc/resoarc-site/issues/24) and [the detailed criterion draft](OSPS_BASELINE1_15597_ASSESSMENT.md):

- [ ] Validate **enforced** default branch protections/rulesets on `main`; no self-review or disabled rule may count as independent enforcement.
- [ ] Distribute full applicable license and third-party notices alongside each signed kintone plugin asset, **without altering signed ZIP contents** unless re-signed and verified.
- [ ] Migrate generated distributable ZIP artifacts out of versioned source only after preserving working download URLs, integrity hashes and user access.
- [ ] Review owner MFA, privileged collaborators, workflow secret isolation, dependency enumeration, source/archive evidence, and release provenance.
- [ ] Populate existing badge project **#15597** with truthful answers and issuer-confirmed metadata; leave uncertain items unknown or unmet until supported.
- [ ] Request independent, qualified human review when an actual external reviewer exists; **AI/self-controlled alt-account review is not independent**.

### Priority B: OpenChain ISO/IEC 5230 scoped preparation

- [ ] Define a narrow product/repository scope and identify accountable maintainer, license-approval role, escalation and operational continuity.
- [ ] Write and operate a real OSS license compliance policy, contribution/provenance process, SBOM/dependency inventory and third-party notices procedure.
- [ ] Document how competent legal advice can actually be obtained for license-obligation questions; **do not name a fictional attorney or team**.
- [ ] Collect executed release checks, training records, audit and remediation evidence over time.
- [ ] Answer official [OpenChain checklist](https://openchainproject.org/get-started) against tangible evidence. Declare self-conformance only after all requirements are met.

### Priority C: Credibility through real users and peers

- [ ] Publish accurate per-tool support status, reproducible tests, signed release provenance where verified, known limitations and incident/postmortem notes.
- [ ] Offer a practical kintone plugin write-up to the relevant developer community under permitted display-name rules; avoid portraying it as a Cybozu endorsement.
- [ ] Pursue genuine OSS community participation, including OSC exhibitors only if eligibility, staffing and costs are settled.
- [ ] Invite user feedback and actual independent code reviews; never manufacture endorsements, star counts, or testimonials.

## 5. Public communication rules

1. Explicitly label statuses as **compliant scan**, **machine assessment**, **registered / not awarded**, **inquiry**, **eligible**, **member**, **self-declared conformant**, or **independently audited**, as applicable.
2. Do not present a registration number, editor response, mailing-list welcome, or badge questionnaire as organizational certification.
3. The public activity name is **ResoArc**. Share operator identity or billing details only after an explicit privacy-impact decision.
4. Do not incur costs, claim awards, register formal membership, or submit a security conformance statement without verifying the real requirements and authority.
5. Keep this register as a *dated snapshot*, not a substitute for live issuer status.

## Source links

- [Master Issue #6](https://github.com/resoarc/resoarc-site/issues/6)
- [OpenSSF issue #24](https://github.com/resoarc/resoarc-site/issues/24)
- [OpenChain official get-started guide](https://openchainproject.org/get-started)
- [OpenSSF Best Practices official project](https://www.bestpractices.dev/projects/15597/baseline-1)
- [OSC schedule](https://ospn.jp/)
- [Cybozu developer community](https://community.cybozu.dev/)
