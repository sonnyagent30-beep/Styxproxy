#!/usr/bin/env python3
"""Sprint 1b — light-mode contrast sweep. Idempotent-ish, asserts counts."""
import re, pathlib, sys

ROOT = pathlib.Path('.')
changed = {}
def log(f, n, what):
    changed.setdefault(str(f), []).append(f"{n}x {what}")

def sub(path, old, new, expect=None, what=''):
    p = pathlib.Path(path)
    t = p.read_text()
    n = t.count(old)
    if expect is not None and n != expect:
        print(f"!! ABORT {path}: expected {expect} of {old!r}, found {n}")
        sys.exit(1)
    if n == 0:
        print(f"   (skip) {path}: no {old!r}")
        return
    p.write_text(t.replace(old, new))
    log(path, n, what or f"{old} -> {new}")

# ── 1. globals.css: token definitions ────────────────────────────────────
css = pathlib.Path('src/app/globals.css')
t = css.read_text()

# 1a. dark values in :root (add --primary-text next to --primary).
# Both :root and :root.dark carry the identical 3-line trio, so disambiguate by index.
old_trio = '  --primary: #0AD25A;\n  --primary-dark: #059669;'
assert t.count(old_trio) == 2, t.count(old_trio)
new_trio = ('  --primary: #0AD25A;\n  --primary-dark: #059669;\n'
    '  /* --primary is a FILL (buttons, dots, bars) and is paired with black\n'
    '     text — #0AD25A gives 10.38:1. It is NOT safe as a text colour on the\n'
    '     light page (#0AD25A on #fafafa = 1.94:1), so text uses --primary-text. */\n'
    '  --primary-text: #0AD25A;')
# first occurrence = :root (base/dark defaults)
t = t.replace(old_trio, new_trio, 1)

# 1b. light blocks: brighten --primary, darken the hover step, add --primary-text
def patch_light_block(text, start_marker):
    i = text.index(start_marker)
    j = text.index('}', i)
    block = text[i:j]
    assert '  --primary: #0b7a34;' in block, start_marker
    block = block.replace('  --primary: #0b7a34;',
        '  /* Bright brand green as the FILL. Every CTA is bg-[var(--primary)]\n'
        '     text-black and 109 fills + 11 globals.css rules all pair it with\n'
        '     #000, so this keeps the brand colour and passes at 10.38:1.\n'
        '     The darkened #0b7a34 it replaces was a mistake: it diluted the\n'
        '     brand and dropped those buttons to 3.85:1. */\n'
        '  --primary: #0AD25A;')
    block = block.replace('  --primary-dark: #095c27;',
        '  /* Hover step: must stay dark enough for the black button label.\n'
        '     #095c27 was only 2.57:1 — a hover state that fails worse than rest. */\n'
        '  --primary-dark: #09b84f;')
    block = block.replace('  --primary-light: #0AD25A;',
        '  --primary-light: #22FF7A;\n  --primary-text: #0b7a34;')
    return text[:i] + block + text[j:]

t = patch_light_block(t, '@media (prefers-color-scheme: light) {')
t = patch_light_block(t, ':root.light {')

# 1c. :root.dark — explicit admin override needs the token too
i = t.index(':root.dark {')
j = t.index('}', i)
blk = t[i:j]
assert '  --primary: #0AD25A;' in blk
blk = blk.replace('  --primary: #0AD25A;', '  --primary: #0AD25A;\n  --primary-text: #0AD25A;', 1)
t = t[:i] + blk + t[j:]

# 1d. the 20 text-colour rules in globals.css
n = len(re.findall(r'^(\s*)color:\s*var\(--primary\)\s*;', t, re.M))
assert n == 20, n
t = re.sub(r'^(\s*)color:\s*var\(--primary\)\s*;', r'\1color: var(--primary-text);', t, flags=re.M)
log('src/app/globals.css', 20, 'color: var(--primary) -> var(--primary-text)')
css.write_text(t)
log('src/app/globals.css', 1, 'added --primary-text + brightened --primary in 2 light blocks')

# ── 2. TSX sweeps ────────────────────────────────────────────────────────
def walk(*dirs):
    for d in dirs:
        for p in pathlib.Path(d).rglob('*.tsx'):
            if p.suffix == '.bak' or '.bak' in p.name:
                continue
            yield p

# 2a. text-[var(--primary)] -> text-[var(--primary-text)]  (public + components only)
total = 0
for p in walk('src/app/(public)', 'src/components'):
    txt = p.read_text()
    n = txt.count('text-[var(--primary)]')
    if n:
        p.write_text(txt.replace('text-[var(--primary)]', 'text-[var(--primary-text)]'))
        total += n
        log(p, n, 'text-[var(--primary)] -> text-[var(--primary-text)]')
print(f"   text-[var(--primary)] repointed: {total}")

# 2b. inline styles
for p in walk('src/app/(public)', 'src/components'):
    txt = p.read_text()
    n = txt.count("color: 'var(--primary)'")
    if n:
        p.write_text(txt.replace("color: 'var(--primary)'", "color: 'var(--primary-text)'"))
        log(p, n, "inline color -> var(--primary-text)")

# 2c. grey literals -> var(--muted)  (gray-300 1.42:1 / gray-400 2.43:1 on #fafafa)
sub('src/app/(public)/products/ProductsClient.tsx', 'text-gray-300', 'text-[var(--muted)]', expect=2)
sub('src/app/(public)/support/SupportClient.tsx',   'text-gray-400', 'text-[var(--muted)]', expect=1)

# 2d. green-400 status/availability badges -> var(--primary-text)
sub('src/components/ProductCard.tsx',                        'text-green-400', 'text-[var(--primary-text)]', expect=1)
sub('src/app/(public)/products/ProductsClient.tsx',          'text-green-400', 'text-[var(--primary-text)]', expect=1)
sub('src/app/(public)/support/SupportClient.tsx',            'text-green-400', 'text-[var(--primary-text)]', expect=1)

# 2e. error.tsx: only place pairing the fill with WHITE text (2.02:1 on bright green)
sub('src/app/(public)/error.tsx',
    'bg-[var(--primary)] text-white', 'bg-[var(--primary)] text-black', expect=1)

print("\n=== CHANGES ===")
for f, items in sorted(changed.items()):
    for it in items:
        print(f"  {f}: {it}")
print(f"\ntotal text-usage repoints: {total}")
