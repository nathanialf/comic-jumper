#!/usr/bin/env python3
"""
check_dev_native.py: refuse source that steers the compiler instead of
expressing what the code does.

The rule (CLAUDE.md, docs/MATCH.md, docs/MATCH.md): a committed
function is what the game's developer would have written in 2008-2010
C++. A crutch is anything that emits no bytes of its own and exists to
change codegen. ICO's campaigns learned that the rule does not hold as
prose: register pins, empty asm barriers, `do { } while (0)` wrappers and
dead stores crept in as "ordinary C" and were retired later at a cost
larger than matching without them. So the checker is mechanical and runs in
the pre-commit hook on every staged source under src/.

Refused, in the staged (or every tracked) source under src/:
  1. inline assembly in any spelling: asm, __asm, __asm__, volatile or not
  2. register pins: `register` storage class, `__asm__("reg")` on a variable
  3. attributes and pragmas that steer codegen: noinline, always_inline,
     flatten, optnone, optimize, hot, cold, noclone, used, naked,
     no_stack_protector, target, minsize, section; #pragma clang/GCC
     optimize|loop|unroll|inline; __builtin_expect, __builtin_assume,
     __builtin_unpredictable, __builtin_prefetch
  4. an empty `do { } while (0)` (or with only a null statement)
  5. `volatile` without a comment on the same line or the line above saying
     what the data model reason is (a value another thread or the hardware
     writes); the reason is the ruling that `volatile` is ordinary C++
  6. a symbol-name alias (`__asm__("name")` on a declaration) and
     `__attribute__((alias))`
  7. compiler-steering keywords through macros that hide them (the checker
     reads the preprocessed-looking text; a macro whose body carries one of
     the tokens above is refused where it is defined)

Allowed and not flagged: alignment (`alignas`, `__attribute__((aligned))`),
`inline`, `static`, `const`, `restrict`-free plain C++, `__m128` and the
intrinsics headers, `#pragma once`, `#pragma pack` (a layout fact, not a
codegen steer).

Exceptions live in tools/dev_native_allow.txt as `<path>:<line-text-prefix>
<reason>`; an allowed site is reported, never silent.

    check_dev_native.py              staged sources (pre-commit), else every tracked source
    check_dev_native.py <file>...    these files
    check_dev_native.py --self-test
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ALLOW = REPO_ROOT / "tools" / "dev_native_allow.txt"
SRC_RE = re.compile(r"^src/.*\.(c|cc|cpp|cxx|h|hpp|inl)$")

RULES = [
    ("inline assembly", re.compile(r"(?<![A-Za-z0-9_])(__asm__|__asm|asm)\s*(volatile\s*|__volatile__\s*)?[\(\{]")),
    ("register pin", re.compile(r"(?<![A-Za-z0-9_])register\s+[A-Za-z_]")),
    ("codegen-steering attribute",
     re.compile(r"__attribute__\s*\(\(\s*(noinline|always_inline|flatten|optnone|optimize|hot|cold|noclone|used|naked|"
                r"no_stack_protector|target|minsize|section|alias|weak|noipa)\b")),
    ("codegen-steering attribute", re.compile(r"\[\[\s*(gnu|clang)::(noinline|always_inline|flatten|optnone|hot|cold|"
                                               r"minsize|section|optimize|noipa)\b")),
    ("codegen-steering pragma", re.compile(r"^\s*#\s*pragma\s+(clang|GCC)\s+(optimize|loop|unroll|inline|push_options|pop_options)\b")),
    ("codegen-steering pragma", re.compile(r"^\s*#\s*pragma\s+(unroll|nounroll|optimize|inline|forceinline|auto_inline|intrinsic|function)\b")),
    ("codegen-steering builtin", re.compile(r"__builtin_(expect|assume|unpredictable|prefetch|unreachable|assume_aligned)\s*\(")),
    ("empty do-while wrapper", re.compile(r"\bdo\s*\{\s*;?\s*\}\s*while\s*\(\s*0\s*\)")),
    ("symbol alias", re.compile(r"\)\s*(__asm__|asm)\s*\(\s*\"")),
    ("hidden forceinline", re.compile(r"(?<![A-Za-z0-9_])__forceinline(?![A-Za-z0-9_])")),
]
VOLATILE_RE = re.compile(r"(?<![A-Za-z0-9_])volatile(?![A-Za-z0-9_])")


def strip_strings(line: str) -> str:
    """Blank out string and char literals so a word inside one is not a hit."""
    return re.sub(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', lambda m: " " * len(m.group(0)), line)


def load_allow() -> list[tuple[str, str, str]]:
    out = []
    if ALLOW.exists():
        for line in ALLOW.read_text().splitlines():
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            loc, _, reason = s.partition(" ")
            path, _, prefix = loc.partition(":")
            out.append((path, prefix, reason))
    return out


def check_file(path: Path, rel: str, allow) -> list[str]:
    problems = []
    try:
        lines = path.read_text(errors="replace").split("\n")
    except OSError as e:
        return [f"{rel}: {e}"]
    in_block_comment = False
    prev_had_comment = False
    for i, raw in enumerate(lines, 1):
        line = raw
        # drop comments (block comments may span lines)
        code = ""
        j = 0
        had_comment = False
        while j < len(line):
            if in_block_comment:
                k = line.find("*/", j)
                had_comment = True
                if k < 0:
                    j = len(line)
                    break
                in_block_comment = False
                j = k + 2
                continue
            if line.startswith("//", j):
                had_comment = True
                break
            if line.startswith("/*", j):
                in_block_comment = True
                had_comment = True
                j += 2
                continue
            code += line[j]
            j += 1
        code = strip_strings(code)
        hits = []
        for name, rx in RULES:
            if rx.search(code):
                hits.append(name)
        if VOLATILE_RE.search(code) and not (had_comment or prev_had_comment):
            hits.append("volatile without a reason in a comment on this line or the line above")
        for name in hits:
            allowed = next((r for p, pre, r in allow if p == rel and raw.strip().startswith(pre)), None)
            if allowed:
                print(f"check_dev_native: ALLOWED {rel}:{i}: {name} ({allowed})")
            else:
                problems.append(f"{rel}:{i}: {name}: {raw.strip()[:100]}")
        prev_had_comment = had_comment
    return problems


def staged_or_tracked() -> list[str]:
    try:
        staged = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
                                cwd=REPO_ROOT, capture_output=True, text=True, check=True).stdout.split()
    except subprocess.CalledProcessError:
        staged = []
    if staged:
        return [f for f in staged if SRC_RE.match(f)]
    tracked = subprocess.run(["git", "ls-files", "--", "src"], cwd=REPO_ROOT,
                             capture_output=True, text=True, check=True).stdout.split()
    return [f for f in tracked if SRC_RE.match(f)]


def self_test() -> int:
    bad = [
        'int f(int x) { __asm__(""); return x; }',
        'int f(int x) { asm volatile("" ::: "memory"); return x; }',
        'register int r asm("rax") = 0;',
        'register int r = 0;',
        '__attribute__((noinline)) void g();',
        '[[gnu::always_inline]] inline void g();',
        '#pragma clang optimize off',
        '#pragma unroll',
        'if (__builtin_expect(x, 0)) {}',
        'do { } while (0);',
        'do { ; } while (0);',
        'void h() __asm__("real_name");',
        'volatile int counter;',
        '__forceinline int q();',
    ]
    good = [
        'struct alignas(16) V { float x[4]; };',
        'typedef float V4 __attribute__((aligned(16)));',
        'inline int add(int a, int b) { return a + b; }',
        '/* the IOP writes this handle */ volatile int handle;',
        '// written by the audio thread\nvolatile int ready;',
        '#pragma once',
        'const char *s = "asm(\\"\\") inside a string is text";',
        'do { step(); } while (0);',
        'static int plain(int x) { return x * 2; }',
    ]
    import tempfile
    ok = True
    with tempfile.TemporaryDirectory() as d:
        for i, text in enumerate(bad):
            p = Path(d) / f"bad{i}.cpp"
            p.write_text(text + "\n")
            if not check_file(p, f"src/t/bad{i}.cpp", []):
                print(f"self-test: NOT refused: {text}")
                ok = False
        for i, text in enumerate(good):
            p = Path(d) / f"good{i}.cpp"
            p.write_text(text + "\n")
            r = check_file(p, f"src/t/good{i}.cpp", [])
            if r:
                print(f"self-test: wrongly refused: {text} -> {r}")
                ok = False
    print("check_dev_native: self-test", "OK" if ok else "FAILED")
    return 0 if ok else 1


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv == ["--self-test"]:
        return self_test()
    files = argv or staged_or_tracked()
    allow = load_allow()
    problems = []
    for f in files:
        p = REPO_ROOT / f
        if p.is_file():
            problems += check_file(p, f, allow)
    if problems:
        print("check_dev_native: REFUSED", file=sys.stderr)
        for pr in problems:
            print(f"  {pr}", file=sys.stderr)
        print("  A construct that emits no bytes and exists to steer the compiler is a crutch;\n"
              "  find the source shape instead (docs/MATCH.md, 'Crutches'). A ruled exception\n"
              "  goes in tools/dev_native_allow.txt with its reason.", file=sys.stderr)
        return 1
    print(f"check_dev_native: OK ({len(files)} source file(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
