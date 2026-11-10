# tools/cj_version.sh: shell twin of tools/cj_version.py.
#
# Source it and call `cj_version_init [repo_root]`; it exports:
#   CJ_VERSION      target slug (retail)
#   CJ_BASEROM_DIR  baserom/<slug>
#   CJ_FILES_DIR    baserom/<slug>/files, the extracted package's files
#   CJ_BASEXEX      baserom/<slug>/default.xex, the executable as shipped
#   CJ_BASEPE       baserom/<slug>/default.pe, its decrypted, expanded image
#   CJ_PKG          the package the user places under baserom/
#   CJ_PKG_NAME     the package as messages name it
#   CJ_TITLE_ID     its title id
#   CJ_BUILD_DIR    build/<slug>
#   CJ_SHA256SUMS   config/sha256sums.<slug>.txt
#   CJ_DOCS_DIR     docs/<slug>
#   CJ_VERSIONS     every configured slug (a config/sha256sums.<slug>.txt
#                   exists), space-separated, in detection order
# All paths are repo-root-relative. An explicit VERSION environment variable
# wins, otherwise the slug is the first configured one, and `retail` when none
# is. No python and no .venv dependency, so the shell tools can source it
# before the venv exists. Keep in sync with tools/cj_version.py.

cj_version_configured() {
    local root="${1:-.}" v
    for v in retail; do
        if [ -f "$root/config/sha256sums.$v.txt" ]; then printf '%s\n' "$v"; fi
    done
}

cj_version_detect() {
    local root="${1:-.}" v
    if [ -n "${VERSION:-}" ]; then printf '%s\n' "$VERSION"; return 0; fi
    v="$(cj_version_configured "$root" | head -n 1)"
    printf '%s\n' "${v:-retail}"
}

# cj_version_pkg <version>: sets CJ_PKG, CJ_PKG_NAME and CJ_TITLE_ID (all
# empty for a slug with no package recipe).
cj_version_pkg() {
    local region="" image=""
    CJ_TITLE_ID=""
    case "$1" in
        retail) region="Xbox Live Arcade retail package, version 0x101"
                CJ_TITLE_ID="58410A20"
                image="CJ_RETAIL.pkg" ;;
    esac
    CJ_PKG="${image:+baserom/$image}"
    CJ_PKG_NAME="${region:+$region}${CJ_TITLE_ID:+ ($CJ_TITLE_ID)}"
}

cj_version_init() {
    local root="${1:-$PWD}"
    CJ_VERSION="$(cj_version_detect "$root")"
    CJ_BASEROM_DIR="baserom/${CJ_VERSION}"
    CJ_FILES_DIR="${CJ_BASEROM_DIR}/files"
    CJ_BASEXEX="${CJ_BASEROM_DIR}/default.xex"
    CJ_BASEPE="${CJ_BASEROM_DIR}/default.pe"
    CJ_BUILD_DIR="build/${CJ_VERSION}"
    CJ_SHA256SUMS="config/sha256sums.${CJ_VERSION}.txt"
    CJ_DOCS_DIR="docs/${CJ_VERSION}"
    CJ_VERSIONS="$(cj_version_configured "$root" | tr '\n' ' ')"
    CJ_VERSIONS="${CJ_VERSIONS% }"
    cj_version_pkg "$CJ_VERSION"
    export CJ_VERSION CJ_BASEROM_DIR CJ_FILES_DIR CJ_BASEXEX CJ_BASEPE
    export CJ_PKG CJ_PKG_NAME CJ_TITLE_ID
    export CJ_BUILD_DIR CJ_SHA256SUMS CJ_DOCS_DIR CJ_VERSIONS
}
