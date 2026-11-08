# SignPath Foundation: eligibility review and application material

## Project summary (English, factual)

**Project:** ResoArc Security Trio  
**Source:** https://github.com/resoarc/resoarc-site/tree/main/apps/security-trio (available after PR merge)  
**Existing unsigned public preview:** https://resoarc-security-trio.pages.dev/  
**License:** MIT (original ResoArc code); third-party runtime licenses documented separately  
**Version:** 0.3.0-rc4, unsigned preview  
**Distribution:** Windows x64 standalone EXEs built from Python source with PyInstaller

This open-source project provides three offline, read-only **static triage** tools:

1. **Secret Scout** inspects source files and archives that developers explicitly select for accidental credential exposure. It never sends or reveals matched credentials; its core use case is scanning software artifacts during development/testing.
2. **Log Lantern** examines existing Apache/Nginx/IIS access logs that the operator explicitly selects. It reports **traces of potential security incidents**. It does not contact or scan other hosts, discover network services, test open ports, or exploit systems.
3. **File Inspector** reads local attachments without executing them. It reports deceptive file formats and possible traces of malicious files. It is not a vulnerability scanner or antivirus product.

All tools are read-only toward input files. There is no built-in upload of user scans, scanning of network ports, credential harvesting, exploit payload generation, or disabling of security controls. Reports are stored only to user-selected local paths.

**Eligibility concern:** SignPath Foundation's *No hacking tools* condition excludes certain security diagnosis utilities while exempting software-artifact scanning during development/testing and detecting traces of actual security incidents. Please determine explicitly whether each of these three tools is eligible before requesting or issuing a Foundation certificate. If some are ineligible, we will not attempt to sign them through the Foundation.

## Requirements and evidence checklist

| Criterion | Status | Evidence / action |
| --- | --- | --- |
| Owner-controlled public source | In PR | GitHub source directory `apps/security-trio/` |
| OSI-approved license | Source MIT | Third-party bundling inventory review pending |
| Already released as unsigned software | Yes | Dedicated preview website |
| User documentation | Yes | Preview site, README |
| No malware / unauthorized behavior | Automated tests; independent review pending | SECURITY.md, QA report |
| CI build from exact source | Proposed in PR | GitHub Actions unsigned workflow |
| Release branch rules / SCM review | Not configured | Require real human reviewer, protected branches, MFA |
| SignPath project and approved policy | Not configured | Foundation approval required |
| Every signing request manually approved | Policy prepared | SignPath approval roles not yet assigned |
| Product/version/filename metadata | Prepared | Requires new Windows CI build |
| Download/release Code signing policy link | Source documentation prepared | Preview website link not yet published |
| Signed artifact validation | Test script prepared | No actual certificate or signed binaries |
| Independent security review | Not completed | Required before general signed release |
| OSS-program eligibility verdict | Unknown | Request Foundation determination |

## Application fields still requiring the operator

- Official maintainer contact email (use project contact address, never publish personal secrets).
- The actual authorized ResoArc maintainer(s) responsible for code review and per-release manual approval.
- MFA confirmation for GitHub and SignPath.
- Human confirmation of policy acceptance.
- SignPath service / organization account and security review outcome.

Do not put credentials, personal identity documents, user tokens, or private logs into public GitHub issues.

## Request for eligibility guidance (draft)

**Subject:** SignPath Foundation OSS eligibility inquiry: ResoArc Security Trio

Hello SignPath Foundation team,

We maintain the ResoArc Security Trio open-source project, a set of three offline, read-only Windows utilities (MIT-licensed source) distributed as an unsigned development preview.

Before applying for the Foundation certificate, we would appreciate confirmation regarding the “No hacking tools” clause. Secret Scout scans source and configuration artifacts for accidental credential disclosure during development. Log Lantern analyzes existing web access logs for potential traces of incidents. File Inspector performs static inspection of locally selected attachments without executing them. None of the three tools scans live networks, discovers exploitable ports, or attempts exploitation.

Would these functions be eligible under the artifact-scanning or security-breach-trace exceptions? If eligibility differs between the three applications, please let us know.

Source repository (after code-review merge): https://github.com/resoarc/resoarc-site/tree/main/apps/security-trio
Unsigned preview: https://resoarc-security-trio.pages.dev/

We understand that acceptance and certificate issuance are at the Foundation’s discretion and that all releases must be built via a verified trusted pipeline and manually approved.

Regards,
ResoArc maintainers

## References

- https://signpath.org/terms
- https://signpath.org/apply
- https://docs.signpath.io/trusted-build-systems/github
- https://docs.signpath.io/artifact-configuration/examples
