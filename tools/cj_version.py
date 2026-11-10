"""Shared target-slug detection and per-target paths for the Comic Jumper tooling.

The targets:

    slug     package                                         executable
    ------   ---------------------------------------------   -----------
    retail   Xbox Live Arcade retail package, title id       default.xex
             58410A20, version 0x101 (media id 69414724)

One tree may carry several targets. A target is configured in a tree when
config/sha256sums.<slug>.txt exists (configured_versions()). Its other
per-target files are config/<stem>.<slug>.<ext>; its extracted base files are
baserom/<slug>/ (`baserom/` is gitignored and holds every target's files side
by side); its build is under build/<slug>/; its progress files are under
docs/<slug>/.

An explicit `VERSION` environment variable wins; otherwise the slug is the
first configured one in VERSIONS order, and `retail` when none is.

PKGS is the one table of what each target's package is called and how the
tools name it in messages: the file (or symlink) the user places under
baserom/, the ids its header must carry, and the executable
tools/extract_pkg.py pulls out of it.

tools/cj_version.sh is the shell twin of this module (same detection order,
same paths, same package table). Keep the two in sync.
"""
from __future__ import annotations
import os
from pathlib import Path

# Detection order.
VERSIONS = ("retail",)

# Per-target package.
#   region     : how messages describe the package
#   title_id   : the title id in the package header and the XEX execution info
#   version    : the title version in both
#   media_id   : the media id in both
#   image      : the file (or symlink) the user places under baserom/
#   executable : the executable's name inside the package
PKGS = {
    "retail": {
        "region": "Xbox Live Arcade retail package, version 0x101",
        "title_id": 0x58410A20,
        "version": 0x00000101,
        "media_id": 0x69414724,
        "image": "CJ_RETAIL.pkg",
        "executable": "default.xex",
    },
}


def configured_versions(repo_root: Path) -> list[str]:
    """The slugs this tree carries recorded hashes for, in VERSIONS order."""
    return [v for v in VERSIONS
            if (repo_root / "config" / f"sha256sums.{v}.txt").exists()]


def detect_version(repo_root: Path) -> str:
    v = os.environ.get("VERSION")
    if v:
        return v
    have = configured_versions(repo_root)
    return have[0] if have else VERSIONS[0]


def baserom_dir(repo_root: Path, version: str) -> Path:
    """Directory holding this target's extracted base files."""
    return repo_root / "baserom" / version


def files_dir(repo_root: Path, version: str) -> Path:
    """The extracted package's files, baserom/<slug>/files/."""
    return baserom_dir(repo_root, version) / "files"


def basexex_path(repo_root: Path, version: str) -> Path:
    """The executable as the package ships it (an encrypted XEX2)."""
    return baserom_dir(repo_root, version) / "default.xex"


def basepe_path(repo_root: Path, version: str) -> Path:
    """The executable's image, decrypted and expanded: the PE as the loader
    maps it at its base address (tools/extract_pkg.py)."""
    return baserom_dir(repo_root, version) / "default.pe"


def config_path(repo_root: Path, version: str, stem: str, ext: str) -> Path:
    """config/<stem>.<version>.<ext>, e.g. config/functions.retail.txt."""
    return repo_root / "config" / f"{stem}.{version}.{ext}"


def build_dir(repo_root: Path, version: str) -> Path:
    """This target's build directory, build/<version>."""
    return repo_root / "build" / version


def sha256sums_path(repo_root: Path, version: str) -> Path:
    """The recorded SHA-256s of this target's base files,
    config/sha256sums.<version>.txt (keyed by basename)."""
    return repo_root / "config" / f"sha256sums.{version}.txt"


def docs_dir(repo_root: Path, version: str) -> Path:
    """This target's progress files, docs/<version>/ (PROGRESS.md,
    progress.json)."""
    return repo_root / "docs" / version


def pkg_name(version: str) -> str:
    """The package as messages name it ("" for a slug with no PKGS row)."""
    d = PKGS.get(version)
    if d is None:
        return ""
    return f"{d['region']} ({d['title_id']:08X})"


def pkg_image(repo_root: Path, version: str) -> Path | None:
    """The package file the user places under baserom/ for this target."""
    d = PKGS.get(version)
    return repo_root / "baserom" / d["image"] if d else None


def _rel(p, root):
    return "" if p is None else p.relative_to(root)


_KEYS = {
    "version": lambda root, v: v,
    "baserom_dir": lambda root, v: baserom_dir(root, v).relative_to(root),
    "files_dir": lambda root, v: files_dir(root, v).relative_to(root),
    "basexex": lambda root, v: basexex_path(root, v).relative_to(root),
    "basepe": lambda root, v: basepe_path(root, v).relative_to(root),
    "pkg": lambda root, v: _rel(pkg_image(root, v), root),
    "pkg_name": lambda root, v: pkg_name(v),
    "title_id": lambda root, v: f"{PKGS[v]['title_id']:08X}" if v in PKGS else "",
    "build_dir": lambda root, v: build_dir(root, v).relative_to(root),
    "sha256sums": lambda root, v: sha256sums_path(root, v).relative_to(root),
    "docs_dir": lambda root, v: docs_dir(root, v).relative_to(root),
    "versions": lambda root, v: " ".join(configured_versions(root)),
}


def main(argv: list[str] | None = None) -> int:
    import sys
    argv = list(sys.argv[1:] if argv is None else argv)
    root = Path(__file__).resolve().parent.parent
    ver = detect_version(root)
    if not argv:
        for k, fn in _KEYS.items():
            print(f"CJ_{k.upper()}={fn(root, ver)}")
        return 0
    for key in argv:
        if key not in _KEYS:
            print(f"cj_version: unknown key '{key}' (have: {', '.join(_KEYS)})",
                  file=sys.stderr)
            return 2
        print(_KEYS[key](root, ver))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
