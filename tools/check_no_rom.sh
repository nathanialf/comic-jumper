#!/usr/bin/env bash
# =============================================================================
# check_no_rom.sh
#
# IP-safety scan. Refuses to let package data, executables, extracted assets
# or other IP-tainted files slip into a commit. Run before pushing; the
# pre-commit hook runs it on staged files.
#
# Heuristics (intentionally conservative: false positives are fine, false
# negatives are not):
#
#   1. File extensions associated with Xbox 360 packages, executables and
#      extracted assets.
#   2. Xbox 360 naming patterns: default.xex and default.pe, the title id
#      (58410A20*), the 42-hex-digit content file names packages ship under,
#      and the names the tools give the user's package (CJ_*.pkg) whatever
#      the extension.
#   3. Any tracked file > 256 KiB (sources under src/: 8 MiB), except the
#      named text files below.
#   4. Package, XEX and PE magic sniff regardless of extension.
#   5. Raw byte-array initializers in tracked C/C++.
#   6. Any file whose path matches our gitignore patterns but is somehow
#      tracked anyway.
#   7. A run of four or more hex .byte/.quad/.long lines in a tracked source
#      (a copied dump).
#   8. Any tracked file that holds a NUL byte. Everything this repository
#      tracks is text, so a binary file under any name or extension (a slice
#      from the middle of the image carries no magic) is refused.
#
# Exit non-zero on any hit.
# =============================================================================
set -euo pipefail

if [[ -n "${FILES:-}" ]]; then
    mapfile -t files < <(printf "%s\n" "$FILES" | tr ' ' '\n')
elif git diff --cached --name-only --quiet 2>/dev/null; then
    mapfile -t files < <(git ls-files)
else
    mapfile -t files < <(git diff --cached --name-only --diff-filter=ACMR)
fi

bad=0
note() { echo "check_no_rom: $*" >&2; bad=1; }

# --- 1. extension blocklist ---
ext_block_re='\.(pkg|xex|xexp|pe|exe|dll|pdb|xdb|bin|xpr|bik|xwb|xsb|xgs|ptc|xma|gpr|i64|idb|bndb)$'
for f in "${files[@]}"; do
    [[ -z "$f" ]] && continue
    if [[ "$f" =~ $ext_block_re ]]; then
        note "blocked extension: $f"
    fi
done

# --- 2. Xbox 360 naming patterns ---
x360_name_re='(^|/)(default\.(xex|pe)|58410A20[^/]*|[0-9A-Fa-f]{42}(\.[^/]*)?|CJ_[A-Z0-9]+\.[^/]*)$'
for f in "${files[@]}"; do
    [[ -z "$f" ]] && continue
    if [[ "$f" =~ $x360_name_re ]]; then
        note "Xbox 360 package naming: $f"
    fi
done

# --- 3. size cap ---
src_large_re='^src/.*\.(c|cpp|cc|h|hpp|inl)$'
for f in "${files[@]}"; do
    [[ -z "$f" ]] && continue
    [[ ! -f "$f" ]] && continue
    # config/functions.<ver>.txt: `addr size name` rows, no bytes; exempt.
    # config/matched.<ver>.txt: `function tu [symbol]` rows, no bytes; exempt.
    case "$f" in config/functions.*.txt|config/matched.*.txt) continue ;; esac
    # docs/<slug>/progress.json: names, addresses and integer byte counts.
    case "$f" in docs/*/progress.json) continue ;; esac
    size=$(wc -c < "$f")
    if [[ "$f" =~ $src_large_re ]]; then
        if (( size > 8388608 )); then
            note "tracked source >8MiB (suspicious): $f ($size bytes)"
        fi
    elif (( size > 262144 )); then
        note "tracked file >256KiB (suspicious): $f ($size bytes)"
    fi
done

# --- 4. package / XEX / PE magic sniff ---
for f in "${files[@]}"; do
    [[ -z "$f" ]] && continue
    [[ ! -f "$f" ]] && continue
    head4=$(head -c 4 "$f" 2>/dev/null | od -An -tx1 -N4 | tr -d ' \n' || true)
    case "$head4" in
        4c495645|50495253|434f4e20) note "file starts with Xbox Live package magic (LIVE/PIRS/CON): $f" ;;
        58455832) note "file starts with XEX2 magic: $f" ;;
        4d5a*) note "file starts with MZ (a PE image): $f" ;;
        7f454c46) note "file starts with ELF magic: $f" ;;
    esac
done

# --- 5. raw byte-array initializers in tracked C/C++ ---
byte_type_re='(unsigned[[:space:]]+char|signed[[:space:]]+char|char|uint8_t|int8_t|u8|s8)'
raw_byte_re="^[[:space:]]*(static[[:space:]]+)?(const[[:space:]]+)?${byte_type_re}[[:space:]]+[A-Za-z_][A-Za-z0-9_]*[[:space:]]*\[[0-9]*\][[:space:]]*=[[:space:]]*\{[[:space:]]*0x[0-9A-Fa-f]{1,2}[[:space:]]*,([[:space:]]*0x[0-9A-Fa-f]{1,2}[[:space:]]*,){7,}"
for f in "${files[@]}"; do
    [[ -z "$f" ]] && continue
    [[ ! -f "$f" ]] && continue
    case "$f" in src/*.c|src/*.cpp|src/*.cc|src/*.h|src/*.hpp|src/*.inl) ;; *) continue ;; esac
    if grep -nE "${raw_byte_re}" "$f" >/dev/null 2>&1; then
        note "raw byte-array initializer in tracked source: $f"
        note "  data must be typed (string literal / int / float / struct), not raw bytes. See docs/LEGAL.md."
        grep -nE "${raw_byte_re}" "$f" 2>&1 | head -3 >&2
    fi
done

# --- 6. gitignore-tracked anomalies ---
while IFS= read -r f; do
    [[ -z "$f" ]] && continue
    if git check-ignore -q "$f" 2>/dev/null; then
        note "tracked file matches .gitignore: $f"
    fi
done < <(printf "%s\n" "${files[@]}")

# --- 7. hex directive runs in tracked sources ---
for f in "${files[@]}"; do
    [[ -z "$f" ]] && continue
    [[ ! -f "$f" ]] && continue
    case "$f" in *.s|*.S|*.asm|*.c|*.cpp|*.h|*.hpp|*.inc) ;; *) continue ;; esac
    if awk '/^[[:space:]]*\.(byte|quad|long|word|short)[[:space:]]+0x/{if(++c>=4)hit=1;next}{c=0}END{exit !hit}' "$f"; then
        note "run of hex .byte/.quad/.long lines (a dump from the executable?): $f"
    fi
done

# --- 8. binary content under any name ---
for f in "${files[@]}"; do
    [[ -z "$f" ]] && continue
    [[ ! -f "$f" ]] && continue
    if [[ "$(LC_ALL=C tr -d '\000' < "$f" | wc -c)" != "$(wc -c < "$f")" ]]; then
        note "binary content (a NUL byte) in a tracked file: $f"
    fi
done

if (( bad )); then
    echo "" >&2
    echo "IP-safety scan FAILED. See messages above." >&2
    echo "If a hit is a false positive, document why and consider tightening" >&2
    echo "allowlists in tools/check_no_rom.sh rather than removing the check." >&2
    exit 1
fi

echo "check_no_rom: OK (${#files[@]} files scanned)"
