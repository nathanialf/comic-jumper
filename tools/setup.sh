#!/usr/bin/env bash
# =============================================================================
# tools/setup.sh
#
# One-shot host setup. Idempotent: running it twice is fine.
#
#   1. Create a Python venv at .venv and install tools/requirements.txt.
#   2. Check for the host packages the tools use (LLVM 19 for disassembly),
#      printing the apt command when one is missing. Nothing else is fetched
#      at the survey stage: the package reader and the XEX reader are this
#      repository's own Python (tools/extract_pkg.py, tools/xex.py). The
#      compiler joins here, pinned by SHA-256 under tools/cc/, when
#      docs/DECISIONS.md D1 is decided.
#   3. Install the git hooks (tools/install_hooks.sh).
#
# This script downloads no game data and no Microsoft files.
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python3}"
VENV="${VENV:-.venv}"

echo "==> comic-jumper setup at $ROOT"

# --- 1. Python venv ----------------------------------------------------------

if [[ ! -d "$VENV" ]]; then
    echo "==> creating venv at $VENV"
    "$PYTHON" -m venv "$VENV"
fi
# shellcheck disable=SC1091
source "$VENV/bin/activate"
python -m pip install --upgrade pip >/dev/null
python -m pip install -q -r tools/requirements.txt

# --- 2. Host packages: LLVM 19 (disassembly) ----------------------------------

missing=()
for t in llvm-objdump-19; do
    command -v "$t" >/dev/null 2>&1 || missing+=("$t")
done
if (( ${#missing[@]} )); then
    cat >&2 <<EOM

==> LLVM 19 tools missing on PATH: ${missing[*]}
    Debian/Ubuntu:
      sudo apt-get install -y llvm-19
    (not needed to extract, survey or gate; used to read disassembly)
EOM
else
    echo "==> LLVM 19 on PATH ($(llvm-objdump-19 --version | sed -n 2p | sed 's/^ *//'))"
fi

# --- 3. git hooks --------------------------------------------------------------

if [[ -d .git ]]; then
    bash tools/install_hooks.sh
else
    echo "==> not a git repo yet; skipping hook install"
fi

echo
if [[ "${CJ_FROM_BUILD_SH:-0}" == "1" ]]; then
    echo "Setup complete; build.sh continues."
    exit 0
fi
# shellcheck source=tools/cj_version.sh
. "$(dirname "$0")/cj_version.sh"
cj_version_init "$ROOT"
echo "Setup complete. Next steps:"
echo "  1. Point $CJ_PKG at your own copy of the $CJ_PKG_NAME:"
echo "       mkdir -p baserom && ln -s /path/to/your/content-file $CJ_PKG"
echo "  2. Run './build.sh' (or 'tools/extract_pkg.sh') to extract $CJ_BASEPE"
