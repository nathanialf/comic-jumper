# comic-jumper

A decompilation project for the Xbox 360 game **Comic Jumper** (Twisted
Pixel Games, 2010), working from the Xbox Live Arcade retail package: title
id `58410A20`, version `0x101`, executable `default.xex`. `VERSION=retail`
picks the target (the only one, and the default).

The project is at the **survey stage**. The tree extracts the executable
from your own package, verifies it, and maps it: 12,179 functions from the
image's own function table, its sections, imports and libraries
([`docs/SURVEY.md`](docs/SURVEY.md)). No source is rebuilt yet. The
executable was built with the Xbox 360 SDK's compiler, which this project
does not use; which public compiler can stand in for it, if any, is the
first open decision ([`docs/DECISIONS.md`](docs/DECISIONS.md), D1).
[`docs/TARGETS.md`](docs/TARGETS.md) describes the target and what the
executable says about its own build.

<!-- progress:begin -->
| Target | Matched |
| --- | --- |
| [Xbox Live Arcade retail package, version 0x101 (58410A20)](https://nathanialf.github.io/comic-jumper/#retail) | ![code progress](https://img.shields.io/badge/code-0.00%20%25-red.svg) ![functions progress](https://img.shields.io/badge/functions-0.00%20%25-red.svg) |
<!-- progress:end -->

> [!IMPORTANT]
> This project is not affiliated with Twisted Pixel Games or Microsoft.
> *Comic Jumper* is a trademark of its owners. No game data is in this
> repository; you supply your own copy. Read
> [`docs/LEGAL.md`](docs/LEGAL.md).

## Quickstart

```sh
git clone https://github.com/nathanialf/comic-jumper.git
cd comic-jumper
mkdir -p baserom
ln -s "/path/to/your/Comic Jumper/58410A20/000D0000/<content file>" baserom/CJ_RETAIL.pkg
./build.sh
```

`./build.sh` runs `tools/setup.sh` when the Python environment is missing,
extracts the package when `baserom/retail/default.pe` is missing
(`tools/extract_pkg.sh`: every file to `baserom/retail/files/`, the
executable decrypted and expanded to the image the console loads, their
SHA-256s recorded), verifies the recorded hashes, then runs the gate,
`tools/check_pe.py --gate`, and exits non-zero if any step fails. The host
needs a 64-bit Linux with Python 3 and network access for the first run;
[`docs/BUILDING.md`](docs/BUILDING.md) describes each step. Extracting the
2.0 GB package writes another 2.0 GB under `baserom/`.

The build checks the SHA-256s from `config/sha256sums.retail.txt`, recorded
the first time the package is extracted and never edited:

| file | SHA-256 |
| --- | --- |
| `baserom/CJ_RETAIL.pkg` (the package) | `14fc885ceee2a0182b45ef1ca09a45d5a1d5f3323c25da97fd9de273812443ea` |
| `baserom/retail/default.xex` (the executable as shipped) | `65d4b32ebde453fdbb41eb1c3852fc514d015a81307bc82296e545ef0443ae7a` |
| `baserom/retail/default.pe` (its image, decrypted and expanded) | `c6bbbc74bf03cca44464dc7796cf7f52c3e2bc91314dc863b199074ef0ab78f3` |

## Layout

```
src/                        the rebuilt sources (none yet)
config/                     per target <slug>: sha256sums (the base files),
                            functions (every function the image's function
                            table lists: address, size, name), imports (the
                            import records)
tools/                      setup, extraction, survey and gate scripts,
                            listed in tools/README.md
docs/                       documentation, indexed by docs/README.md;
                            docs/retail/ holds the target's progress files
baserom/  build/            local only and gitignored: the user's package and
                            extracted files, and the build output
```

## Toolchain

| tool | role | source | licence |
| --- | --- | --- | --- |
| `tools/extract_pkg.py` | reads the user's package (STFS) | this repository, after Velocity's public reader | MIT |
| `tools/xex.py` | decrypts and expands the executable (XEX2) | this repository, after Xenia's public structures | MIT |
| cryptography, capstone, ninja, clang-format | AES, disassembly, the build runner, the formatter | PyPI, into `.venv/` | their own |

Nothing comes from the Xbox 360 SDK. The compiler is not chosen yet
(`docs/DECISIONS.md`, D1).

## Legal and licence

The code in this repository is MIT licensed ([`LICENSE`](LICENSE)). The
licence covers the code written for this project and grants no rights in the
game, its data or anything else owned by Twisted Pixel Games or Microsoft.
[`docs/LEGAL.md`](docs/LEGAL.md) says what may and may not be in the
repository and which references were used.
