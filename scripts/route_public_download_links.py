# SPDX-FileCopyrightText: 2026 ResoArc
# SPDX-License-Identifier: MIT
"""Route public HTML product ZIP/ISO hyperlinks through counted Worker delivery.

Only href attributes directly linking official local resoarc*.zip/iso files are
changed. Source artifacts and their SHA256 remain byte-for-byte untouched.
Keep this script idempotent so regenerated catalog pages can be reprocessed.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
DOWNLOADS = SITE / "downloads"
URL = re.compile(r'href=(["\'])(/downloads/(resoarc[a-zA-Z0-9._-]+\.(?:zip|iso)))\1', re.I)


def main() -> None:
    changed_files = 0
    changed_links = 0
    skipped_missing = []
    for page in sorted(SITE.rglob("*.html")):
        before = page.read_text(encoding="utf-8")
        def replace(match: re.Match) -> str:
            nonlocal changed_links
            filename = match.group(3)
            if not (DOWNLOADS / filename).is_file():
                skipped_missing.append((str(page.relative_to(SITE)),filename))
                return match.group(0)
            changed_links += 1
            q = match.group(1)
            return f'href={q}/api/v1/downloads/file?asset={filename}{q}'
        after = URL.sub(replace,before)
        if after != before:
            page.write_text(after,encoding="utf-8",newline="\n")
            changed_files += 1
    print(f"COUNTED_DOWNLOAD_LINKS: pages={changed_files} links={changed_links}")
    print(f"UNSUPPORTED_STATIC_ASSETS: {len(skipped_missing)}")
    for page, filename in skipped_missing:
        print(f"  {page} : {filename}")
    if not changed_files and any(URL.search(p.read_text(encoding='utf-8')) for p in SITE.rglob('*.html')):
        raise RuntimeError("Expected links were not updated")

if __name__ == "__main__":
    main()
