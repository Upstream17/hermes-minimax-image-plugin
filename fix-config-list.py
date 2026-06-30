#!/usr/bin/env python3
"""Fix the `hermes config set` list-as-string malformation.

After running:
    hermes config set plugins.enabled '["minimax"]'

The config file ends up with:
    plugins:
      enabled: '["minimax"]'   # string, not list — Hermes skips the plugin

This script reads the config, finds the malformed list line, and rewrites it as
a proper YAML list. Idempotent: safe to run multiple times.

Usage:
    python fix-config-list.py
    python fix-config-list.py --path /custom/path/to/config.yaml
"""
import argparse
import os
import sys
from pathlib import Path


DEFAULT_PATHS = [
    Path(os.environ.get("HERMES_HOME", "")) / "config.yaml" if os.environ.get("HERMES_HOME") else None,
    Path.home() / ".hermes" / "config.yaml",
    Path(os.environ.get("LOCALAPPDATA", "")) / "hermes" / "config.yaml" if os.environ.get("LOCALAPPDATA") else None,
    Path("/mnt/c/Users") / os.environ.get("USER", "Administrator") / "AppData" / "Local" / "hermes" / "config.yaml"
        if os.environ.get("USER") else None,
]


def find_config(explicit: str | None) -> Path:
    if explicit:
        p = Path(explicit)
        if not p.exists():
            sys.exit(f"ERROR: {p} does not exist")
        return p
    for candidate in DEFAULT_PATHS:
        if candidate and candidate.exists():
            return candidate
    sys.exit("ERROR: could not find config.yaml. Pass --path explicitly.")


def fix(text: str) -> tuple[str, int]:
    """Replace any stringified JSON-array list value with a real YAML list.

    Returns (new_text, replacements_made).
    """
    import re

    count = 0
    # Match patterns like:
    #   plugins:
    #     enabled: '["minimax"]'
    # and rewrite as:
    #   plugins:
    #     enabled:
    #     - minimax
    #
    # The pattern: a non-indented or indented key line "<parent>:" followed by
    # a deeper-indented "<child>:" whose value is a quoted JSON array string.
    # Two named groups: parent (group 1) and child (group 2).
    pattern = re.compile(
        r"^(\s*)([\w.-]+):[ \t]*\n\s+([\w.-]+):[ \t]*'\[([^\]]*)\]'\s*\n",
        re.MULTILINE,
    )

    def repl(m: re.Match) -> str:
        nonlocal count
        parent_indent, parent_key, child_key, items_json = (
            m.group(1), m.group(2), m.group(3), m.group(4)
        )
        # Parse the items: simple, unquoted
        items = [s.strip().strip('"').strip("'") for s in items_json.split(",")]
        items = [i for i in items if i]  # drop empties
        child_indent = parent_indent + "  "
        out = [f"{parent_indent}{parent_key}:\n", f"{child_indent}{child_key}:\n"]
        for it in items:
            out.append(f"{child_indent}- {it}\n")
        count += 1
        return "".join(out)

    new_text = pattern.sub(repl, text)
    return new_text, count


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--path", help="Explicit path to config.yaml (auto-detected by default)")
    ap.add_argument("--dry-run", action="store_true", help="Print what would change without writing")
    args = ap.parse_args()

    cfg = find_config(args.path)
    original = cfg.read_text(encoding="utf-8")
    new, count = fix(original)

    if count == 0:
        print(f"OK: {cfg}")
        print("No stringified-list malformations found. Nothing to fix.")
        return 0

    print(f"Found {count} stringified-list value(s) in {cfg}:")
    if args.dry_run:
        # Show a diff preview
        import difflib
        diff = list(difflib.unified_diff(
            original.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile="before",
            tofile="after",
            n=2,
        ))
        sys.stdout.writelines(diff)
        print("\n(dry-run: not writing)")
        return 0

    cfg.write_text(new, encoding="utf-8")
    print(f"Fixed {count} value(s) in {cfg}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
