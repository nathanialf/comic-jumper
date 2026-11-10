#!/usr/bin/env python3
"""
disasm.py: disassemble a range of the base image.

    disasm.py <function name or address> [<end address>]

    disasm.py FUN_82120000          the function's range from config/functions.<slug>.txt
    disasm.py 0x822a6370 0x822a63a0 an explicit range

Reads baserom/<slug>/default.pe, whose offsets are addresses minus the image
base. capstone decodes big-endian 64-bit PowerPC; a word it cannot decode is
printed as `.long` and counted, so an instruction outside its tables is seen,
never skipped.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cj_version as cv  # noqa: E402
import survey_pe  # noqa: E402


def main(argv: list[str]) -> int:
    if not argv or len(argv) > 2:
        print(__doc__, file=sys.stderr)
        return 2
    import capstone
    ver = cv.detect_version(REPO_ROOT)
    img = survey_pe.Image(cv.basepe_path(REPO_ROOT, ver).read_bytes())
    if len(argv) == 2:
        start, end = int(argv[0], 16), int(argv[1], 16)
    else:
        want = argv[0]
        start = end = None
        for addr, size, *_ in img.functions():
            if want in (f"FUN_{addr:08x}", f"{addr:08x}", f"0x{addr:08x}"):
                start, end = addr, addr + size
                break
        if start is None:
            print(f"disasm: {want} is not a function table entry; give a start "
                  "and an end address", file=sys.stderr)
            return 1
    if start % 4 or end <= start or not (img.base <= start and end - img.base <= len(img.d)):
        print(f"disasm: bad range {start:#x}..{end:#x}", file=sys.stderr)
        return 1
    md = capstone.Cs(capstone.CS_ARCH_PPC, capstone.CS_MODE_64 | capstone.CS_MODE_BIG_ENDIAN)
    unknown = 0
    for a in range(start, end, 4):
        word = img.d[a - img.base:a - img.base + 4]
        insn = next(md.disasm(word, a), None)
        if insn is None:
            unknown += 1
            text = f".long   {struct.unpack('>I', word)[0]:#010x}"
        else:
            text = f"{insn.mnemonic:<7} {insn.op_str}"
        print(f"{a:08x}:  {word.hex()}  {text}")
    if unknown:
        print(f"disasm: {unknown} of {(end - start) // 4} words not decoded", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
