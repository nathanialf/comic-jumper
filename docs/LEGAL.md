# Legal notes

What this repository may contain, what it must never contain, and which
references its source is written from.

This is a community decompilation project. It is not affiliated with,
endorsed by, or sponsored by Twisted Pixel Games, Microsoft Corporation, or
any of their affiliates. *Comic Jumper*, *Xbox 360* and *Xbox Live Arcade* are
trademarks of their respective owners.

## What is in this repository

- Build scripts and tooling written for this project.
- Documentation written for this project.
- Configuration that describes how the user's own package is checked: the
  SHA-256s of the expected files (`config/sha256sums.retail.txt`), the list of
  the executable's functions as address, size and name
  (`config/functions.retail.txt`), and its import records as library, ordinal,
  kind and address (`config/imports.retail.txt`).
- The survey of the executable's structure (`docs/SURVEY.md`): headers,
  section sizes, counts, the libraries it was linked with and imports, and the
  directories of the source files that the executable names in its strings.
  Those are facts about the file, in the way a linker map's addresses are.
- Later: C++ source written for this project that compiles into functions
  matching the game's executable.

## What is not in this repository, and must never be added

- The game package or any file from it, in whole or in part: `default.xex`,
  the `.xpr` resource archives, the `.bik` videos, the wave bank, the
  marketplace images and metadata, the two packages it embeds.
- The executable in any form, XEX or PE image, or any part of its bytes.
- Audio, images, textures, models, shaders, text or other assets from the
  package.
- The game's data tables (next section).
- Symbol tables, strings or other identifier tables, and any debug string,
  asset or code blob, copied verbatim or in bulk out of the executable or the
  package. Using an individual fact (a name, an offset, a `__FILE__` path) as
  a reference is covered under "Identifiers as references" below; this item
  forbids copying a table of them into the repository.
- Any code believed to derive from leaked source, a leaked SDK, or a leaked
  SDK header.

`.gitignore` and `tools/check_no_rom.sh` (run by the pre-commit hook) make it
harder to commit such material by accident. They do not replace care. If you
suspect a file in this repository breaks these rules, open an issue tagged
`legal`.

## Data

The game's content lives in the package's resource archives and in the data
sections of the executable (tables, strings, shader binaries). None of it is
committed in any form, as C++, as assembly or otherwise. The build does not
reproduce any data section yet; when it does, data-only ranges will be
generated at build time from the user's own executable, as the sibling ICO
and The Last Guardian projects do, with only types, counts and names
committed. A count or size derived from a table is an ordinary fact about it.

## Public reverse-engineering material (allowed as references)

Published reverse-engineering material may be consulted as a reference for
naming and structure: conference talks, blog posts and articles, public
analysis projects with clear non-leaked provenance, public descriptions of
the file formats (STFS, XEX2, the PE function table), and academic papers on
PowerPC code generation. Treat them like academic papers: read, understand,
then re-derive from the disassembly. Never paste their code, comments or
symbol names into this repository.

Public source code under an open licence is used the same way. The container
readers here were written against two such references and cite them:
Velocity's STFS reader (`tools/extract_pkg.py`) and Xenia's XEX2 structures
(`tools/xex.py`).

## The XEX2 retail key

`tools/xex.py` holds one 16-byte constant, the retail XEX2 key. It is the
same for every retail Xbox 360 title: it is not a console's key and not this
game's. The loader uses it to unwrap the per-file session key stored in an
executable's header, and that session key decrypts the image. The constant is
published in open-source software, for example Xenia
(`src/xenia/cpu/xex_module.cc`, `xe_xex2_retail_key`), and the tool cites that
file. With it the build reads the user's own package and nothing else is
needed. It decrypts only what the user already holds, and the decrypted image
stays under gitignored `baserom/`.

## Identifiers as references: facts, not expression

Facts observable in a copy you legally own (function and symbol names, struct
field offsets and sizes, array strides, `__FILE__` paths in the executable's
strings, the tool versions in its headers) are not copyrightable expression.
They may inform original code: read, understand, re-derive. Never commit the
source artifact, and never paste a table of identifiers in bulk.

- **Allowed:** reading the legally owned executable, or a public decomp of
  sound provenance, and re-deriving names and shapes into your own code.
- **Forbidden:** committing the package, the executable, asset bytes, or a
  symbol, string or debug table in whole or in bulk; and any use of leaked
  source, leaked SDKs, or leaked prototype or debug builds (below). A retail
  copy you own is never in that category.

## Forbidden inputs

These may never be used as inputs to this project, even indirectly:

- Microsoft's Xbox 360 SDK (the XDK), its headers, libraries, compiler,
  linker or documentation, in any version, however obtained. The XDK was
  licensed to registered developers only; this project has no such licence
  and uses none of it. The compiler question this leaves open is
  `docs/DECISIONS.md` D1.
- Leaked source code from any party, including any of Twisted Pixel's titles,
  however obtained.
- Leaked prototype or debug builds of the game, and symbol files (`.pdb`,
  `.xdb`, `.map`) that did not ship in the retail package.
- Paid asset extractors that bundle game data.

If you have ever read any of the above, say so on your first pull request so
your contributions can be reviewed for provenance.

## The package and the executable (`retail`)

The target is the Xbox Live Arcade retail package, title id `58410A20`,
version `0x101`. The build reads the user's own copy: its header, to check
the title id, version and media id; `default.xex`, to decrypt and expand to
the image the console loads, to hash and to compare against. Every file in
the package is extracted with it and none of the others is read.
`tools/extract_pkg.sh` writes everything under gitignored `baserom/`.

The executable carries no symbol table. Its imports are ordinals. Names in
this tree come from facts in the executable (assert and log strings, class
names in RTTI, the function table) or are derived and marked
`/* derived name */`. No address is copied from any file other than the
user's own executable: every address in `config/*.retail.*` was found in it
by `tools/survey_pe.py`.

## What you need to build

You must legally own a copy of *Comic Jumper* and supply the package
yourself. The build checks the package's and the executable's SHA-256 before
it proceeds and refuses any other file (`config/sha256sums.retail.txt`,
`docs/BUILDING.md`). A SHA-256 is a fingerprint, not a copy of the work; the
package and the executable remain the property of their rightsholders.

This project gives no instructions for obtaining a package or copying one
off a console. The only legitimate source is a personal copy of a game you
own, made in compliance with the law where you live.

## Why decompilation projects can exist

Projects of this kind have a long history (Super Mario 64, Ocarina of Time,
Majora's Mask, Paper Mario, Sly Cooper, Jak and Daxter, Kingdom Hearts, ICO
and many more). They produce original source code by reverse engineering,
distribute no copyrighted assets, and require users to bring their own copy.
This project follows the same model.

If you represent a rightsholder and have a concern, please open a GitHub
issue.
