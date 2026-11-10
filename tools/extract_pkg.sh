#!/usr/bin/env bash
# =============================================================================
# tools/extract_pkg.sh
#
# Extracts every file from the user's own Xbox Live package
# (baserom/CJ_RETAIL.pkg, a file or a symlink to the user's copy) into
# baserom/<slug>/files/, copies the executable to baserom/<slug>/default.xex,
# decrypts and expands it to baserom/<slug>/default.pe, and records the
# SHA-256s to config/sha256sums.<slug>.txt (creating the entries on first run,
# verifying against them after). The target is VERSION, or the first
# configured one (tools/cj_version.py).
#
# Wrapper that delegates to tools/extract_pkg.py.
#
# Reads no copyrighted material into the repository: everything but the
# hashes lands under baserom/, which is gitignored.
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

VENV_PY="$ROOT/.venv/bin/python"
if [[ ! -x "$VENV_PY" ]]; then
    echo "extract_pkg: $VENV_PY not found: run tools/setup.sh first" >&2
    exit 1
fi

exec "$VENV_PY" -I "$ROOT/tools/extract_pkg.py" "$@"
