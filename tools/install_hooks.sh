#!/usr/bin/env bash
# Install the IP-safety scan and the match gate as git hooks (opt-in):
#   - pre-commit: refuses a local commit that breaks the gate
#   - pre-push:   refuses to push a ref whose tip fails the gate (the backstop
#                 for commits made with --no-verify); a tip whose tree the
#                 pre-commit gate already passed is pushed without a second run
#                 (the tree hashes are kept in <gitdir>/gated-trees)
# Re-run any time either hook body changes.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GITDIR="$(cd "$ROOT" && git rev-parse --git-common-dir 2>/dev/null || true)"
case "$GITDIR" in "") GITDIR="$ROOT/.git" ;; /*) ;; *) GITDIR="$ROOT/$GITDIR" ;; esac
HOOK="$GITDIR/hooks/pre-commit"
PUSH_HOOK="$GITDIR/hooks/pre-push"

if [[ ! -d "$GITDIR" ]]; then
    echo "install_hooks: $ROOT is not a git repo (no git dir)" >&2
    exit 1
fi
mkdir -p "$GITDIR/hooks"

cat > "$HOOK" <<'EOF2'
#!/usr/bin/env bash
# Auto-installed by tools/install_hooks.sh. Runs, in order:
#   1. tools/check_no_rom.sh        IP-safety scan of the staged files
#   2. tools/check_dev_native.py    refuses crutches in the staged sources (inline
#                                   asm, register pins, codegen attributes and
#                                   pragmas, empty do-while, unexplained volatile)
#   3. tools/format.sh --check      staged C/C++ must be clang-formatted
#   4. tools/build.sh gate-all      for EVERY configured target: its base files
#                                   are required, then setup, ninja and the
#                                   match gate (tools/check_pe.py --gate)
#   5. tools/build.sh progress-all  refresh docs/<slug>/PROGRESS.md,
#                                   docs/<slug>/progress.json and README.md's
#                                   progress block, then `git add` them
#   4a. refuse when the working tree and the index differ under src/, config/
#       or tools/: the gate runs on the working tree, the commit is the index
#   6. record the staged tree's hash in <gitdir>/gated-trees, so the pre-push
#      hook knows this exact tree passed the gate and does not run it again
#
# Steps 4 to 6 run only when a staged path can affect the build (src/,
# config/, tools/). Bypass with --no-verify only for a commit that cannot touch
# the build and when the build is known green.
set -e
ROOT="$(git rev-parse --show-toplevel)"
GITDIR="$(git rev-parse --git-common-dir)"
case "$GITDIR" in /*) ;; *) GITDIR="$ROOT/$GITDIR" ;; esac

"$ROOT/tools/check_no_rom.sh"

# Staged sources must be developer-native: no construct that emits no bytes
# and exists to steer the compiler (CLAUDE.md, docs/MATCH.md "Crutches").
"$ROOT/.venv/bin/python" -I "$ROOT/tools/check_dev_native.py"

STAGED_SRC=$(git diff --cached --name-only --diff-filter=ACMR -z | tr '\0' '\n' |
    grep -E '^src/.*\.(c|cpp|cc|h|hpp|inl)$' || true)
if [[ -n "$STAGED_SRC" ]]; then
    # shellcheck disable=SC2086
    "$ROOT/tools/format.sh" --check $STAGED_SRC
fi

BUILD_SENSITIVE=$(git diff --cached --name-only -z | tr '\0' '\n' |
    grep -E '^(src/|config/|tools/)' || true)
if [[ -z "$BUILD_SENSITIVE" ]]; then
    exit 0
fi

# The gate runs on the working tree and the commit records the index. They
# must agree in every path that can affect the build (a tracked file with
# unstaged changes, a staged file changed again, an untracked source), or the
# tree recorded below was never the tree that passed.
DIVERGED=$(git status --porcelain=v1 --untracked-files=all -- src config tools |
    grep -E '^(.[^ ]|\?\?)' || true)
if [[ -n "$DIVERGED" ]]; then
    echo "pre-commit: the working tree differs from the index in build-sensitive paths;" >&2
    echo "  the gate runs on the working tree and the commit records the index, so" >&2
    echo "  stage these (or remove them) before committing:" >&2
    echo "$DIVERGED" >&2
    exit 1
fi

echo "pre-commit: tools/build.sh gate-all ..."
if ! "$ROOT/tools/build.sh" gate-all; then
    echo "" >&2
    echo "pre-commit: GATE FAILED: a configured target's base files are missing," >&2
    echo "  or a function listed as matched no longer matches. Fix before committing;" >&2
    echo "  bypass with \`git commit --no-verify\` only if you understand why." >&2
    exit 1
fi

echo "pre-commit: tools/build.sh progress-all (refresh + stage progress) ..."
if "$ROOT/tools/build.sh" progress-all >/dev/null 2>&1; then
    (cd "$ROOT" && git add README.md docs/*/PROGRESS.md docs/*/progress.json) 2>/dev/null || true
else
    echo "pre-commit: progress regen failed (non-fatal): commit proceeds" >&2
fi

# The tree about to be committed is exactly the staged index; the gate passed
# on it, so the pre-push hook may push a commit of this tree without a second
# run. A commit made with --no-verify records nothing and is gated at push.
echo "$(cd "$ROOT" && git write-tree) $(date -u +%Y-%m-%dT%H:%M:%SZ) pre-commit" >> "$GITDIR/gated-trees"
EOF2
chmod +x "$HOOK"
echo "Installed pre-commit hook at $HOOK"

cat > "$PUSH_HOOK" <<'EOF2'
#!/usr/bin/env bash
# Auto-installed by tools/install_hooks.sh. For each ref being pushed, check
# out its tip in a temporary worktree and run tools/build.sh gate-all there,
# unless the tip's tree is listed in <gitdir>/gated-trees: the pre-commit hook
# (or an earlier push) ran the gate on exactly that tree and it passed, and the
# gate is a function of the tree alone (the base files and the compilers are
# the same ones, linked into the worktree). `git push --no-verify` skips it.
set -e
ROOT="$(git rev-parse --show-toplevel)"
GITDIR="$(git rev-parse --git-common-dir)"
case "$GITDIR" in /*) ;; *) GITDIR="$ROOT/$GITDIR" ;; esac
zero=0000000000000000000000000000000000000000
while read -r local_ref local_sha remote_ref remote_sha; do
    [[ "$local_sha" == "$zero" ]] && continue   # deleting a ref
    tree="$(git -C "$ROOT" rev-parse "$local_sha^{tree}")"
    if [[ -f "$GITDIR/gated-trees" ]] && grep -q "^$tree " "$GITDIR/gated-trees"; then
        echo "pre-push: tree $tree of $local_ref passed the gate at commit time; not run again"
        continue
    fi
    tmp="$(mktemp -d)"
    trap 'rm -rf "$tmp"; git -C "$ROOT" worktree prune' EXIT
    git -C "$ROOT" worktree add -q --detach "$tmp" "$local_sha"
    for d in .venv tools/cc tools/ext baserom; do
        [[ -e "$ROOT/$d" ]] && ln -s "$ROOT/$d" "$tmp/$d"
    done
    echo "pre-push: gate-all on $local_ref ($local_sha)"
    if ! (cd "$tmp" && tools/build.sh gate-all); then
        echo "pre-push: GATE FAILED on $local_ref; refusing to push" >&2
        git -C "$ROOT" worktree remove --force "$tmp"
        exit 1
    fi
    git -C "$ROOT" worktree remove --force "$tmp"
    echo "$tree $(date -u +%Y-%m-%dT%H:%M:%SZ) pre-push" >> "$GITDIR/gated-trees"
done
EOF2
chmod +x "$PUSH_HOOK"
echo "Installed pre-push hook at $PUSH_HOOK"
