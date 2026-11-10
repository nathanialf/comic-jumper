#!/usr/bin/env python3
"""
check_pe.py: the gate and the progress files.

    check_pe.py --gate       exit non-zero unless the tree agrees with the base
    check_pe.py --progress   rewrite docs/<slug>/PROGRESS.md,
                             docs/<slug>/progress.json and README.md's block

Survey stage. The gate checks what the tree claims today:

  1. config/functions.<slug>.txt and config/imports.<slug>.txt equal, byte
     for byte, what tools/survey_pe.py derives from the user's base files
     (the image's own function table and the XEX import records).
  2. config/matched.<slug>.txt holds no row. There is no compiler and no
     compare step yet (docs/DECISIONS.md D1), so a claimed match cannot be
     checked, and an unchecked claim fails the gate.

The compare step joins here when D1 is decided: each matched row compiled and
compared with the base at its address.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cj_version as cv  # noqa: E402
import survey_pe  # noqa: E402
import xex  # noqa: E402

VERSION = cv.detect_version(REPO_ROOT)
README = REPO_ROOT / "README.md"
PROGRESS_DOC = cv.docs_dir(REPO_ROOT, VERSION) / "PROGRESS.md"
PROGRESS_JSON = cv.docs_dir(REPO_ROOT, VERSION) / "progress.json"
DASHBOARD = "https://nathanialf.github.io/comic-jumper/"
BEGIN, END = "<!-- progress:begin -->", "<!-- progress:end -->"


def load():
    img = survey_pe.Image(cv.basepe_path(REPO_ROOT, VERSION).read_bytes())
    x = xex.parse(cv.basexex_path(REPO_ROOT, VERSION).read_bytes())
    return img, x


def matched_rows() -> list[str]:
    p = cv.config_path(REPO_ROOT, VERSION, "matched", "txt")
    if not p.exists():
        return []
    return [ln for ln in p.read_text().splitlines()
            if ln.strip() and not ln.lstrip().startswith("#")]


def run_gate() -> int:
    img, x = load()
    ok = True
    derived = (("functions", survey_pe.functions_text(img.functions())),
               ("imports", survey_pe.imports_text(survey_pe.import_rows(x, img))))
    for stem, text in derived:
        p = cv.config_path(REPO_ROOT, VERSION, stem, "txt")
        rel = p.relative_to(REPO_ROOT)
        rows = text.count("\n") - 2
        if not p.exists():
            print(f"check_pe: FAIL {rel} is missing (tools/survey_pe.sh writes it)")
            ok = False
        elif p.read_text() != text:
            print(f"check_pe: FAIL {rel} differs from what the base attests")
            ok = False
        else:
            print(f"check_pe: ok   {rel}: {rows} rows equal the base")
    rows = matched_rows()
    if rows:
        print(f"check_pe: FAIL config/matched.{VERSION}.txt claims {len(rows)} functions and "
              "there is no compare step to check them (docs/DECISIONS.md D1)")
        ok = False
    else:
        print("check_pe: ok   no function is claimed as matched (survey stage)")
    print(f"check_pe: gate {'PASSED' if ok else 'FAILED'} ({VERSION})")
    return 0 if ok else 1


def build_tree() -> dict:
    img, _x = load()
    funcs = img.functions()
    code_total = sum(s[2] for s in img.sections if s[4] & survey_pe.SCN_EXECUTE)
    ranges: dict[int, list] = {}
    for addr, size, *_ in funcs:
        s = img.section_of(addr - img.base)
        ranges.setdefault(addr >> 20, []).append(
            {"name": f"FUN_{addr:08x}", "addr": f"0x{addr:08X}", "size": size,
             "section": s[0], "matched": False})
    tus = []
    for hi in sorted(ranges):
        fs = ranges[hi]
        name = f"0x{hi << 20:08x}-0x{(hi << 20) | 0xFFFFF:08x}"
        tus.append({"name": name, "path": f"unassigned/{name}", "matched_funcs": 0,
                    "total_funcs": len(fs), "matched_bytes": 0,
                    "total_bytes": sum(f["size"] for f in fs), "funcs": fs})
    fn_bytes = sum(f[1] for f in funcs)
    return {
        "schema": 2,
        "version": VERSION,
        "totals": {
            "matched_funcs": 0, "total_funcs": len(funcs), "stub_funcs": 0,
            "matched_bytes": 0, "total_bytes": code_total,
            "sections": {".text": [0, code_total]},
            "extracted": {".text": 0},
            "nobits_sections": [],
            "sections_from_symbols": {".text": [0, fn_bytes]},
        },
        "programmers": [{
            "name": "unassigned", "matched_funcs": 0, "total_funcs": len(funcs),
            "matched_bytes": 0, "total_bytes": fn_bytes, "tus": tus,
            "note": ("functions no source file claims yet, in 1 MiB address ranges; "
                     "a function moves to its TU's group when it is matched"),
        }],
    }


def _fmt_pct(m: int, t: int) -> str:
    return "-" if t == 0 else f"{100.0 * m / t:.2f} %"


def _badge_color(m: int, t: int) -> str:
    if t == 0:
        return "lightgrey"
    pct = 100.0 * m / t
    for floor, color in ((100.0, "brightgreen"), (75.0, "green"),
                         (50.0, "yellowgreen"), (25.0, "yellow")):
        if pct >= floor:
            return color
    return "orange" if pct > 0.0 else "red"


def _badge(label: str, m: int, t: int) -> str:
    from urllib.parse import quote
    msg = quote(_fmt_pct(m, t), safe="").replace("-", "%2D")
    url = f"https://img.shields.io/badge/{label}-{msg}-{_badge_color(m, t)}.svg"
    return f"![{label} progress]({url})"


def _badges(t: dict) -> str:
    code = t["sections"][".text"]
    return " ".join([_badge("code", code[0], code[1]),
                     _badge("functions", t["matched_funcs"], t["total_funcs"])])


def _table(tree: dict) -> str:
    t = tree["totals"]
    code = t["sections"][".text"]
    fb = t["sections_from_symbols"][".text"]
    lines = ["| Measure | Matched | Total | % |", "| --- | ---: | ---: | ---: |",
             f"| functions | {t['matched_funcs']} | {t['total_funcs']} | "
             f"{_fmt_pct(t['matched_funcs'], t['total_funcs'])} |",
             f"| bytes in functions | {fb[0]} | {fb[1]} | {_fmt_pct(fb[0], fb[1])} |",
             f"| code section bytes | {code[0]} | {code[1]} | {_fmt_pct(code[0], code[1])} |",
             "",
             "The project is at the survey stage: no function is compiled or compared yet "
             "(`docs/DECISIONS.md`, D1). The function list and sizes come from the "
             "executable's own function table (`tools/survey_pe.py`, "
             f"`config/functions.{VERSION}.txt`); the code row's total is every executable "
             "section of the image, including functions the table does not list and the "
             "bytes between functions.",
             "", "| Group | Matched functions | Total | Matched bytes | Total bytes |",
             "| --- | ---: | ---: | ---: | ---: |"]
    for p in tree["programmers"]:
        lines.append(f"| `{p['name']}` | {p['matched_funcs']} | {p['total_funcs']} | "
                     f"{p['matched_bytes']} | {p['total_bytes']} |")
    return "\n".join(lines)


PROGRESS_SKELETON = """# Progress: {name}

How much of the executable is rebuilt from source and matches. Generated by
`tools/check_pe.py --progress`; the dashboard is `docs/index.html`.

<!-- progress:begin -->
<!-- progress:end -->
"""


def _readme_block(tree: dict) -> str:
    rows = {}
    for js in sorted((REPO_ROOT / "docs").glob("*/progress.json")):
        slug = js.parent.name
        if slug == VERSION:
            continue
        try:
            rows[slug] = json.loads(js.read_text())["totals"]
        except (OSError, ValueError, KeyError):
            continue
    rows[VERSION] = tree["totals"]
    order = sorted(rows, key=lambda v: (cv.VERSIONS.index(v) if v in cv.VERSIONS
                                        else len(cv.VERSIONS), v))
    lines = ["| Target | Matched |", "| --- | --- |"]
    for slug in order:
        lines.append(f"| [{cv.pkg_name(slug) or slug}]({DASHBOARD}#{slug}) | "
                     f"{_badges(rows[slug])} |")
    return "\n".join(lines)


def _splice(path: Path, body: str) -> bool:
    text = path.read_text()
    if BEGIN not in text or END not in text:
        sys.exit(f"check_pe: {path} has no {BEGIN} / {END} markers")
    pat = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END), re.DOTALL)
    new = pat.sub(lambda _: BEGIN + "\n" + body + "\n" + END, text)
    if new == text:
        return False
    path.write_text(new)
    return True


def run_progress() -> int:
    tree = build_tree()
    t = tree["totals"]
    print(f"progress ({VERSION}): {t['matched_funcs']}/{t['total_funcs']} functions, "
          f"{t['matched_bytes']}/{t['total_bytes']} code bytes "
          f"({_fmt_pct(t['matched_bytes'], t['total_bytes'])})")
    if not PROGRESS_DOC.exists():
        PROGRESS_DOC.parent.mkdir(parents=True, exist_ok=True)
        PROGRESS_DOC.write_text(PROGRESS_SKELETON.format(name=cv.pkg_name(VERSION)))
    for path, body in ((README, _readme_block(tree)), (PROGRESS_DOC, _table(tree))):
        print(f"check_pe: {'rewrote' if _splice(path, body) else 'unchanged'} "
              f"{path.relative_to(REPO_ROOT)}")
    PROGRESS_JSON.write_text(json.dumps(tree, separators=(",", ":")) + "\n")
    print(f"check_pe: wrote {PROGRESS_JSON.relative_to(REPO_ROOT)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--gate", action="store_true")
    mode.add_argument("--progress", action="store_true")
    args = ap.parse_args()
    for p in (cv.basepe_path(REPO_ROOT, VERSION), cv.basexex_path(REPO_ROOT, VERSION)):
        if not p.exists():
            sys.exit(f"check_pe: {p.relative_to(REPO_ROOT)} not found; run ./build.sh")
    return run_gate() if args.gate else run_progress()


if __name__ == "__main__":
    sys.exit(main())
