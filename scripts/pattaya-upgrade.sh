#!/bin/bash
# pattaya-upgrade.sh — upgrade gstack-auto (Pattaya) in place.
#
# Detects git vs vendored install, performs the upgrade, writes a
# just-upgraded-from marker, and clears caches.
#
# Usage:
#   ./scripts/pattaya-upgrade.sh          # upgrade from remote
#   ./scripts/pattaya-upgrade.sh --check  # just print status

set -euo pipefail

PATTAYA_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STATE_DIR="${HOME}/.pattaya"
VERSION_FILE="${PATTAYA_ROOT}/VERSION"
UPGRADED_FILE="${STATE_DIR}/just-upgraded-from"
CACHE_FILE="${STATE_DIR}/last-update-check"
SNOOZE_FILE="${STATE_DIR}/update-snoozed"

mkdir -p "$STATE_DIR"

OLD_VERSION=$(cat "$VERSION_FILE" 2>/dev/null | tr -d '[:space:]')

if [ "${1:-}" = "--check" ]; then
  exec "$PATTAYA_ROOT/scripts/pattaya-update-check"
fi

# --- Detect install type ---

if [ -d "$PATTAYA_ROOT/.git" ]; then
  INSTALL_TYPE="git"
else
  INSTALL_TYPE="vendored"
fi

echo "gstack-auto upgrade"
echo "  Install type: $INSTALL_TYPE"
echo "  Current version: $OLD_VERSION"
echo ""

# --- Perform upgrade ---

case "$INSTALL_TYPE" in
  git)
    cd "$PATTAYA_ROOT"
    echo "Fetching latest..."
    git stash -q 2>/dev/null || true
    git fetch origin 2>/dev/null
    git reset --hard origin/main 2>/dev/null
    echo "Updated."
    ;;

  vendored)
    TMPDIR=$(mktemp -d)
    REPO_URL="${PATTAYA_REMOTE_REPO:-https://github.com/loperanger7/gstack-auto.git}"
    echo "Cloning latest to temp dir..."
    if ! git clone --depth 1 -q "$REPO_URL" "$TMPDIR/fresh" 2>/dev/null; then
      echo "ERROR: git clone failed. Check network and repo URL."
      rm -rf "$TMPDIR"
      exit 1
    fi
    BACKUP="${PATTAYA_ROOT}.backup.$$"
    mv "$PATTAYA_ROOT" "$BACKUP"
    mv "$TMPDIR/fresh" "$PATTAYA_ROOT"
    rm -rf "$BACKUP" "$TMPDIR"
    echo "Updated."
    ;;
esac

NEW_VERSION=$(cat "$PATTAYA_ROOT/VERSION" 2>/dev/null | tr -d '[:space:]')

# --- Write markers, clear caches ---

echo "$OLD_VERSION" > "$UPGRADED_FILE"
rm -f "$CACHE_FILE" "$SNOOZE_FILE"

echo ""
echo "Upgraded: $OLD_VERSION → $NEW_VERSION"

# --- Show changelog diff ---

if [ -f "$PATTAYA_ROOT/CHANGELOG.md" ]; then
  echo ""
  echo "What's new:"
  # Show lines between old version header and the one before it
  sed -n "/## \[*${NEW_VERSION}/,/## \[*${OLD_VERSION}/p" "$PATTAYA_ROOT/CHANGELOG.md" \
    | head -20 \
    | grep -v "^## " \
    | grep -v "^$" \
    | head -7 \
    | sed 's/^/  /'
fi
