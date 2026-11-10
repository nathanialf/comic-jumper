#!/usr/bin/env bash
# Format (or check) the repo's C/C++ with clang-format and the tracked .clang-format.
#   tools/format.sh            # rewrite every tracked or untracked source under src/
#   tools/format.sh --check    # exit 1 if any source is not formatted (pre-commit)
#   tools/format.sh FILE...    # format just these files
# Whitespace and line breaks only. The binary is the `clang-format` wheel in
# the venv (tools/setup.sh installs it); without it the script fails.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CF="$ROOT/.venv/bin/clang-format"
if [[ ! -x "$CF" ]]; then
    echo "format: $CF not found; run tools/setup.sh (it installs tools/requirements.txt)" >&2
    exit 1
fi
mode=format
if [[ "${1:-}" == "--check" ]]; then mode=check; shift; fi
if [[ $# -gt 0 ]]; then
    files=("$@")
else
    mapfile -t files < <(cd "$ROOT" && git ls-files -co --exclude-standard 'src/*.c' 'src/*.cpp' 'src/*.h' 'src/*.hpp' 'src/*.inl')
fi
[[ ${#files[@]} -gt 0 ]] || exit 0
cd "$ROOT"
if [[ "$mode" == check ]]; then
    bad=0
    for f in "${files[@]}"; do
        [[ -f "$f" ]] || continue
        if ! "$CF" --dry-run -Werror "$f" >/dev/null 2>&1; then
            echo "format: $f is not clang-formatted (run tools/format.sh $f)" >&2
            bad=1
        fi
    done
    exit $bad
fi
"$CF" -i "${files[@]}"
