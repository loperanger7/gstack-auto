#!/bin/bash
# check-gstack-sync.sh — Warns when Pattaya phase prompts are stale
# relative to the gstack skills they were derived from.
#
# Usage: ./scripts/check-gstack-sync.sh
#
# Compares the gstack source hash recorded in each phase prompt header
# against the current hash of the corresponding gstack SKILL.md file.

set -euo pipefail

GSTACK_DIR="${HOME}/.claude/skills/gstack"
PHASES_DIR="$(dirname "$0")/../pipeline/phases"
STALE=0
CHECKED=0
SKIPPED=0

if [ ! -d "$GSTACK_DIR" ]; then
  echo "⚠ gstack not found at $GSTACK_DIR — skipping sync check"
  exit 0
fi

GSTACK_VERSION=$(cat "$GSTACK_DIR/VERSION" 2>/dev/null || echo "unknown")
echo "gstack version: $GSTACK_VERSION"
echo ""

for phase_file in "$PHASES_DIR"/*.md; do
  filename=$(basename "$phase_file")

  # Extract gstack source info from header
  recorded_hash=$(grep "^# Gstack source hash:" "$phase_file" 2>/dev/null | sed 's/.*: //' || true)

  if [ -z "$recorded_hash" ]; then
    SKIPPED=$((SKIPPED + 1))
    continue
  fi

  # Extract which gstack skill this derives from
  derived_from=$(grep "^# Derived from:" "$phase_file" 2>/dev/null | sed 's/.*: gstack //' | sed 's/ @.*//' || true)
  # Handle "Also derived from:" for derived phases
  if [ -z "$derived_from" ]; then
    derived_from=$(grep "^# Also derived from:" "$phase_file" 2>/dev/null | sed 's/.*: gstack //' | sed 's/ @.*//' || true)
  fi

  if [ -z "$derived_from" ]; then
    SKIPPED=$((SKIPPED + 1))
    continue
  fi

  skill_file="$GSTACK_DIR/$derived_from"
  if [ ! -f "$skill_file" ]; then
    echo "⚠ $filename — source not found: $skill_file"
    STALE=$((STALE + 1))
    continue
  fi

  # Get current hash of the gstack skill file (first 8 chars of sha256)
  current_hash=$(cd "$GSTACK_DIR" && git rev-parse HEAD 2>/dev/null | cut -c1-8 || shasum "$skill_file" | cut -c1-8)

  CHECKED=$((CHECKED + 1))

  if [ "$recorded_hash" != "$current_hash" ]; then
    echo "⚠ STALE: $filename"
    echo "  Recorded hash: $recorded_hash"
    echo "  Current hash:  $current_hash"
    echo "  Run: ./scripts/diff-gstack-phase.sh $filename"
    echo ""
    STALE=$((STALE + 1))
  else
    echo "✓ $filename — up to date"
  fi
done

echo ""
echo "Summary: $CHECKED checked, $STALE stale, $SKIPPED skipped (no gstack source)"

if [ "$STALE" -gt 0 ]; then
  echo ""
  echo "To see what changed: ./scripts/diff-gstack-phase.sh <phase-file>"
  exit 1
fi
