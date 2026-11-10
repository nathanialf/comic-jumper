#!/usr/bin/env bash
# tools/build.sh: top-level orchestration for the Comic Jumper decomp.
#
# One tree may carry several targets: a target is configured when
# config/sha256sums.<slug>.txt exists. The target slug and its paths come from
# tools/cj_version.sh: VERSION=<slug> picks one, and without it the first
# configured target (retail) is used.
#
# Subcommands:
#   setup         Delete build/<slug>/, verify the base files' SHA-256s,
#                 write build.ninja (once tools/gen_ninja.py exists).
#   verify        Just verify the base files' SHA-256s.
#   regen         Just rewrite build.ninja.
#   clean         rm -rf build/<slug>/.
#   distclean     rm -rf build/ and build.ninja (every target).
#   progress      Regenerate the progress files (docs/<slug>/PROGRESS.md,
#                 docs/<slug>/progress.json, README's progress block).
#   gate-all      For every configured target: require its base files, then
#                 setup, ninja and the gate.
#   progress-all  progress for every configured target.

set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${ROOT}"

VENV_PY="${ROOT}/.venv/bin/python"

# shellcheck source=tools/cj_version.sh
. "${ROOT}/tools/cj_version.sh"
cj_version_init "${ROOT}"
VERSION="${CJ_VERSION}"
export VERSION

regen_ninja() {
    if [ ! -f tools/gen_ninja.py ]; then
        echo "build.sh: no tools/gen_ninja.py yet (survey stage); nothing to write" >&2
        return 0
    fi
    echo "==> writing build.ninja (VERSION=${VERSION})"
    "${VENV_PY}" -I tools/gen_ninja.py
}

verify_base() {
    echo "==> verifying the base files' SHA-256s (${CJ_SHA256SUMS})"
    "${VENV_PY}" -I tools/verify_base.py --target "${CJ_BASEXEX}"
    "${VENV_PY}" -I tools/verify_base.py --target "${CJ_BASEPE}"
}

setup() {
    echo "==> clean ${CJ_BUILD_DIR}/ (full rebuild)"
    rm -rf "${CJ_BUILD_DIR}"
    verify_base
    regen_ninja
}

# The gate's build: the base files verified and build.ninja rewritten, the
# objects rebuilt by ninja from its dependency log (every header a TU includes
# is in its depfile; the compiler binary is an implicit input of every object,
# so a rebuilt compiler rebuilds everything). CJ_CLEAN=1 removes the build
# directory first, the from-scratch gate.
prepare() {
    if [ "${CJ_CLEAN:-0}" = 1 ]; then
        setup
    else
        verify_base
        regen_ninja
    fi
}

do_progress() {
    if [ ! -f tools/check_pe.py ]; then
        echo "build.sh: no tools/check_pe.py yet; nothing to regenerate" >&2
        return 0
    fi
    "${VENV_PY}" -I tools/check_pe.py --progress
}

ninja_bin() {
    if [ -x "${ROOT}/.venv/bin/ninja" ]; then
        printf '%s\n' "${ROOT}/.venv/bin/ninja"
    else
        command -v ninja || { echo "build.sh: ninja missing: run tools/setup.sh" >&2; exit 1; }
    fi
}

gate_all() {
    local v missing=0 n
    if [ -z "${CJ_VERSIONS}" ]; then
        echo "build.sh gate-all: no configured target (no config/sha256sums.<slug>.txt)" >&2
        exit 1
    fi
    for v in ${CJ_VERSIONS}; do
        for f in "baserom/${v}/default.xex" "baserom/${v}/default.pe"; do
            if [ ! -f "${f}" ]; then
                echo "build.sh gate-all: ${f} is missing; every configured target (${CJ_VERSIONS}) needs its base files (VERSION=${v} tools/extract_pkg.sh)" >&2
                missing=1
            fi
        done
    done
    [ "${missing}" -eq 0 ] || exit 1
    for v in ${CJ_VERSIONS}; do
        echo "==> gate-all: ${v}"
        VERSION="${v}" "${ROOT}/tools/build.sh" prepare
        # ninja's default target is the gate itself (tools/gen_ninja.py: the
        # objects, then tools/check_pe.py --gate), so the gate runs once here
        if [ -f tools/gen_ninja.py ]; then
            n="$(ninja_bin)"
            VERSION="${v}" "${n}" -C "${ROOT}"
        elif [ -f tools/check_pe.py ]; then
            VERSION="${v}" "${VENV_PY}" -I tools/check_pe.py --gate
        fi
    done
    echo "==> gate-all: every configured target passed (${CJ_VERSIONS})"
}

progress_all() {
    local v
    for v in ${CJ_VERSIONS}; do
        echo "==> progress-all: ${v}"
        VERSION="${v}" do_progress
    done
}

cmd="${1:-help}"
case "$cmd" in
    setup)        setup ;;
    prepare)      prepare ;;
    verify)       verify_base ;;
    regen)        regen_ninja ;;
    clean)        rm -rf "${CJ_BUILD_DIR}" ;;
    distclean)    rm -rf build; rm -f build.ninja .ninja_log .ninja_deps ;;
    progress)     do_progress ;;
    gate-all)     gate_all ;;
    progress-all) progress_all ;;
    help|*)
        cat <<USAGE
usage: [VERSION=<slug>] $0 <subcommand>      (configured: ${CJ_VERSIONS:-none}; now ${VERSION})

  setup         delete ${CJ_BUILD_DIR}/, verify the base files, write build.ninja
  verify        verify the base files' SHA-256s only
  regen         rewrite build.ninja
  clean         rm -rf ${CJ_BUILD_DIR}/
  distclean     rm -rf build/ and delete build.ninja
  progress      regenerate ${CJ_DOCS_DIR}/PROGRESS.md, ${CJ_DOCS_DIR}/progress.json and README's block
  gate-all      every configured target: its base files required, then setup, ninja, gate
  progress-all  progress for every configured target
USAGE
        ;;
esac
