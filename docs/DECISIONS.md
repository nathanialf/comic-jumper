# Decisions

The record of every decision that shapes what "matched" means in this tree,
and the standard each one has to meet. A decision here is not revisited by
taste; it is revisited when its stated trigger fires, with the same evidence
standard it was made under. New decisions are appended, never edited in
place; a superseded entry gets a "Superseded by" line.

## The standard

Carried over from the sibling The Last Guardian project, where each rule was
earned.

1. **Evidence from the executable first.** A claim about the original
   compiler, its flags or its libraries is backed by a measurement over the
   whole executable (every function, not the few we have written) or by a
   primary source, cited in `docs/TARGETS.md`. One function's diff is a hint,
   never a justification.
2. **Measured, not argued.** A change to the compiler or to a flag is made
   only with a probe and the gate run before and after. It must not lower the
   score of any function already matched, and it must raise the
   whole-executable agreement it was made for.
3. **Per prefix, never per function.** Flags and the compiler attach to a
   source prefix, with the evidence written beside them. No file-level or
   function-level steering, no pragmas, no attributes that exist to change
   codegen.
4. **No unexplained residue.** A function that will not match is not claimed
   and is not forgotten: its diff is classified and feeds the next decision.
   "Unmatchable" is a classification that must name the compiler mechanism.
5. **Reproduce, do not approximate, when the mechanism is known.**
6. **Nothing lands red.** The pre-commit gate checks every claim the tree
   makes; the hashes of the base files are never edited; a claimed function
   is never un-claimed to pass.

## D0. The target is the retail package (2026-11-10)

**Decision.** The target is the Xbox Live Arcade retail package, title id
`58410A20`, version `0x101`, slug `retail`. An earlier demo build is not a
target and not an input.

**Why.** The maintainer's ruling. The demo was examined in September 2026 for
a symbol map that would have helped a decompilation, was judged not helpful
enough, and was removed; retail is what players own.

**Trigger to revisit.** None planned. A title update or another region would
join as a second target (`docs/TARGETS.md`).

## D1. The compiler (open, 2026-11-10)

**What is fixed.** Public tools only (the maintainer's ruling, 2026-11-10).
The executable was built by the XDK's compiler and linker (`C1`/`C2`
16.0.10224, `LINK` 10.0.10224, read from the XEX's library table), and the
XDK is a forbidden input (`docs/LEGAL.md`). So there is no relink with the
original linker, and the strongest proof available is per function: a
compiled function's instructions equal to the base's at its address, with
only linker-filled fields masked, as in the sibling The Last Guardian tree.

**What is open.** Whether any public compiler reproduces this executable's
code closely enough for that proof to be reachable, and if so which one, at
which version, with which flags. Nothing has been measured yet. The project
stays at the survey stage until this is answered: no source is committed and
no function is claimed (`tools/check_pe.py --gate` fails on a claim).

**How it will be answered.** A probe stage, in this order:

1. Fingerprint the base over every function in `config/functions.retail.txt`:
   prolog and epilog forms (the six register save and restore helpers at
   `0x825E35D0` to `0x825E46A8` and how functions call them), instruction
   frequency, the share of instructions a public disassembler decodes, calling
   convention and stack frame layout.
2. Compile a fixed set of small, unambiguous functions (leaves first) with
   each candidate public compiler that targets big-endian PowerPC, and score
   each against the base with the same comparison the gate will use.
3. Record the scores here. A candidate is adopted only when it reproduces the
   fingerprints over the whole executable; a candidate that matches a handful
   of leaves and misses a whole-executable fingerprint is not adopted.

**Possible outcomes, each a recorded decision.** A public compiler reproduces
the code and matching proceeds as in the sibling trees. A public compiler
reproduces it with documented, mechanism-level patches built from source. No
public compiler does, in which case byte matching is out of reach under the
public-tools ruling and the project's goal is restated (for example a
functionally equivalent source tree checked by behaviour) by the maintainer.

**Trigger to revisit the ruling itself.** The maintainer's decision only.
