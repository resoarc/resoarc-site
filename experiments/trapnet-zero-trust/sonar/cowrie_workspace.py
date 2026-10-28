#!/usr/bin/env python3
"""Read-only preflight for a disposable Cowrie writable workspace.

This module never starts a container, creates directories, touches operational
mounts, opens a socket, or changes production service configuration.
"""
from pathlib import Path

REQUIRED_RELATIVE = ("log/cowrie", "run", "lib/cowrie")

def assess_var_layout(base):
    root = Path(base)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Cowrie var must be a real directory")
    resolved = root.resolve(strict=True)
    absent = []
    invalid = []
    for relative in REQUIRED_RELATIVE:
        path = root
        for component in relative.split("/"):
            path = path / component
            if path.is_symlink():
                invalid.append(relative)
                break
        else:
            if not path.is_dir():
                absent.append(relative)
            elif not path.resolve(strict=True).is_relative_to(resolved):
                invalid.append(relative)
    return {"schema": "trapnet.cowrie-workspace-preflight.v1",
            "passed": not absent and not invalid,
            "missing_directory_classes": absent,
            "invalid_directory_classes": sorted(set(invalid)),
            "production_mounts_untouched": True,
            "ssh_handshake_proven": False,
            "network_isolation_proven": False}

if __name__ == "__main__":
    import argparse
    import json
    import sys
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-var", required=True)
    args = parser.parse_args()
    try:
        result = assess_var_layout(args.private_var)
        print(json.dumps(result, sort_keys=True))
        sys.exit(0 if result["passed"] else 3)
    except (OSError, ValueError) as e:
        print(json.dumps({"schema":"trapnet.cowrie-workspace-preflight.v1",
                          "passed":False,"error_class":type(e).__name__}))
        sys.exit(2)