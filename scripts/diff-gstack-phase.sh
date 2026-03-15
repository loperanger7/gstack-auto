#!/bin/bash
# diff-gstack-phase.sh — Shows what changed in a gstack skill since
# the Pattaya phase prompt was last synced.
#
# Usage: ./scripts/diff-gstack-phase.sh <phase-filename>
# Example: ./scripts/diff-gstack-phase.sh 04-review.md

set -euo pipefail

if [ -z "${1:-}" ]; then
  echo "Usage: $0 <phase-filename>"
  echo "Example: $0 04-review.md"
  exit 1
fi

GSTACK_DIR="${HOME}/.claude/skills/gstack"
PHASES_DIR="$(dirname "$0")/../pipeline/phases"
PHASE_FILE="$PHASES_DIR/$1"

if [ ! -f "$PHASE_FILE" ]; then
  echo "Error: Phase file not found: $PHASE_FILE"
  exit 1
fi

if [ ! -d "$GSTACK_DIR/.git" ]; then
  echo "Error: gstack is not a git repo at $GSTACK_DIR"
  exit 1
fi

# Extract recorded hash and source skill
recorded_hash=$(grep "^# Gstack source hash:" "$PHASE_FILE" 2>/dev/null | sed 's/.*: //' || true)
derived_from=$(grep "^# Derived from:" "$PHASE_FILE" 2>/dev/null | sed 's/.*: gstack //' | sed 's/ @.*//' || true)
if [ -z "$derived_from" ]; then
  derived_from=$(grep "^# Also derived from:" "$PHASE_FILE" 2>/dev/null | sed 's/.*: gstack //' | sed 's/ @.*//' || true)
fi

if [ -z "$recorded_hash" ] || [ -z "$derived_from" ]; then
  echo "Error: Could not extract gstack source info from $1"
  echo "Expected headers: '# Gstack source hash: ...' and '# Derived from: gstack ...'"
  exit 1
fi

echo "Phase:    $1"
echo "Source:   gstack/$derived_from"
echo "Synced:   $recorded_hash"
echo "Current:  $(cd "$GSTACK_DIR" && git rev-parse HEAD | cut -c1-8)"
echo ""
echo "=== Changes in gstack since last sync ==="
echo ""

cd "$GSTACK_DIR"

# Try to diff from the recorded commit to HEAD
if git cat-file -e "${recorded_hash}^{commit}" 2>/dev/null; then
  git diff "$recorded_hash" HEAD -- "$derived_from"
else
  echo "Warning: Commit $recorded_hash not found in gstack history."
  echo "Showing the full current file instead:"
  echo ""
  cat "$derived_from"
fi
