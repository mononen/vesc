#!/usr/bin/env python3
"""
Add aliases: to every note's frontmatter so Obsidian wikilinks using
the human-readable title (e.g. [[ATR — Adaptive Terrain Response]])
resolve to the kebab-case file (atr.md).

Each note gets its frontmatter title as an alias, plus any extra aliases
listed in EXTRA_ALIASES for notes whose links appear under variant names.
"""

import re
import sys
from pathlib import Path

VAULT = Path(__file__).parent

# Extra aliases beyond the title, for notes linked under variant names.
EXTRA_ALIASES = {
    "atr.md":                     ["ATR"],
    "motor-data.md":              ["Motor Data"],
    "mahony-ahrs-filter.md":      ["Mahony Filter", "Mahony AHRS"],
    "pid-controller.md":          ["PID"],
    "traction-control.md":        ["Traction Control"],
    "foc-overview.md":            ["FOC", "Field Oriented Control"],
    "setpoint-composition.md":    ["Setpoint"],
    "bldc-mc-configuration.md":   ["BLDC mc_configuration", "mc_configuration"],
    "refloat-config.md":          ["RefloatConfig Reference"],
}

FM_RE = re.compile(r'^(---\n)(.*?)(\n---)', re.DOTALL)
TITLE_RE = re.compile(r'^title:\s*["\']?(.+?)["\']?\s*$', re.MULTILINE)
ALIASES_RE = re.compile(r'^aliases:.*?(?=\n\S|\Z)', re.MULTILINE | re.DOTALL)

patched = 0
skipped = 0

for md in sorted(VAULT.rglob("*.md")):
    if ".obsidian" in str(md) or md.name == "audit_links.py" or md.name == "add_aliases.py":
        continue

    text = md.read_text(encoding="utf-8")
    fm_match = FM_RE.match(text)
    if not fm_match:
        print(f"  SKIP (no frontmatter): {md.name}")
        skipped += 1
        continue

    fm_block = fm_match.group(2)

    # Extract title
    title_match = TITLE_RE.search(fm_block)
    if not title_match:
        print(f"  SKIP (no title): {md.name}")
        skipped += 1
        continue

    title = title_match.group(1).strip()

    # Build alias list: title + any extras
    extras = EXTRA_ALIASES.get(md.name, [])
    all_aliases = [title] + extras

    # Check if aliases already present
    if "aliases:" in fm_block:
        # Already has aliases — skip to avoid duplicating
        print(f"  SKIP (aliases exist): {md.name}")
        skipped += 1
        continue

    # Build YAML aliases block
    alias_lines = "\n".join(f'  - "{a}"' for a in all_aliases)
    aliases_yaml = f"aliases:\n{alias_lines}"

    # Insert aliases after title line
    new_fm = TITLE_RE.sub(
        lambda m: m.group(0) + "\n" + aliases_yaml,
        fm_block,
        count=1
    )

    new_text = text[:fm_match.start(2)] + new_fm + text[fm_match.end(2):]
    md.write_text(new_text, encoding="utf-8")
    print(f"  PATCH: {md.relative_to(VAULT)}  aliases={all_aliases}")
    patched += 1

print(f"\nDone. Patched {patched} files, skipped {skipped}.")
