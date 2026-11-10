#!/usr/bin/env bash
# build.sh: from a clean clone to the gate in one command.
#
# The target is the one tools/cj_version.sh detects: VERSION=<slug>, or the
# first configured one (a config/sha256sums.<slug>.txt exists; retail on main).
#
#   1. tools/setup.sh, when the venv is missing.
#   2. tools/extract_pkg.sh, when baserom/<slug>/default.pe or the recorded
#      hashes (config/sha256sums.<slug>.txt) are missing. It reads the user's
#      own package, baserom/CJ_RETAIL.pkg (a symlink is fine), extracts its
#      files, decrypts and expands the executable and records (or verifies)
#      the SHA-256s.
#   3. tools/build.sh verify: the recorded SHA-256s of the base files.
#   4. tools/build.sh setup + ninja, once tools/gen_ninja.py exists (the
#      compile and match stage; not yet, during the survey stage).
#   5. tools/check_pe.py --gate.
#
# Exits non-zero when any step fails.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

# shellcheck source=tools/cj_version.sh
. tools/cj_version.sh
cj_version_init "$ROOT"

toolchain_ok() {
    [[ -x .venv/bin/python && -x .venv/bin/ninja && -x .venv/bin/clang-format ]] &&
    .venv/bin/python -I -c 'import cryptography, capstone' 2>/dev/null
}

if ! toolchain_ok; then
    echo "==> build.sh: toolchain incomplete, running tools/setup.sh"
    CJ_FROM_BUILD_SH=1 tools/setup.sh
    if ! toolchain_ok; then
        echo "build.sh: tools/setup.sh finished but the toolchain is still incomplete;" >&2
        echo "  see its output above (network access, host packages)." >&2
        exit 1
    fi
fi

if [[ ! -f "$CJ_BASEPE" || ! -f "$CJ_BASEXEX" || ! -f "$CJ_SHA256SUMS" ]]; then
    if [[ ! -e "$CJ_PKG" ]]; then
        cat >&2 <<EOM
build.sh: $CJ_BASEPE is missing and there is no package to extract it from.
  Point $CJ_PKG at your own copy of the $CJ_PKG_NAME:
    mkdir -p baserom
    ln -s "/path/to/your/Comic Jumper/58410A20/000D0000/<content file>" $CJ_PKG
  then run ./build.sh again. Nothing under baserom/ is ever committed.
EOM
        exit 1
    fi
    echo "==> build.sh: extracting the executable from $CJ_PKG"
    tools/extract_pkg.sh
fi

tools/build.sh verify

if [[ -f tools/gen_ninja.py ]]; then
    if [[ -f build.ninja ]]; then :; else tools/build.sh setup; fi
    .venv/bin/ninja
fi
echo
echo "==> build.sh: gate"
VERSION="$CJ_VERSION" .venv/bin/python -I tools/check_pe.py --gate
if [[ ! -f tools/gen_ninja.py ]]; then
    echo "==> build.sh: survey stage (no tools/gen_ninja.py yet); base files verified."
    echo "    The executable's map: tools/survey_pe.sh (docs/SURVEY.md)"
fi
