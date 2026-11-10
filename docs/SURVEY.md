# Survey of the executable

Written by `tools/survey_pe.py --md` from the `retail` target's base files (`baserom/retail/default.xex` and `default.pe`). Do not edit by hand.

## Container

| Field | Value |
|---|---|
| Title id | `58410A20` |
| Media id | `69414724` |
| Version / base version | `0x101` / `0x101` |
| Original PE name | `Game.exe` |
| Encryption / compression | 1 (AES) / 1 (basic, 3 blocks) |
| Image base | `0x82000000` |
| Image size (XEX) | `0x8f0000` |
| Size of image (PE header) | `0x989800` |
| Entry point | `0x822a6370` |
| PE machine | `0x01f2` |
| PE timestamp | `0x4c237dd7` (2010-06-24 15:46:31 UTC) |
| Section / file alignment | `0x10000` / `0x200` |

## Sections

| Name | Address | Size | Kind | Functions | Bytes in functions |
|---|---|---|---|---|---|
| `.rdata` | `0x82000600` | `0x10059c` | rodata |  |  |
| `.pdata` | `0x82100c00` | `0x17c98` | rodata |  |  |
| `BINKCONS` | `0x82118a00` | `0x2908` | rodata |  |  |
| `.text` | `0x82120000` | `0x639dec` | code | 11892 | `0x5ca31c` (93.0%) |
| `.embsec_` | `0x82759e00` | `0x17dec` | code | 23 | `0x17214` (96.9%) |
| `.embsec_` | `0x82771c00` | `0x1dfd4` | code | 118 | `0x1bb10` (92.3%) |
| `.embsec_` | `0x8278fc00` | `0x19e0` | code | 3 | `0x19d8` (99.9%) |
| `.embsec_` | `0x82791600` | `0x6c6c` | code | 18 | `0x61a8` (90.1%) |
| `.embsec_` | `0x82798400` | `0x15fd4` | code | 13 | `0x15fb0` (100.0%) |
| `.embsec_` | `0x827ae400` | `0x1270` | code | 4 | `0xff8` (86.6%) |
| `.embsec_` | `0x827af800` | `0x240` | code | 1 | `0x240` (100.0%) |
| `.embsec_` | `0x827afc00` | `0x2c94` | code | 1 | `0x2c94` (100.0%) |
| `.embsec_` | `0x827b2a00` | `0x4b38` | code | 7 | `0x4a7c` (99.0%) |
| `BINK` | `0x827b7600` | `0xfb08` | code | 99 | `0xf564` (97.8%) |
| `BINKBSS` | `0x827d0000` | `0x4310` | bss |  |  |
| `.data` | `0x827d4400` | `0xd6460` | data |  |  |
| `.XBMOVIE` | `0x828aaa00` | `0xc` | data |  |  |
| `BINKDATA` | `0x828aac00` | `0x338` | data |  |  |
| `.idata` | `0x828b0000` | `0x480` | data |  |  |
| `.XBLD` | `0x828c0000` | `0x1a0` | discardable |  |  |
| `.reloc` | `0x828c0200` | `0x3ef34` (past the XEX image) | discardable |  |  |

## Functions

The function table holds 12179 entries, sorted, with no overlap, every range inside an executable section. They cover `0x632a1c` of `0x6a6950` bytes of code (93.2%). The remaining `0x73f34` bytes are functions with no unwind data, padding and data held in code sections; they are not classified yet.

Function sizes: smallest `0xc`, median `0xf4`, largest `0x1b428`. 64 entries carry the exception-handler flag.

6 entries have the 32-bit flag clear, and in each the prolog length equals the function length: `0x825e35d0`, `0x825e3620`, `0x825e4130`, `0x825e417c`, `0x825e4410`, `0x825e46a8`.

## Imports

| Library | Version | Minimum | Records | Thunks | Variables |
|---|---|---|---|---|---|
| `xam.xex` | 2.0.11164.0 | 2.0.8955.0 | 180 | 90 | 90 |
| `xboxkrnl.exe` | 2.0.11164.0 | 2.0.8955.0 | 323 | 155 | 168 |

## Static libraries

| Library | Version |
|---|---|
| `LIBCPMT` | 2.0.11164.0 |
| `XAPILIB` | 2.0.11164.0 |
| `D3D9` | 2.0.11164.0 |
| `D3DX9` | 2.0.11164.0 |
| `XGRAPHC` | 2.0.11164.0 |
| `XBOXKRNL` | 2.0.11164.0 |
| `XNET` | 2.0.11164.0 |
| `XAUDIO2` | 2.0.11164.3 |
| `XAPOBA` | 2.0.11164.3 |
| `XACT3` | 2.0.11164.0 |
| `X3DAUD` | 2.0.11164.0 |
| `XONLINE` | 2.0.11164.0 |
| `XMP` | 2.0.11164.0 |
| `QNETXA2` | 2.0.11164.0 |
| `XRNSS` | 2.0.11164.0 |
| `XRNMS` | 2.0.11164.0 |
| `XCAM` | 2.0.11164.0 |
| `XMCORE` | 2.0.11164.0 |
| `XPARTY` | 2.0.11164.0 |
| `XAVATAR` | 2.0.11164.3 |
| `XMEDIA2` | 2.0.11164.0 |
| `XAUD` | 2.0.11164.0 |
| `XHV2` | 2.0.11164.0 |
| `LINK` | 10.0.10224.0 |
| `C2` | 16.0.10224.0 |
| `C1` | 16.0.10224.0 |

## Rich header

The linker's record of the tools that produced the objects, as stored: product id, build number, object count. The ids are not interpreted here.

| Product id | Build | Objects |
|---|---|---|
| 123 | 2909 | 2 |
| 109 | 2909 | 1 |
| 158 | 10224 | 27 |
| 1 | 0 | 380 |
| 156 | 10224 | 3 |
| 170 | 10224 | 387 |
| 171 | 10224 | 797 |
| 175 | 10224 | 380 |
| 157 | 10224 | 1 |

## Source paths in strings

54 distinct source paths appear as strings in the data sections, by directory:

| Directory | Files |
|---|---|
| `c:\p4develop\twistedpixel\wilsonf.cj.xbla.autobuild\beard+razor\dependencies\granny\src` | 1 |
| `e:\xenon\xdk-main-feb10\core\private\xtl\graphics\xgraphics\ucode\compiler` | 1 |
| `e:\xenon\xdk-main-feb10\core\private\xtl\graphics\xgraphics\ucode\compiler\asm` | 2 |
| `e:\xenon\xdk-main-feb10\core\private\xtl\graphics\xgraphics\ucode\compiler\il` | 2 |
| `e:\xenon\xdk-main-feb10\core\private\xtl\graphics\xgraphics\ucode\compiler\ir` | 12 |
| `e:\xenon\xdk-main-feb10\core\private\xtl\graphics\xgraphics\ucode\compiler\opt` | 5 |
| `e:\xenon\xdk-main-feb10\core\private\xtl\graphics\xgraphics\ucode\driver` | 1 |
| `e:\xenon\xdk-main-feb10\core\private\xtl\graphics\xgraphics\ucode\ssm\abstractstate` | 2 |
| `e:\xenon\xdk-main-feb10\core\private\xtl\graphics\xgraphics\ucode\ssm\inc` | 1 |
| `e:\xenon\xdk-main-feb10\core\private\xtl\graphics\xgraphics\ucode\ssm\interface` | 4 |
| `e:\xenon\xdk-main-feb10\core\private\xtl\graphics\xgraphics\ucode\ssm\statecache` | 5 |
| `e:\xenon\xdk-main-feb10\core\private\xtl\graphics\xgraphics\ucode\ssm\statecompiler` | 12 |
| `e:\xenon\xdk-main-feb10\core\private\xtl\graphics\xgraphics\ucode\ssm\translator` | 1 |
| `e:\xenon\xdk-main-feb10\core\private\xtl\graphics\xgraphics\ucode\ssm\util` | 5 |
