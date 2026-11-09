# ResoArc authoritative codebases and mirrors

**Verified 2026-11-06.** Scope list for OSPS-QA-04.01. Mirror existence and synchronization are different claims.

| Purpose | Repository | Authority and scope |
| --- | --- | --- |
| **Canonical public source** | https://github.com/resoarc/resoarc-site | Main public codebase: website, Web8 tools, kintone plugins, verification scripts, and frozen ResoArcOS source archives |
| **Secondary Codeberg mirror** | https://codeberg.org/ResoArc/resoarc-site | Public mirror; latest-commit equality is **not confirmed** |

The public GitHub and Codeberg user repository APIs each returned **one** corresponding ResoArc repository on 2026-11-06. This does not prove there are no private or internal codebases.

**Subprojects kept inside the canonical repository:**
- `site/tools/` and `site/assets/tools/`: browser tools / Web8.
- `plugins/`: kintone plugin code and package manifests.
- `site/downloads/`: release archives and manifest evidence, pending safe move to external GitHub Release assets.
- ResoArcOS PC and Pi developer snapshots are presently source ZIP releases, not verified as independent public repositories.
- TrapNet development and operational VPS details are not included as a general-availability public release on the basis of this list.

Source-of-truth: `resoarc/resoarc-site`. A new official codebase, mirror or subproject requires updating this index and security-insights.yml. Do not publish personal/private forks or assume Codeberg synchronization.
