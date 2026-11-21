#!/bin/bash
# Runs every quality gate: ruff, mypy, pytest, eslint, tsc, vitest, production build. Usage: scripts/check.sh
set -e
cd "$(dirname "$0")/.."
echo "== ruff";   ruff check backend scripts
echo "== mypy";   mypy
echo "== pytest"; python -m pytest -q
cd frontend
echo "== eslint"; npx eslint src
echo "== tsc";    npx tsc --noEmit
echo "== vitest"; npx vitest run
echo "== build";  npm run build > /dev/null && echo "build ok"
