#!/bin/bash
# usage: scripts/checkpoint.sh "message"  -> tests, stage, refuse if .env staged, commit, push
set -e
cd "$(dirname "$0")/.."
python -m pytest -q
git add -A
if git diff --cached --name-only | grep -qE '(^|/)\.env$'; then echo "ABORT: .env is staged"; git reset -q .env; exit 1; fi
git commit -q -m "$1

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>" || echo "nothing to commit"
git push -q origin HEAD 2>&1 | tail -2
git log --oneline | head -1
