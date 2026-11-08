"""Read PyInstaller CArchive TOCs from unsigned Windows executables.

This is an inventory only: entries are NOT extracted or executed. The report
cannot substitute for checking every embedded dependency's source and license.
"""
from __future__ import annotations

import json
from pathlib import Path
from PyInstaller.archive.readers import CArchiveReader

HERE = Path(__file__).resolve().parent
DIST = HERE / "dist"
STEMS = ("ResoArcSecretScout", "ResoArcLogLantern", "ResoArcFileInspector")


def main() -> None:
    results = []
    for stem in STEMS:
        path = DIST / (stem + ".exe")
        archive = CArchiveReader(str(path))
        names = sorted(archive.toc.keys())
        tkdnd_entries = [n for n in names if "tkdnd" in n.lower()]
        foreign = [
            n for n in tkdnd_entries
            if any(marker in n.lower() for marker in (
                "linux-", "osx-", "macos-", "win-x86", "win-arm64"
            ))
        ]
        results.append({
            "binary": path.name,
            "carchive_member_count": len(names),
            "tkdnd_members": tkdnd_entries,
            "foreign_platform_tkdnd_members": foreign,
        })
        print(
            f"FROZEN INVENTORY {path.name}: entries={len(names)}, "
            f"tkdnd={len(tkdnd_entries)}, cross-platform={len(foreign)}"
        )
        for n in tkdnd_entries:
            print("  TKDND: " + n)
    output = DIST / "FROZEN_CONTENTS_REVIEW.json"
    output.write_text(
        json.dumps({
            "status": "UNSIGNED_BUILD_REVIEW_ONLY",
            "description": "PyInstaller CArchive names; not full license approval",
            "applications": results,
        }, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("FROZEN INVENTORY REPORT: " + str(output))


if __name__ == "__main__":
    main()
