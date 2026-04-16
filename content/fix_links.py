#!/usr/bin/env python3
"""
Convert wikilinks that don't resolve by exact filename stem to pipe syntax.

For [[Some Title]] where "some title" doesn't match any filename stem exactly,
look it up in the aliases index and rewrite to [[filename-stem|Some Title]].

For [[Some Title|display]] pipe links where the target doesn't match a stem,
rewrite target to the correct stem: [[filename-stem|display]].

"Resolves by filename" means: target.lower() == stem.lower(). No
hyphen/space substitution — that's not how Obsidian works.
"""

import re
import yaml
from pathlib import Path

VAULT = Path(__file__).parent

# Exact stem index: lowercase stem → stem string
stem_index = {}
for md in VAULT.rglob("*.md"):
    if ".obsidian" in str(md):
        continue
    stem_index[md.stem.lower()] = md.stem

# Alias index: lowercase alias → stem string
alias_index = {}
for md in VAULT.rglob("*.md"):
    if ".obsidian" in str(md):
        continue
    text = md.read_text(encoding="utf-8")
    fm_match = re.match(r'^---\n(.*?)\n---', text, re.DOTALL)
    if fm_match:
        try:
            fm = yaml.safe_load(fm_match.group(1))
            if isinstance(fm, dict):
                for alias in fm.get("aliases", []) or []:
                    alias_index[str(alias).lower()] = md.stem
        except Exception:
            pass

SOURCE_EXTS = {'.c', '.h', '.md', '.py', '.json', '.qml', '.ld'}

def resolves_by_stem(target):
    return target.lower() in stem_index

def stem_for(target):
    """Return the file stem this target resolves to, or None."""
    if resolves_by_stem(target):
        return stem_index[target.lower()]
    return alias_index.get(target.lower())

# Match bare links [[target]] — no pipe, no #
BARE_LINK = re.compile(r'\[\[([^\]|#\n]+?)\]\]')
# Match pipe links [[target|display]] or [[target#section|display]]
PIPE_LINK = re.compile(r'\[\[([^\]|#\n]+?)(\|[^\]\n]+?)\]\]')

total_changed = 0

for md in sorted(VAULT.rglob("*.md")):
    if ".obsidian" in str(md):
        continue
    text = md.read_text(encoding="utf-8")
    original = text

    # Fix bare links: [[Some Title]] → [[some-title|Some Title]]
    def fix_bare(m):
        target = m.group(1).strip()
        if any(target.endswith(ext) for ext in SOURCE_EXTS):
            return m.group(0)
        if resolves_by_stem(target):
            return m.group(0)
        stem = alias_index.get(target.lower())
        if stem:
            return f"[[{stem}|{target}]]"
        return m.group(0)  # unknown — leave for audit

    text = BARE_LINK.sub(fix_bare, text)

    # Fix pipe links: [[Some Title|display]] → [[some-title|display]]
    def fix_pipe(m):
        target = m.group(1).strip()
        display = m.group(2)  # includes leading |
        if any(target.endswith(ext) for ext in SOURCE_EXTS):
            return m.group(0)
        if resolves_by_stem(target):
            return m.group(0)
        stem = alias_index.get(target.lower())
        if stem:
            return f"[[{stem}{display}]]"
        return m.group(0)

    text = PIPE_LINK.sub(fix_pipe, text)

    if text != original:
        md.write_text(text, encoding="utf-8")
        print(f"  FIXED {md.relative_to(VAULT)}")
        total_changed += 1

print(f"\nDone. Updated {total_changed} file(s).")
