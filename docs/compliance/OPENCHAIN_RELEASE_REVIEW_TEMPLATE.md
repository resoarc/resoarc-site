# ResoArc OpenChain 5230: release review and evidence record

**TEMPLATE ONLY**. Copy into a release-specific record and enter *observed facts*, not imagined approvals.

| Field | Required evidence |
| --- | --- |
| Release ID and product name | |
| Scope and program revision | |
| Commit SHA / source tag | |
| Build and test run URL(s) | |
| Build and packaging procedure; toolchain | |
| Component inventory / SBOM document and SHA-256 | |
| Component origin, upstream copyright, versions | |
| Direct and transitive dependencies, declared licenses | |
| Source vs binary delivery and modified OSS | |
| License compatibility and attribution review | |
| Required full license texts / notices / offers | |
| Exact artifacts and SHA-256 | |
| Signed package signature verification (if relevant) | |
| Public distribution URL and live HEAD/GET verification | |
| Source code / corresponding build instructions link | |
| Compliance artifact archive location and retention | |
| Outstanding concerns and legal escalation | |
| Approving accountable person and decision time | |
| Decision | **HOLD / APPROVED** |

## Release gate

A release is **HOLD** if any actual distributed component or obligation is not identified, a full license is missing, there is an incompatible combination, third-party redistribution rights are unclear, a required notice/source offer is absent, the source and installation archive do not match, a signed package was modified without re-signing, or a legal escalation is unresolved.

Only the accountable human with validated evidence may mark `APPROVED`. An AI-generated checklist, passing CI, and this template are insufficient approvals.

## External license inquiry log (private, no identities in the public repo)

Record case ID, received time, affected component/release, assigned handler, initial reply, risk level, reproduction, applicable license, response, remedy, counsel consultation (if needed), communication and closeout evidence. Sensitive contact details stay in an access-controlled location.
