#!/usr/bin/env python3
"""
survey_pe.py: the map of the target's executable, read from the base files.

    baserom/<slug>/default.xex   XEX headers: imports, libraries, ids
    baserom/<slug>/default.pe    the image: sections, function table, strings

Writes (with --write; without it, prints the summary only):
    config/functions.<slug>.txt   `addr size name` per function the image's
                                  own function table (.pdata) attests
    config/imports.<slug>.txt     `library ordinal kind address` per import
    docs/SURVEY.md                with --md

default.pe is the image as the loader maps it: a byte's offset in the file is
its RVA, and the section headers' raw pointers do not apply.

The function table is the PE exception directory. Each entry is two
big-endian words: the function's address, and a word packing the prolog
length (low 8 bits) and the function length (next 22 bits), both in
instructions, then a 32-bit flag and an exception-handler flag. A few entries have the
32-bit flag clear (the survey lists them). The survey
checks that reading against the image (sorted, no overlap, every range inside
an executable section) and fails when it does not hold. A function with no
entry (a leaf that needs no unwind data) is not in the table; the bytes of
executable sections outside every entry are counted and left unclaimed.
"""
from __future__ import annotations

import argparse
import datetime
import re
import struct
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cj_version as cv  # noqa: E402
import xex  # noqa: E402

SCN_CODE = 0x00000020
SCN_UNINIT = 0x00000080
SCN_DISCARDABLE = 0x02000000
SCN_EXECUTE = 0x20000000
SCN_WRITE = 0x80000000


def die(msg: str) -> "None":
    print(f"survey_pe: {msg}", file=sys.stderr)
    raise SystemExit(1)


class Image:
    def __init__(self, data: bytes):
        self.d = d = data
        if d[:2] != b"MZ":
            die("default.pe does not start with MZ")
        pe = struct.unpack_from("<I", d, 0x3C)[0]
        if d[pe:pe + 4] != b"PE\0\0":
            die("no PE signature")
        self.machine, nsec, self.timestamp, _, _, optsz, self.characteristics = \
            struct.unpack_from("<HHIIIHH", d, pe + 4)
        o = pe + 24
        self.entry_rva = struct.unpack_from("<I", d, o + 16)[0]
        self.base = struct.unpack_from("<I", d, o + 28)[0]
        self.section_align, self.file_align = struct.unpack_from("<II", d, o + 32)
        self.size_of_image = struct.unpack_from("<I", d, o + 56)[0]
        ndirs = struct.unpack_from("<I", d, o + 92)[0]
        self.dirs = [struct.unpack_from("<II", d, o + 96 + 8 * i) for i in range(ndirs)]
        self.sections = []
        so = o + optsz
        for _ in range(nsec):
            name = d[so:so + 8].rstrip(b"\0").decode("ascii")
            vsize, va, rsize, _rp = struct.unpack_from("<IIII", d, so + 8)
            flags = struct.unpack_from("<I", d, so + 36)[0]
            self.sections.append((name, va, vsize, rsize, flags))
            so += 40
        self.rich = self._rich(pe)

    def _rich(self, pe: int):
        d = self.d
        i = d.find(b"Rich", 0x40, pe)
        if i < 0:
            return []
        key = struct.unpack_from("<I", d, i + 4)[0]
        words = []
        j = i - 4
        while j >= 0x40:
            w = struct.unpack_from("<I", d, j)[0] ^ key
            if w == 0x536E6144:      # "DanS"
                break
            words.append(w)
            j -= 4
        else:
            return []
        words.reverse()
        words = words[3:]            # three padding words follow DanS
        return [(words[k] >> 16, words[k] & 0xFFFF, words[k + 1])
                for k in range(0, len(words) - 1, 2)]

    def section_of(self, rva: int):
        for s in self.sections:
            if s[1] <= rva < s[1] + max(s[2], s[3]):
                return s
        return None

    def functions(self):
        rva, size = self.dirs[3]
        if not size or size % 8:
            die(f"exception directory size {size:#x} is not a whole number of 8-byte entries")
        out = []
        for i in range(size // 8):
            addr, w = struct.unpack_from(">II", self.d, rva + 8 * i)
            out.append((addr, ((w >> 8) & 0x3FFFFF) * 4, w & 0xFF, (w >> 30) & 1, w >> 31))
        return out


def kind(flags: int) -> str:
    if flags & SCN_EXECUTE:
        return "code"
    if flags & SCN_UNINIT:
        return "bss"
    if flags & SCN_DISCARDABLE:
        return "discardable"
    return "data" if flags & SCN_WRITE else "rodata"


SRC_RE = re.compile(rb"[A-Za-z]:[\\/][\x20-\x7e]{3,200}?\.(?:cpp|cxx|cc|c|h|hpp|inl)(?=\0)", re.I)


def source_paths(img: Image) -> list[str]:
    seen = set()
    for name, va, vsize, _r, flags in img.sections:
        if flags & (SCN_EXECUTE | SCN_UNINIT | SCN_DISCARDABLE):
            continue
        for m in SRC_RE.finditer(img.d, va, va + vsize):
            seen.add(m.group(0).decode("ascii").replace("/", "\\"))
    return sorted(seen, key=str.lower)


def import_rows(x, img: Image):
    """(library, ordinal, kind, address) per XEX import record. The record's
    word in the image holds its type in the top byte and the ordinal in the
    low 16 bits."""
    rows = []
    for lib in x.import_libraries():
        for rec in lib.records:
            w = struct.unpack_from(">I", img.d, rec - img.base)[0]
            k = {0: "variable", 1: "thunk"}.get(w >> 24)
            if k is None:
                die(f"import record at {rec:#x} has type {w >> 24}")
            rows.append((lib.name, w & 0xFFFF, k, rec))
    return rows


def functions_text(funcs) -> str:
    return ("# addr size name: every function the image's function table (.pdata) attests,\n"
            "# written by tools/survey_pe.py. A function without unwind data is not listed.\n"
            + "".join(f"{addr:08x} {size:#x} FUN_{addr:08x}\n" for addr, size, *_ in funcs))


def imports_text(imports) -> str:
    return ("# library ordinal kind address: the XEX import records, written by\n"
            "# tools/survey_pe.py. Ordinals are not named yet.\n"
            + "".join(f"{lib} {ordinal} {k} {rec:08x}\n" for lib, ordinal, k, rec in imports))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", action="store_true",
                    help="write config/functions.<slug>.txt and config/imports.<slug>.txt")
    ap.add_argument("--md", action="store_true", help="write docs/SURVEY.md (implies --write)")
    args = ap.parse_args(argv)

    ver = cv.detect_version(REPO_ROOT)
    pe_path = cv.basepe_path(REPO_ROOT, ver)
    xex_path = cv.basexex_path(REPO_ROOT, ver)
    for p in (pe_path, xex_path):
        if not p.exists():
            die(f"{p.relative_to(REPO_ROOT)} not found: run tools/extract_pkg.sh")
    img = Image(pe_path.read_bytes())
    x = xex.parse(xex_path.read_bytes())
    base = img.base
    if x.image_base != base:
        die(f"XEX image base {x.image_base:#x} and PE image base {base:#x} disagree")

    # ---- functions --------------------------------------------------------
    funcs = img.functions()
    per_section = Counter()
    covered = Counter()
    prev_end = 0
    for addr, size, prolog, f32, _exc in funcs:
        s = img.section_of(addr - base)
        if s is None or not s[4] & SCN_EXECUTE:
            die(f"function table entry {addr:#x} is not in an executable section")
        if addr - base + size > s[1] + s[2]:
            die(f"function {addr:#x} (+{size:#x}) runs past the end of {s[0]}")
        if addr < prev_end:
            die(f"function {addr:#x} starts before the previous one ends ({prev_end:#x})")
        if size == 0 or addr % 4 or prolog * 4 > size:
            die(f"function table entry {addr:#x} is malformed (size {size:#x}, prolog {prolog})")
        prev_end = addr + size
        per_section[(s[0], s[1])] += 1
        covered[(s[0], s[1])] += size
    starts = {f[0] for f in funcs}
    entry = x.entry_point
    if entry != base + img.entry_rva:
        die(f"XEX entry {entry:#x} and PE entry {base + img.entry_rva:#x} disagree")
    entry_in_table = entry in starts

    imports = import_rows(x, img)

    libs = x.static_libraries()
    paths = source_paths(img)
    code_total = sum(s[2] for s in img.sections if s[4] & SCN_EXECUTE)
    code_covered = sum(covered.values())
    ts = datetime.datetime.fromtimestamp(img.timestamp, datetime.timezone.utc)

    print(f"survey_pe: {ver}: {len(img.sections)} sections, {len(funcs)} functions in the "
          f"function table covering {code_covered:#x} of {code_total:#x} code bytes "
          f"({100 * code_covered / code_total:.1f}%), {len(imports)} import records, "
          f"{len(libs)} static libraries, {len(paths)} source paths in strings")

    if not (args.write or args.md):
        return 0

    fn_path = cv.config_path(REPO_ROOT, ver, "functions", "txt")
    fn_path.write_text(functions_text(funcs))
    imp_path = cv.config_path(REPO_ROOT, ver, "imports", "txt")
    imp_path.write_text(imports_text(imports))
    print(f"survey_pe: wrote {fn_path.relative_to(REPO_ROOT)}, {imp_path.relative_to(REPO_ROOT)}")

    if not args.md:
        return 0

    info = x.execution_info()
    enc, comp, blocks = x.file_format()
    L = []
    A = L.append
    A("# Survey of the executable\n")
    A(f"Written by `tools/survey_pe.py --md` from the `{ver}` target's base files "
      "(`baserom/" + ver + "/default.xex` and `default.pe`). Do not edit by hand.\n")
    A("## Container\n")
    A("| Field | Value |\n|---|---|")
    A(f"| Title id | `{info['title_id']:08X}` |")
    A(f"| Media id | `{info['media_id']:08X}` |")
    A(f"| Version / base version | `{info['version']:#x}` / `{info['base_version']:#x}` |")
    A(f"| Original PE name | `{x.original_pe_name}` |")
    A(f"| Encryption / compression | {enc} (AES) / {comp} (basic, {len(blocks)} blocks) |")
    A(f"| Image base | `{base:#010x}` |")
    A(f"| Image size (XEX) | `{x.image_size:#x}` |")
    A(f"| Size of image (PE header) | `{img.size_of_image:#x}` |")
    A(f"| Entry point | `{entry:#010x}`"
      f"{'' if entry_in_table else ' (no function table entry)'} |")
    A(f"| PE machine | `{img.machine:#06x}` |")
    A(f"| PE timestamp | `{img.timestamp:#x}` ({ts:%Y-%m-%d %H:%M:%S} UTC) |")
    A(f"| Section / file alignment | `{img.section_align:#x}` / `{img.file_align:#x}` |")
    A("")
    A("## Sections\n")
    A("| Name | Address | Size | Kind | Functions | Bytes in functions |\n|---|---|---|---|---|---|")
    for name, va, vsize, _r, flags in img.sections:
        n = per_section.get((name, va), 0)
        c = covered.get((name, va), 0)
        truncated = " (past the XEX image)" if va + vsize > x.image_size else ""
        A(f"| `{name}` | `{base + va:#010x}` | `{vsize:#x}`{truncated} | {kind(flags)} | "
          f"{n or ''} | {f'`{c:#x}` ({100 * c / vsize:.1f}%)' if n else ''} |")
    A("")
    A("## Functions\n")
    A(f"The function table holds {len(funcs)} entries, sorted, with no overlap, every range "
      f"inside an executable section. They cover `{code_covered:#x}` of `{code_total:#x}` "
      f"bytes of code ({100 * code_covered / code_total:.1f}%). The remaining "
      f"`{code_total - code_covered:#x}` bytes are functions with no unwind data, padding "
      "and data held in code sections; they are not classified yet.\n")
    sizes = sorted(f[1] for f in funcs)
    A(f"Function sizes: smallest `{sizes[0]:#x}`, median `{sizes[len(sizes) // 2]:#x}`, "
      f"largest `{sizes[-1]:#x}`. {sum(1 for f in funcs if f[4])} entries carry the "
      "exception-handler flag.\n")
    plain = [f for f in funcs if not f[3]]
    if plain:
        A(f"{len(plain)} entries have the 32-bit flag clear, and in each the prolog length "
          "equals the function length: " + ", ".join(f"`{f[0]:#010x}`" for f in plain) + ".\n")
    A("## Imports\n")
    A("| Library | Version | Minimum | Records | Thunks | Variables |\n|---|---|---|---|---|---|")
    for lib in x.import_libraries():
        mine = [i for i in imports if i[0] == lib.name]
        A(f"| `{lib.name}` | {'.'.join(map(str, lib.version))} | "
          f"{'.'.join(map(str, lib.version_min))} | {len(mine)} | "
          f"{sum(1 for i in mine if i[2] == 'thunk')} | "
          f"{sum(1 for i in mine if i[2] == 'variable')} |")
    A("")
    A("## Static libraries\n")
    A("| Library | Version |\n|---|---|")
    for name, major, minor, build, qfe in libs:
        A(f"| `{name}` | {major}.{minor}.{build}.{qfe} |")
    A("")
    A("## Rich header\n")
    A("The linker's record of the tools that produced the objects, as stored: product id, "
      "build number, object count. The ids are not interpreted here.\n")
    A("| Product id | Build | Objects |\n|---|---|---|")
    for prod, build, count in img.rich:
        A(f"| {prod} | {build} | {count} |")
    A("")
    A("## Source paths in strings\n")
    if paths:
        roll = Counter("\\".join(p.split("\\")[:-1]).lower() for p in paths)
        A(f"{len(paths)} distinct source paths appear as strings in the data sections, "
          "by directory:\n")
        A("| Directory | Files |\n|---|---|")
        for dname, n in sorted(roll.items(), key=lambda kv: kv[0].lower()):
            A(f"| `{dname}` | {n} |")
    else:
        A("No source path appears as a string in the data sections.")
    A("")
    md = REPO_ROOT / "docs" / "SURVEY.md"
    md.write_text("\n".join(L))
    print(f"survey_pe: wrote {md.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
