# Recognition verification and next actions (2026-10-17 JST)

Scope: ResoArc / resoarc.com. Do not list program participation, certification, or badges unless verified by source.

## Confirmed and deployed
- Green Web Foundation: official API `https://api.thegreenwebfoundation.org/api/v3/greencheck/resoarc.com` -> `green: true`, host Cloudflare. Official PNG badge mirrored under `site/assets/recognition/`. This is hoster verification, not zero site-specific emissions.
- Qualys SSL Labs: `https://api.ssllabs.com/api/v3/analyze?host=resoarc.com&fromCache=on&maxAge=24` returned READY with four IPv4/IPv6 endpoint grades A+. It tests publicly served TLS, not plugin source security.
- Internet.nl: official test permalink `https://internet.nl/site/resoarc.com/4355764/` -> 73% on 2026-10-17. IPv6 and RPKI pass. DNSSEC, HSTS and some TLS properties need improvement. **No 100% badge.**
- Published: TOP recognition cards, recognition detail cards, release history. Six Web-quality cards laid out as 3 x 2 on wide viewports.
- Security improvements: `/.well-known/security.txt` (uses existing project disclosure contact) and staged `Strict-Transport-Security: max-age=300`. Do not advertise Internet.nl 100% until it is legitimately earned and listed.

## Not yet attained; blockers and actions
1. Internet.nl 100%: enable DNSSEC with domain registrar and configure DS correctly; investigate Cloudflare TLS cipher findings; safely ramp HSTS from 300 seconds through staged intervals toward >= 31536000 only once HTTPS for the domain is stable. Verify security.txt reachable and re-run official site test. Do not use 100% logo before Hall of Fame.
2. PageSpeed Insights: API responded HTTP 429 quota exceeded. Retry a public test when quota allows; publish dated scores only if results are independently retrievable, not a Google certification.
3. OpenSSF Best Practices project #15597: `https://www.bestpractices.dev/projects/15597.json` officially reports badge_level=in_progress, baseline Level 1 = 17%, achieved_baseline_1_at=null and achieved_passing_at=null. Project access/ownership must be verified before submitting accurate evidence-backed questionnaire responses. Review the current official criteria and address all unknown/unmet controls. No Passing/Baseline emblem now.
4. SonarQube Cloud, Codacy, Codecov: public-project onboarding and repository-linked verification depend on a usable GitHub ResoArc org/repository. ResoArc GitHub currently unavailable. Do not imply projects are scanned or gates passed. After reinstatement link official repository using its organization owner, configure test/coverage pipeline, and then add only real status badges.
5. OpenChain ISO/IEC 5230 / ISO/IEC 18974: public mailing-list activity is not formal conformance. Need demonstrated license-management/security processes, accountability, recordkeeping, education, handling of third-party components and an accurate self-conformance declaration before using any conformance mark. No self-declaration made.
6. CHAOSS: participation and corresponding logo require actual verified involvement; no evidence of completed membership/working-group activity in this inspection, so no affiliation claim.

## Release constraints
- Cloudflare Pages project `resoarc` is Direct Upload; GitHub pushes do not publish. Deploy only verified canonical `site/` and confirm live apex.
- Snapshot of current public pages was reconciled before editing to avoid overwriting later TOP recognition layout.
- The official public GitHub repository has not recovered, so there is no claimed successful upstream push.
- Keep disclosure contact details within project identity; do not expose operator's private identity.
