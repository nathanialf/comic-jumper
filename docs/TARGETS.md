# Targets

One target so far. Each target has its own `config/*.<slug>.*`,
`baserom/<slug>/`, `build/<slug>/` and `docs/<slug>/`; `VERSION=<slug>`
picks it (`tools/cj_version.py`). A second target would join by adding a
`PKGS` row there, a `config/sha256sums.<slug>.txt` from its own extraction,
and its slug to `.github/scripts/build_pages_site.sh` and the dashboard's
picker.

Every figure below is read from the user's package by `tools/extract_pkg.py`
or `tools/survey_pe.py`; [`SURVEY.md`](SURVEY.md) is the full map.

## Xbox Live Arcade retail package (`retail`)

| | |
| --- | --- |
| package | STFS volume, magic `LIVE`, content type `0x000D0000` (Arcade Title), display name "Comic Jumper" |
| ids | title id `58410A20`, media id `69414724`, version `0x101`, base version `0x101` |
| size | 2,057,826,304 bytes; 499,431 data blocks of 4 KiB; 193 files in one directory, 2,045,262,585 bytes |
| executable | `default.xex`, 9,056,256 bytes: XEX2, AES encrypted with a session key wrapped by the retail key, basic compression (3 blocks) |
| image | `0x8F0000` bytes at base `0x82000000`, entry `0x822A6370`, original name `Game.exe` |
| PE | machine `0x01F2` (PowerPC, big-endian), 32-bit, timestamp `0x4C237DD7` (2010-06-24 15:46:31 UTC), 21 sections |
| code | 12 executable sections, `0x6A6950` bytes: `.text` (`0x639DEC`), nine `.embsec_` sections, `BINK` |
| functions | 12,179 entries in the function table (`.pdata`), covering `0x632A1C` bytes, 93.2% of the code |
| data | `.rdata` `0x10059C`, `.data` `0xD6460`, and the small `BINKCONS`, `BINKDATA`, `BINKBSS`, `.XBMOVIE`, `.idata`, `.XBLD` |
| imports | `xam.xex` (180 records) and `xboxkrnl.exe` (323 records), both version 2.0.11164.0, by ordinal |

### What the image is

`baserom/retail/default.pe` is the executable as the console's loader maps
it: the XEX payload decrypted and its zero runs restored. A byte's offset in
that file is its address minus `0x82000000`. The PE section headers' raw file
pointers describe the linker's output file, which the XEX does not keep, and
do not apply. The PE header's size of image is `0x989800`; the XEX image is
`0x8F0000`, so the tail of `.reloc` (a discardable section) is absent.

### What the executable says about its build

- **Toolchain.** The XEX's library table lists the tools beside the
  libraries: `C1` 16.0.10224.0 and `C2` 16.0.10224.0 (the compiler's front
  and back end) and `LINK` 10.0.10224.0. The PE's Rich header records build
  10224 for most objects and build 2909 for three.
- **SDK.** Every static library is version 2.0.11164 (three carry a QFE of
  3): `LIBCPMT`, `XAPILIB`, `D3D9`, `D3DX9`, `XGRAPHC`, `XBOXKRNL`, `XNET`,
  `XAUDIO2`, `XAPOBA`, `XACT3`, `X3DAUD`, `XONLINE`, `XMP`, `QNETXA2`,
  `XRNSS`, `XRNMS`, `XCAM`, `XMCORE`, `XPARTY`, `XAVATAR`, `XMEDIA2`, `XAUD`,
  `XHV2`. Source paths in the strings name the tree those libraries came from
  as `xdk-main-feb10`.
- **Which public compiler.** Undetermined, and the first open decision
  (`docs/DECISIONS.md`, D1). The original compiler and linker are part of the
  XDK, which is a forbidden input (`docs/LEGAL.md`).
- **Third-party code.** Sections named `BINK`, `BINKCONS`, `BINKDATA` and
  `BINKBSS` hold a video codec's code and data; one source path names a
  `dependencies\granny` directory under the game's own tree. The `.embsec_`
  sections are nine separate code sections whose origin is not established.
- **Source layout.** 54 source paths appear as strings. All but one are under
  the SDK's `xgraphics\ucode` directory; one is the game's own tree
  (`c:\p4develop\twistedpixel\...\beard+razor\dependencies\granny\src`). The
  game's own sources name no file in a string the survey's pattern finds.
- **No symbols.** The package holds no `.pdb`, `.xdb` or `.map`.

### What is not read from the package

The build reads the package header and `default.xex`. The other 192 files
(resource archives, videos, the wave bank, marketplace images and metadata,
two embedded packages) are extracted with it under `baserom/retail/files/`
and never read, and nothing from them is committed.
