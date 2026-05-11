#!/usr/bin/env python3
"""
ClawShell Path Fix Script
Fixes path references in the codebase:
  1. ~/.openclaw -> ~/.real (migrate to Wukong runtime directory)
  2. C:\\Users\\* hardcoded -> dynamic path detection (cross-platform)

Usage:
  python3 fix_paths.py              # Scan and fix all files under .ClawShell/
  python3 fix_paths.py --dry-run    # Preview only, no actual modification
  python3 fix_paths.py --target <dir>  # Specify target directory
"""

import os
import re
from pathlib import Path

# Skip directories
SKIP_PATTERNS = {'.git', '__pycache__', '.pyc', '.venv', 'node_modules', '.pytest_cache'}

TEXT_EXTENSIONS = {'.py', '.sh', '.yaml', '.yml', '.json', '.md', '.txt', '.toml', '.cfg', '.ini'}


def should_skip_file(filepath):
    parts = set(filepath.parts)
    return bool(parts & SKIP_PATTERNS)


def fix_content(content, filepath):
    original = content
    modified = False
    changes = []

    # Fix 1: .openclaw -> .real (path references in strings)
    # Match ".openclaw" or '.openclaw' in path contexts
    count_openclaw = content.count('.openclaw')
    if count_openclaw > 0:
        # Only replace in string/path contexts, not variable names
        # Pattern: preceded by / or " or ' or space
        new_content = re.sub(
            r'(?<=["\'\s/])\.openclaw(?=["\'\s/])',
            '.real',
            content
        )
        if new_content != content:
            changes.append("  Path mapping: .openclaw -> .real")
            content = new_content
            modified = True

    # Fix 2: Hardcoded C:\\Users\\Aorus\\.ClawShell -> dynamic
    # Use simpler string replacement for known patterns
    replacements = [
        ('C:\\\\Users\\\\Aorus\\\\.ClawShell', 'os.environ.get("CLAWSHELL_ROOT", str(Path.home() / ".ClawShell"))'),
        ('C:\\Users\\Aorus\\.ClawShell', 'os.environ.get("CLAWSHELL_ROOT", str(Path.home() / ".ClawShell"))'),
    ]
    for old, new in replacements:
        if old in content:
            content = content.replace(old, new)
            changes.append("  Hardcoded path: C:\\Users\\Aorus\\.ClawShell -> dynamic")
            modified = True
            break

    return modified, content, changes


def process_file(filepath, dry_run=False):
    if should_skip_file(filepath):
        return False

    if filepath.suffix not in TEXT_EXTENSIONS:
        return False

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except (UnicodeDecodeError, IOError):
        return False

    modified, new_content, changes = fix_content(content, filepath)

    if modified and not dry_run:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)

    if modified:
        try:
            rel_path = filepath.relative_to(Path.cwd())
        except ValueError:
            rel_path = filepath
        print("  OK %s" % rel_path)
        for change in changes:
            print(change)
        return True

    return False


def scan_and_fix(root_dir, dry_run=False):
    fixed_files = []
    label = '[DRY RUN] ' if dry_run else ''
    print("\n%sScanning: %s" % (label, root_dir))

    for filepath in sorted(root_dir.rglob('*')):
        if filepath.is_file():
            if process_file(filepath, dry_run):
                fixed_files.append(filepath)

    return fixed_files


def main():
    import argparse
    parser = argparse.ArgumentParser(description="ClawShell Path Fix Script")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    parser.add_argument("--target", type=str, help="Target directory (default: ~/.ClawShell)")
    args = parser.parse_args()

    target = Path(args.target) if args.target else Path.home() / ".ClawShell"

    if not target.exists():
        print("ERROR: Target directory not found: %s" % target)
        return 1

    fixed = scan_and_fix(target, dry_run=args.dry_run)

    action = "would fix" if args.dry_run else "fixed"
    print("\n%s" % ('=' * 60))
    print("%s %d files" % (action, len(fixed)))

    return 0


if __name__ == "__main__":
    exit(main())
