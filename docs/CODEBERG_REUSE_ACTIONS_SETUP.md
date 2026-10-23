<!--
SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
SPDX-License-Identifier: MIT
-->
# Codeberg Actions activation / REUSE gate

**State as checked on 2026-10-23:** the public Codeberg repository API returns `has_actions: false`. The workflow file alone does not enable CI or supply a Runner.

1. Sign in as an authorized ResoArc administrator at `https://codeberg.org/ResoArc/resoarc-site/settings/units`.
2. In **Units > Overview**, enable **Repository Actions** and save.
3. Open **Settings > Actions > Runners**. Check whether a hosted runner matching `runs-on: codeberg-tiny` is available. Codeberg's hosted capacity is limited. Where unavailable, obtain a registration token and connect a separately isolated runner, or use Woodpecker CI.
4. Do **not** run arbitrary pull-request builds with elevated access to the production VPS, Cloudflare secrets, or the ResoArc signing key. Use a limited, dedicated container or VM; disable privileged Docker mounting for untrusted code.
5. Trigger `.forgejo/workflows/reuse-compliance.yml` manually, then confirm the displayed commit exactly equals the public Codeberg main SHA.
6. When it passes, keep the pull-request check required via branch protection (if supported by the current repository settings) and ensure the local `scripts/verify_site.py` fail-closed gate is used for direct Pages deploys too.
7. Evidence: action run ID / commit SHA / timestamp / success status; in case of failure preserve the failing file paths and corrective commit. Never present a historical success as the current main result.

Official guides: https://docs.codeberg.org/ci/actions/ and https://forgejo.codeberg.page/docs/latest/user/actions/overview/

Current local release gates:
- `python scripts/reuse_release_gate.py` : REUSE 3.3 metadata check.
- `python scripts/check_signed_archive_notice.py` : register/hash gate on published signed ZIP wrappers (not a cryptographic signature verification or redistribution rights determination).
- `python scripts/verify_site.py` : combines site integrity and both gates.

The only remaining account-side actions are enabling Actions and attaching a trusted Runner. Those cannot be performed using unauthenticated Git access.
