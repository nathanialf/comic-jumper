#!/usr/bin/env bash
# =============================================================================
# build_pages_site.sh: assemble the progress dashboard into _site/
#
# Run by .github/workflows/pages.yml on a push to main. Layout produced:
#   _site/index.html          the dashboard page (docs/index.html)
#   _site/retail/progress.json  the retail target's data (docs/retail/)
#   _site/retail/PROGRESS.md
#   _site/progress.json       a root copy of the default target's data, the
#   _site/PROGRESS.md         page's fallback when a <slug>/ fetch misses
#
# Only the files named in DATA_FILES are published from each docs/<slug>/,
# not all of docs/: docs/ also holds the project's documentation, and a Pages
# deploy is public, so the served set is named rather than taken as a
# directory. A second target adds its slug to SLUGS.
# =============================================================================
set -euo pipefail

SLUGS="retail"
DEFAULT_SLUG="retail"
DATA_FILES="progress.json PROGRESS.md"

rm -rf _site
mkdir -p _site

for slug in $SLUGS; do
    mkdir -p "_site/$slug"
    for f in $DATA_FILES; do
        if [ -f "docs/$slug/$f" ]; then
            cp "docs/$slug/$f" "_site/$slug/$f"
        else
            echo "::warning title=Pages::docs/$slug/$f is missing; the page will say so."
        fi
    done
done

if [ -d "_site/$DEFAULT_SLUG" ]; then
    cp -R "_site/$DEFAULT_SLUG/." _site/
fi
cp docs/index.html _site/index.html

echo "build_pages_site: assembled site:"
find _site -type f | LC_ALL=C sort | while read -r f; do
    printf '  %s (%s bytes)\n' "$f" "$(wc -c < "$f")"
done
