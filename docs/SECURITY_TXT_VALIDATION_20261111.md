<!--
SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
SPDX-License-Identifier: MIT
-->

# RFC 9116 security.txt external validation — 2026-11-11 JST

**Result:** The actual production endpoint `https://resoarc.com/.well-known/security.txt` returned HTTP 200, and a third-party RFC 9116 validator at `https://securitytxts.com/api/validate` returned **`valid: true`**, **`errors: []`**, **`warnings: []`**, **`crawl_errors: []`** on 2026-11-11.

The validator received a URL-only public-data request using `POST /api/validate` with:
```json
{"url":"https://resoarc.com/.well-known/security.txt"}
```

Actual publicly retrieved security.txt fields:

```text
Contact: mailto:security@resoarc.com
Expires: 2027-04-18T00:00:00Z
Preferred-Languages: ja, en
Canonical: https://resoarc.com/.well-known/security.txt
Policy: https://resoarc.com/trust/#disclosure
```

Public proof links:
- [Live security.txt](https://resoarc.com/.well-known/security.txt)
- [Independent validator](https://securitytxts.com/) (interactive tool / API; a dated immutable public audit record is not supplied by the service)
- [RFC 9116](https://www.rfc-editor.org/rfc/rfc9116)

**What this means:** the published vulnerability-reporting contact metadata is syntactically valid according to the external checker at the tested point in time. There is **no security certification or warranty**. The check does not test that the email inbox receives messages, that the operator responds within a target interval, that the whole website is secure, or that the vulnerability disclosure workflow is effective.

**Follow-up:** perform a privacy-safe end-to-end mailbox receipt/acknowledgment test using the appropriate connected ResoArc mail account; record only timing and success, never private mail contents. Revalidate after changing Contact / Policy / Expires or deployment origin.
