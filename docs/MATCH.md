# Matching a function

The unit of work is one function of the base executable
(`config/functions.retail.txt`: address, size, name). The claim is a row in
`config/matched.retail.txt`; the proof is `tools/check_pe.py --gate`. This
document is the method, carried over from the ICO and The Last Guardian
projects' matching campaigns and adapted to this target.
`docs/DECISIONS.md` holds the standard it serves, and
[`FINISHING.md`](FINISHING.md) the end state every function is written
toward from the first one.

## What runs today and what waits

The loop below is the binding method. Its compile and compare steps wait on
the compiler decision (`docs/DECISIONS.md`, D1): there is no compiler under
`tools/cc/`, no `tools/quick_diff.sh`, no `tools/match_check.py`, and the
gate fails on any row in `config/matched.retail.txt`, because a claim it
cannot check is not a claim. Steps 1 and 2 of the loop (pick a function,
recover its data model and purpose) run today with `tools/disasm.py`. The
tool names used below are the ones the sibling projects use and the ones
this tree will ship under when D1 is decided.

## Where a function lives

The executable has 12 code sections (`docs/SURVEY.md`). `.text` holds the
game and the libraries it was linked with; `BINK` is a video codec; the nine
`.embsec_` sections are not attributed yet. Which address ranges of `.text`
belong to which SDK library, and which to the game, is a survey question to
answer before the first function is placed: library code goes under
`src/libs/<library>/`, the game's under `src/game/`, each prefix with its
compiler and flags in `config/flags.retail.txt`. The game's own sources name
no file in a string, so a function with no placing evidence goes in the
prefix's `unknown/`, one function per file, until a string, a vtable or a
caller places it.

## The loop

1. **Pick a function.** `docs/retail/progress.json` and the dashboard show
   what is unclaimed; take the smallest unmatched one in the region being
   worked and stay on it until it matches. Parked functions are in the queue
   like any other.

2. **Recover the data model and the purpose before the first diff.** Read
   the function's disassembly (`tools/disasm.py`) and its callers and
   callees. Name what each offset means, find the same offsets in sibling
   functions, learn the callees' real signatures from their bodies, and state
   in one line what the function does. The developer wrote toward that
   purpose in 2008 to 2010 C++ with the studio's engine idioms and the SDK's
   types, not toward a diff.

3. **Write the C++ as the developer would have.** Typed members, not offset
   casts; the engine's own types in `src/include/`, grown one verified field
   at a time (offset and width from the load or store that touches it).
   Callees are `FUN_<addr>` until named, data `D_<hex>`: both are facts the
   gate checks. A table's content is generated at build time from the user's
   executable, never typed. A constructor is written as a constructor; a
   vtable is the compiler's. A name taken from a string, RTTI or an import is
   a fact; a name invented from context carries `/* derived name */`.

4. **Diff, then reason.** `tools/quick_diff.sh <tu> <function>` compiles the
   TU with the prefix's compiler and flags and prints the first differing
   instruction with context on each side, plus any relocation whose target
   the base contradicts. Work the divergences in the function's own order:
   the first one first, because everything before it is proven context, and
   the second does not exist until the first is resolved. For each: state the
   claim (which compiler decision produced the base's form and what source
   property drives it), name the source for it (the compiler's code, its
   dumps on your TU, the base's own bytes), then change the one semantic
   property and predict the output before compiling. Compile once. If the
   prediction was wrong, fix the model, not the spelling. More than about six
   compiles on one divergence means spraying; stop and derive.

5. **Claim it.** When `quick_diff` reports equal with every target verified,
   add `<function> <tu> [<symbol>]` to `config/matched.retail.txt`,
   `tools/build.sh regen` if the TU is new, then `./build.sh`. The gate is
   the only truth: `quick_diff` compares an isolated object and can pass a
   function the layout then refutes. Commit; the pre-commit hook runs the
   gate and refreshes the progress files.

6. **Rename when known.** A real name replaces the `FUN_` row in
   `config/functions.retail.txt`, the `matched` row drops its third column,
   and the file moves out of `unknown/`.

## What counts as a hypothesis

A change the compiler can see: a type (int or struct or union or pointer),
aliasing (which pointers may alias, `const`), liveness (what is live across
which call), factoring (inline helper or out-of-line call, same TU or not),
the algorithm, the control-flow shape, the signature (parameter count and
types, `this` or free function, return by value through a hidden pointer).
Respellings the front end folds to the same form (`if`/`else` versus a
ternary, `a == 3` versus `3 == a`, a named temporary versus an inline
expression) are one hypothesis in several costumes and are not tried. When
every variant gives the same result, the axis is wrong, not the number of
tries.

Derive before compiling on a large function: from the base's bytes compute
what the compiler must have been given (which values were in registers at
which call, which loads were hoisted, which stores merged), solve backward
to the source conditions on paper, then compile to verify, three compiles a
round at most, each with its prediction written first.

## Structure over count

The score (the share of equal instructions) is a byproduct. What converges
is structure: a register-allocation, scheduling or store-merging class
snapping into the base's form, often raising the raw count while a
neighbouring class is disturbed, then collapsing in a group when the
upstream cause lands. Keep an edit that makes a class match or fixes a
whole-function property even when the count rises; keep a
structurally-forward state as the working base even when a lower-count state
exists; never select a branch on count. The size of the function against the
base's is a hard signal: an edit that moves it away is a regression whatever
else improves.

## Crutches

A crutch is anything that emits no bytes of its own and exists to steer the
compiler instead of expressing what the code does. The ban is a test and the
list is not exhaustive: register pins, empty or register-only inline
assembly, dead stores after the last read, orphan carrier locals, pragmas or
attributes that change codegen, `volatile` applied to a value the program
never treats as volatile, a declaration trick that changes the calling
convention, a block scope or storage class that exists only to move a live
range. Each is spelled as ordinary C++ and each is the same crutch renamed.
A barrier may be used once as a throwaway diagnostic to prove a body is
reachable, then reproduced in real code before anything is saved.
Legitimate: `volatile` on data the program's own logic treats as volatile (a
value another thread or the hardware writes), with its reason in a comment;
a store to a real field; the engine's own idioms. The question to ask of
every line: would the game's developer have written this to express what the
function does? `tools/check_dev_native.py` refuses the spellings a tool can
see in the pre-commit hook; the rest is the reviewer's test, and a new
spelling that gets through joins the tool's list.
`tools/dev_native_allow.txt` holds ruled exceptions with their evidence.

## The compiler is fixed inside the loop

Within the matching loop the compiler and the flags of the prefix are fixed
and correct, and a residual is a source shape not yet found. "This compiler
would never emit that order", "needs a different release", "a flag the
developer used" are not conclusions a function can reach on its own: the
compiler is chosen and the flags set from measurements over the whole
executable (`docs/DECISIONS.md`), and one function's diff is a hint about
that evidence, never a verdict. No flag is ever tried per file or per
function; `config/flags.retail.txt` is per prefix and changes only under the
standard. Flags enabled crutches in ICO's early campaigns more often than
they found a source shape, so a flag or compiler change is accepted only
when it is one emission rule narrower than any source form, the source-form
alternatives were tried and excluded by bytes, a region-wide census shows the
base never deviates, and the mechanism is read in the compiler's own source.
When a residual is believed to be the compiler's, the finding goes to
`docs/NOTES.md` as a classified mechanism (which decision, which input, the
base's bytes, what was compiled) with the function left unclaimed, and the
question is decided across the region, not inside the round. A matched
sibling of the same shape under the same flags is the usual proof that the
shape exists.

## Talk to the compiler

When D1 picks a compiler whose source is public, it is staged under
`tools/cc/src/` and read first-party when a divergence resists: state the
pass's required input as a predicate over its own variables, mark each
condition satisfied or not on the current TU from the compiler's dumps, and
derive backwards from the unsatisfied condition to the source construct that
establishes it. A decisive fact is usually one line of compiler source that
no amount of inference from the output would have surfaced.

## Evidence discipline

- A claim becomes a fact with independent sources: the compiler's code, a
  dump of your own TU, the base's own bytes. One source is a hypothesis and
  is labelled as one.
- Pre-register the falsifier before adopting a reading; a probe that
  satisfies one instrument and contradicts another is the false positive this
  method keeps catching.
- A corrected premise retracts every conclusion built on it; re-open them
  explicitly and record the re-opening.
- A fitted regularity is one-directional until the converse is tested on a
  case where the left side holds and the right does not.
- Record mechanisms and measurements, never prohibitions. "The hoist happens
  unconditionally under this source, dumps attached" is durable; "therefore
  do not look for a shape that stops it" freezes a solvable class. Say what
  was compiled; a model-derived closure with nothing compiled is labelled so.
- Re-derive any number you rely on this session; an inherited gate that was
  never measured has been wrong before.

## When a round ends without a match

There is no stall gate, no skip and no floor. A function that did not match
in one worker's context is resumed by a fresh one from the saved state: the
TU at its best structure-forward form, a round entry in `docs/NOTES.md`
naming what landed, the exact residual as a map (classes, sizes, the
mechanism measured for each) and the next reasoned lead, never a list of
failed spellings and never an instruction not to try. The function is never
claimed until the gate passes; `unknown/` keeps the work in progress with a
`// NONMATCHING: <residual>` comment on the definition so the tree compiles
and the dashboard counts it unmatched.

## Codify what is learned

When a landing used a mechanism the local cookbook (`docs/COOKBOOK.md`,
gitignored) does not hold, add one entry: the base's shape, the source form
that produced it, the compiler mechanism with its source location. A landing
that reused known mechanisms needs nothing. A tooling or layout fact goes to
`docs/NOTES.md`. The cookbook is what the next worker greps before writing
C++ for the same shape.

## Roles

A hard function is worked by a supervisor and one worker at a time: the
supervisor never grinds the function itself, measures every result itself
and treats a worker's report as a claim to check, and relaunches a fresh
worker on the same function from the saved state. The local
`.claude/skills/decomp-convergence/` holds both roles and the worker brief;
`.claude/CHAIN_BRIEFS.md` describes how ICO's chains were briefed.

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
