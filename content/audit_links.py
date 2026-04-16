#!/usr/bin/env python3
"""
Audit Obsidian wikilinks across all .md files in this vault.

A link [[Foo]] resolves ONLY if there is a note whose filename stem matches
exactly (case-insensitive). No hyphen/space substitution — Obsidian does not
do this automatically. Use [[filename|Display Text]] pipe syntax for links
where the display text differs from the filename.
"""

import re
import sys
from pathlib import Path

VAULT = Path(__file__).parent

# Build index: exact lowercase stem → Path
index = {}
for md in VAULT.rglob("*.md"):
    if ".obsidian" in str(md):
        continue
    index[md.stem.lower()] = md

# Matches wikilinks; group 1 = target (before | or #)
WIKILINK = re.compile(r'\[\[([^\]|#\n]+?)(?:[|#][^\]\n]*)?\]\]')
SOURCE_EXTS = {'.c', '.h', '.md', '.py', '.json', '.qml', '.ld'}

broken = []

for md in sorted(VAULT.rglob("*.md")):
    if ".obsidian" in str(md):
        continue
    text = md.read_text(encoding="utf-8")
    for lineno, line in enumerate(text.splitlines(), 1):
        for m in WIKILINK.finditer(line):
            target = m.group(1).strip()
            if any(target.endswith(ext) for ext in SOURCE_EXTS):
                continue
            if target.lower() in index:
                continue
            broken.append((str(md.relative_to(VAULT)), lineno, target))

if not broken:
    print("✓ All wikilinks resolve.")
    sys.exit(0)

print(f"Found {len(broken)} broken wikilink(s):\n")
by_file = {}
for (path, lineno, target) in broken:
    by_file.setdefault(path, []).append((lineno, target))
for path in sorted(by_file):
    print(f"  {path}")
    for lineno, target in by_file[path]:
        print(f"    line {lineno:>4}: [[{target}]]")
    print()

unique = sorted(set(t for _, _, t in broken))
print(f"Unique missing targets ({len(unique)}):")
for t in unique:
    print(f"  [[{t}]]")
