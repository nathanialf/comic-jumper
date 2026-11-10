#!/usr/bin/env bash
# tools/survey_pe.sh: rewrite the executable's map from the base files:
# config/functions.<slug>.txt, config/imports.<slug>.txt and docs/SURVEY.md
# (tools/survey_pe.py --md), then the progress files.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
.venv/bin/python -I tools/survey_pe.py --md "$@"
.venv/bin/python -I tools/check_pe.py --progress
