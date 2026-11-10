# Building

How the tree goes from a clean clone to the gate, step by step, and what each
tool needs. The one-command form is `./build.sh`; this document is what it
does.

The project is at the survey stage: the build extracts and verifies the base
files and gates the tables derived from them. There is no compiler and no
compile step yet (`docs/DECISIONS.md`, D1).

## Host

A 64-bit Linux. Tested on Debian 13 (trixie), x86-64. Disk: the package is
2.0 GB and its extracted files another 2.0 GB, both under `baserom/`.

Host packages (Debian names):

```sh
sudo apt-get install -y python3-venv git llvm-19
```

`llvm-19` is optional at this stage; `tools/setup.sh` says so when it is
missing. Everything else is the Python venv (`tools/requirements.txt`:
cryptography, capstone, ninja, clang-format) under `.venv/`. Nothing is
downloaded but those packages: the package reader and the XEX reader are this
repository's own Python.

## One command

```sh
mkdir -p baserom
ln -s "/path/to/your/Comic Jumper/58410A20/000D0000/<content file>" baserom/CJ_RETAIL.pkg
./build.sh
```

The content file is the single large file an Xbox Live Arcade title is
stored as, named by 42 hexadecimal digits.

`build.sh`:

1. runs `tools/setup.sh` when `.venv/` or one of its packages is missing;
2. runs `tools/extract_pkg.sh` when `baserom/retail/default.pe`,
   `baserom/retail/default.xex` or `config/sha256sums.retail.txt` is missing;
3. runs `tools/build.sh verify` (the recorded SHA-256s of `default.xex` and
   `default.pe`);
4. runs `tools/build.sh setup` and `ninja` once `tools/gen_ninja.py` exists
   (not yet);
5. runs the gate, `tools/check_pe.py --gate`.

It exits non-zero when any step fails.

## 1. Host setup: `tools/setup.sh`

Idempotent. Creates the venv and installs `tools/requirements.txt`; checks
the host packages; installs the git hooks (`tools/install_hooks.sh`).

## 2. The executable: `tools/extract_pkg.sh`

`tools/extract_pkg.py`, in the venv (about 25 seconds):

1. Reads the package header and stops unless the title id, version and media
   id are the target's (`tools/cj_version.py`, `PKGS`).
2. Walks the STFS volume: the file table, then each file's chain of 4 KiB
   blocks through the hash tables. Every block is checked against the SHA-1
   its hash entry records, so a damaged package or a layout the tool does not
   read stops the run instead of writing a wrong file. The 193 files land in
   `baserom/retail/files/`.
3. Copies `default.xex` to `baserom/retail/default.xex`, checks the title id,
   version and media id in its execution info, unwraps its session key with
   the retail XEX2 key (`docs/LEGAL.md`), decrypts the payload (AES-128-CBC)
   and restores the zero runs of its basic compression. The result must be
   exactly the image size the header states and must start with a PE header.
   It is written to `baserom/retail/default.pe`: the image as the console
   loads it, where a byte's offset is its address minus `0x82000000`.
4. `config/sha256sums.retail.txt`: the SHA-256 of the package, `default.xex`
   and `default.pe`, recorded on the first run and verified on every later
   one. **Never edit the hashes.** A mismatch is a different package or a
   changed tool, and either is a finding.

## 3. The gate: `tools/check_pe.py --gate`

At the survey stage the gate checks what the tree claims:

- `config/functions.retail.txt` and `config/imports.retail.txt` equal, byte
  for byte, what `tools/survey_pe.py` derives from the user's base files;
- `config/matched.retail.txt` has no row, because nothing can check one yet.

The compare step joins the gate when D1 is decided.

## The survey: `tools/survey_pe.sh`

`tools/survey_pe.py --md` writes `config/functions.retail.txt` (every
function the image's function table lists: address, size, name),
`config/imports.retail.txt` (the XEX import records) and `docs/SURVEY.md`. It
reads the PE headers and sections, the exception directory (`.pdata`), the
Rich header, the XEX optional headers (execution info, file format, import
libraries, static libraries) and the source paths in the image's strings. It
checks the function table as it reads it (sorted, no overlap, every range
inside an executable section) and stops when a check fails. Re-run it only
when the tooling changes; the function list is the base of every claim.

`tools/disasm.py <function or address> [<end>]` prints a range of the image
as PowerPC instructions.

## Progress and the dashboard

`tools/build.sh progress` (`tools/check_pe.py --progress`) rewrites
`docs/retail/progress.json` (the dashboard's data, schema 2), the table in
`docs/retail/PROGRESS.md` and the badge row between the
`<!-- progress:begin -->` / `<!-- progress:end -->` markers in `README.md`.
The dashboard, `docs/index.html`, reads `retail/progress.json`; preview it
locally with `python3 -m http.server -d docs` and open
`http://localhost:8000/`. `.github/workflows/pages.yml` publishes
`docs/index.html`, `docs/retail/progress.json` and `docs/retail/PROGRESS.md`
to GitHub Pages on a push to `main` that changes one of them
(`.github/scripts/build_pages_site.sh` assembles `_site/`).

## Hooks

`tools/install_hooks.sh` (run by `setup.sh`) writes two hooks:

- **pre-commit**: `tools/check_no_rom.sh` (the IP scan of the staged files),
  `tools/check_dev_native.py` and `tools/format.sh --check` on staged
  sources, and when a staged path is under `src/`, `config/` or `tools/`:
  `tools/build.sh gate-all`, then `tools/build.sh progress-all`, whose
  refreshed files are staged into the commit.
- **pre-push**: `gate-all` on the tip of each pushed ref, in a temporary
  worktree, unless the pre-commit hook already gated that exact tree.

`git commit --no-verify` bypasses the first and `git push --no-verify` the
second; use either only for a commit that cannot touch the build.

## Formatting

`tools/format.sh` runs clang-format with the tracked `.clang-format` over the
sources under `src/` (`--check` for the hook). Whitespace only.
