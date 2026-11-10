# Matching a function

The unit of work will be one function of the base executable
(`config/functions.retail.txt`: address, size, name), the claim a row in
`config/matched.retail.txt`, and the proof `tools/check_pe.py --gate`.

**This stage has not started.** There is no compiler yet
(`docs/DECISIONS.md`, D1), so there is no compile step, no compare step and
no source under `src/`. The gate fails on any row in
`config/matched.retail.txt`, because a claim it cannot check is not a claim.

What is settled now, so the first function is written toward it:

## The method

The method is the one the sibling ICO and The Last Guardian projects
converged on, and it binds every matching session once D1 is decided.

- Recover the data model and the function's purpose before the first diff.
- Work divergences in the function's own order, one claim at a time, each
  sourced and checked.
- Reason, predict, compile once; when the prediction fails, fix the model.
  Many compiles on one divergence means the model is wrong.
- Structure over count: the shape of the code matters more than the number
  of differing instructions.
- No stall gate, no skip, no floor. A function is worked until it matches.
- The compiler and its flags are fixed inside the loop. A suspected compiler
  residual is a classified note and a question about a whole region, never a
  per-function flag.

## Crutches

Code is what a developer at the studio in 2008 to 2010 would have written to
express what it does. Nothing may exist only to steer the compiler: no
register pins, no empty or register-only inline assembly, no dead stores, no
orphan locals, no per-function pragmas or attributes, no declaration tricks,
no block scope that exists to move a live range. The test is whether the
construct emits no bytes of its own and exists to change codegen; the list
is not exhaustive. `tools/check_dev_native.py` enforces part of it in the
pre-commit hook, and `tools/dev_native_allow.txt` holds ruled exceptions with
their evidence.

## Names

The executable has no symbols. A name taken from a string, RTTI or an import
is a fact and may be used; a name invented from context carries
`/* derived name */` on its definition line. A function with no name yet is
`FUN_<addr>`, its row in `config/functions.retail.txt`.

## Looking at a function today

```sh
.venv/bin/python -I tools/disasm.py FUN_82120000
.venv/bin/python -I tools/disasm.py 0x822a6370 0x822a63a0
```

`tools/disasm.py` reads the image, a flat file whose offsets are addresses
minus `0x82000000` (`docs/TARGETS.md`), and decodes it with capstone. A word
capstone cannot decode is printed as `.long` and counted. How much of the
executable a public disassembler decodes is one of the measurements D1 asks
for.
