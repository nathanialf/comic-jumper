#!/usr/bin/env python3
"""
extract_pkg.py: extract the target's files from the user's own Xbox Live
package and record (or verify) their SHA-256s.

    baserom/<IMAGE>                  the user's package (file or symlink)
      -> baserom/<slug>/files/*      every file the package holds
      -> baserom/<slug>/default.xex  the executable as shipped
      -> baserom/<slug>/default.pe   its image, decrypted and expanded
      -> config/sha256sums.<slug>.txt  written on the first run, verified after

The package is an STFS volume (magic LIVE or PIRS). The block layout follows
Velocity's public reader (github.com/hetelek/Velocity, XboxInternals/Stfs/
StfsPackage.cpp): data blocks of 0x1000 bytes with a hash block ahead of every
0xAA of them, each hash entry holding the block's SHA-1 and the number of the
block that follows it in its file. Every block read here is checked against
its SHA-1, and each file's chain is followed through the hash entries, so a
wrong layout fails loudly and cannot write a wrong file.

Only the read-only layout with one hash table per level is handled (the
volume descriptor's block separation bit set); the other is refused.

Nothing but the hashes leaves baserom/, which is gitignored.
"""
from __future__ import annotations

import argparse
import hashlib
import mmap
import shutil
import struct
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cj_version as cv  # noqa: E402
import xex  # noqa: E402

BLOCK = 0x1000
PER_L0 = 0xAA            # data blocks per level-0 hash block
PER_L1 = 0xAA * 0xAA     # data blocks per level-1 hash block (0x70E4)
HASH_ENTRY = 0x18


def die(msg: str) -> "None":
    print(f"extract_pkg: {msg}", file=sys.stderr)
    raise SystemExit(1)


class Stfs:
    def __init__(self, m: mmap.mmap):
        self.m = m
        magic = bytes(m[:4])
        if magic not in (b"LIVE", b"PIRS"):
            die(f"not an Xbox Live package (magic {magic!r}; expected LIVE or PIRS)")
        self.magic = magic.decode()
        self.header_size, self.content_type = struct.unpack_from(">II", m, 0x340)
        self.media_id, self.version, self.base_version, self.title_id = \
            struct.unpack_from(">IIII", m, 0x354)
        self.display_name = bytes(m[0x411:0x411 + 0x80]).decode("utf-16-be").split("\0")[0]
        vd = bytes(m[0x379:0x379 + 0x24])
        if vd[0] != 0x24:
            die(f"volume descriptor size {vd[0]:#x}, expected 0x24 (not an STFS volume)")
        self.block_separation = vd[2]
        self.table_blocks = struct.unpack_from("<H", vd, 3)[0]
        self.table_start = int.from_bytes(vd[5:8], "little")
        self.allocated = struct.unpack_from(">I", vd, 0x1C)[0]
        if not (self.block_separation & 1):
            die("the package uses the two-hash-table layout (block separation "
                f"{self.block_separation:#x}); only the read-only layout is handled")
        self.first_hash = (self.header_size + 0xFFF) & 0xFFFFF000

    # Backing block numbers: one hash block ahead of every 0xAA data blocks,
    # one level-1 block ahead of every 0x70E4 once the volume needs it, one
    # level-2 block once it needs that.
    def _data_backing(self, n: int) -> int:
        b = (n + PER_L0) // PER_L0 + n
        if n < PER_L0:
            return b
        b += (n + PER_L1) // PER_L1
        if n < PER_L1:
            return b
        return b + 1

    def _l0_backing(self, n: int) -> int:
        if n < PER_L0:
            return 0
        b = (n // PER_L0) * (PER_L0 + 1) + (n // PER_L1) + 1
        if n // PER_L1 == 0:
            return b
        return b + 1

    def block(self, n: int) -> bytes:
        """Data block n, checked against its SHA-1."""
        if n >= self.allocated:
            die(f"block {n:#x} is past the volume's {self.allocated:#x} allocated blocks")
        off = self.first_hash + self._data_backing(n) * BLOCK
        data = bytes(self.m[off:off + BLOCK])
        if hashlib.sha1(data).digest() != self._entry(n)[:20]:
            die(f"block {n:#x} at offset {off:#x} fails its SHA-1: the package "
                "is damaged or its layout is not the one this tool reads")
        return data

    def _entry(self, n: int) -> bytes:
        off = self.first_hash + self._l0_backing(n) * BLOCK + (n % PER_L0) * HASH_ENTRY
        return bytes(self.m[off:off + HASH_ENTRY])

    def next_block(self, n: int) -> int:
        return int.from_bytes(self._entry(n)[21:24], "big")

    def chain(self, start: int, count: int):
        n = start
        for _ in range(count):
            yield n
            n = self.next_block(n)

    def entries(self):
        """(name, is_dir, path_index, blocks, start, size) per file table row."""
        out = []
        for bn in self.chain(self.table_start, self.table_blocks):
            data = self.block(bn)
            for o in range(0, BLOCK, 0x40):
                e = data[o:o + 0x40]
                flags = e[0x28]
                namelen = flags & 0x3F
                if namelen == 0:
                    return out
                name = e[:namelen].decode("ascii")
                blocks = int.from_bytes(e[0x29:0x2C], "little")
                start = int.from_bytes(e[0x2F:0x32], "little")
                path_index, size = struct.unpack_from(">hI", e, 0x32)
                out.append((name, bool(flags & 0x80), path_index, blocks, start, size))
        return out

    def read_file(self, start: int, blocks: int, size: int) -> bytes:
        if blocks != (size + BLOCK - 1) // BLOCK:
            die(f"file of {size} bytes lists {blocks} blocks")
        out = bytearray()
        for bn in self.chain(start, blocks):
            out += self.block(bn)
        return bytes(out[:size])


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


SUMS_HEADER = """\
# SHA-256 of the target's base files, keyed by basename. Written once by
# tools/extract_pkg.py from the user's own package; verified by
# tools/verify_base.py. NEVER EDIT: a mismatch means a different package
# or a changed tool, and either is a finding, not a typo.
#
# {name}
#   {image:<14} the package as the user supplies it
#   default.xex    the executable as the package holds it
#   default.pe     its image, decrypted and expanded (the PE as loaded)
"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.parse_args(argv)

    ver = cv.detect_version(REPO_ROOT)
    row = cv.PKGS.get(ver)
    if row is None:
        die(f"no package recipe for VERSION={ver} (tools/cj_version.py PKGS)")
    pkg = cv.pkg_image(REPO_ROOT, ver)
    if not pkg.exists():
        die(f"{pkg.relative_to(REPO_ROOT)} not found: place (or symlink) your own "
            f"copy of the {cv.pkg_name(ver)} package there")

    out_dir = cv.baserom_dir(REPO_ROOT, ver)
    files_dir = cv.files_dir(REPO_ROOT, ver)

    with pkg.open("rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as m:
        st = Stfs(m)
        print(f"extract_pkg: {pkg.relative_to(REPO_ROOT)}: {st.magic} package "
              f"\"{st.display_name}\", title {st.title_id:08X}, version "
              f"{st.version:#x}, media {st.media_id:08X}, "
              f"{st.allocated} blocks")
        for what, got in (("title_id", st.title_id), ("version", st.version),
                          ("media_id", st.media_id)):
            if got != row[what]:
                die(f"the package's {what} is {got:#x}; the {ver} target is "
                    f"{row[what]:#x}. This is a different package.")

        entries = st.entries()
        dirs = {i: e[0] for i, e in enumerate(entries) if e[1]}

        def rel(i: int) -> Path:
            name, _d, parent, *_ = entries[i]
            return (rel(parent) / name) if parent >= 0 else Path(name)

        if files_dir.exists():
            shutil.rmtree(files_dir)
        files_dir.mkdir(parents=True)
        n_files = total = 0
        for i, (name, is_dir, _parent, blocks, start, size) in enumerate(entries):
            dest = files_dir / rel(i)
            if files_dir not in dest.resolve().parents:
                die(f"file table entry {name!r} leaves the output directory")
            if is_dir:
                dest.mkdir(parents=True, exist_ok=True)
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(st.read_file(start, blocks, size))
            n_files += 1
            total += size
        print(f"extract_pkg: {n_files} files, {total} bytes, {len(dirs)} "
              f"directories -> {files_dir.relative_to(REPO_ROOT)}/ "
              "(every block checked against its SHA-1)")

    src_xex = files_dir / row["executable"]
    if not src_xex.is_file():
        die(f"the package holds no {row['executable']}")
    base_xex = cv.basexex_path(REPO_ROOT, ver)
    shutil.copyfile(src_xex, base_xex)

    try:
        x = xex.parse(base_xex.read_bytes())
        info = x.execution_info() or {}
        for what in ("title_id", "version", "media_id"):
            if info.get(what) != row[what]:
                die(f"{row['executable']}: execution info {what} is "
                    f"{info.get(what)!r}; the {ver} target is {row[what]:#x}")
        img = xex.image(x)
    except xex.XexError as e:
        die(f"{row['executable']}: {e}")
    if x.image_base != x.load_address:
        die(f"image base header {x.image_base:#x} and security info load "
            f"address {x.load_address:#x} disagree")
    pe_off = struct.unpack_from("<I", img, 0x3C)[0]
    if img[pe_off:pe_off + 4] != b"PE\0\0":
        die("expanded image has no PE signature where its MZ header points")
    base_pe = cv.basepe_path(REPO_ROOT, ver)
    base_pe.write_bytes(img)
    print(f"extract_pkg: {base_xex.relative_to(REPO_ROOT)} ({base_xex.stat().st_size} bytes) "
          f"-> {base_pe.relative_to(REPO_ROOT)} ({len(img):#x} bytes, base "
          f"{x.image_base:#x}, entry {x.entry_point:#x}, {x.original_pe_name})")

    # Record on the first run; verify on every later one.
    sums = cv.sha256sums_path(REPO_ROOT, ver)
    actual = [(sha256_file(p), n) for p, n in
              ((pkg, row["image"]), (base_xex, base_xex.name), (base_pe, base_pe.name))]
    if not sums.exists():
        sums.parent.mkdir(parents=True, exist_ok=True)
        text = SUMS_HEADER.format(name=cv.pkg_name(ver), image=row["image"])
        text += "".join(f"{h}  {n}\n" for h, n in actual)
        sums.write_text(text)
        print(f"extract_pkg: recorded {len(actual)} SHA-256s in {sums.relative_to(REPO_ROOT)}")
        return 0
    recorded = {}
    for line in sums.read_text().splitlines():
        parts = line.split()
        if len(parts) == 2 and not line.startswith("#"):
            recorded[parts[1]] = parts[0]
    bad = 0
    for h, n in actual:
        if recorded.get(n) != h:
            print(f"extract_pkg: MISMATCH {n}\n  recorded: {recorded.get(n)}\n"
                  f"  actual:   {h}", file=sys.stderr)
            bad = 1
    if bad:
        die(f"the files differ from {sums.relative_to(REPO_ROOT)}; the recorded "
            "hashes are never edited. This is a different package or a changed tool.")
    print(f"extract_pkg: all {len(actual)} SHA-256s equal {sums.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
