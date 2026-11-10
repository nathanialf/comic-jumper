# tools/

Every script the build uses. Python tools run in the venv with `-I`.

| tool | what it does |
| --- | --- |
| `setup.sh` | host setup: the venv from `requirements.txt`, the host package check, the git hooks |
| `cj_version.py`, `cj_version.sh` | the target slug, its paths and the package table; the two are twins and are kept in sync |
| `extract_pkg.sh`, `extract_pkg.py` | the user's package to `baserom/<slug>/`: every file, `default.xex`, the expanded image `default.pe`; records or verifies the SHA-256s |
| `xex.py` | XEX2 reading shared by the extractor and the survey: optional headers, security info, decryption and basic decompression |
| `verify_base.py` | one file's SHA-256 against `config/sha256sums.<slug>.txt` |
| `survey_pe.sh`, `survey_pe.py` | the executable's map: `config/functions.<slug>.txt`, `config/imports.<slug>.txt`, `docs/SURVEY.md` |
| `disasm.py` | a range of the image as PowerPC instructions |
| `check_pe.py` | `--gate`: the tree's claims against the base; `--progress`: the progress files and README badges |
| `build.sh` | `setup`, `verify`, `regen`, `clean`, `distclean`, `progress`, `gate-all`, `progress-all` |
| `check_no_rom.sh` | the IP scan: extensions, names, package and executable magic, a size cap, raw byte arrays |
| `check_dev_native.py`, `dev_native_allow.txt` | refuses source constructs that exist only to steer the compiler; the ruled exceptions |
| `format.sh` | clang-format over `src/` |
| `install_hooks.sh` | writes the pre-commit and pre-push hooks |

Not here yet, and waiting on `docs/DECISIONS.md` D1: the compiler fetch, the
ninja generator, the per-function compare and the inner-loop diff.
