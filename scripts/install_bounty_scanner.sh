#!/usr/bin/env bash
# install_bounty_scanner.sh — Install CORTEX Bounty Scanner as macOS launchd agent
# Usage:  bash scripts/install_bounty_scanner.sh [--uninstall]
set -euo pipefail

LABEL="com.cortex.bounty_scanner"
PLIST_SRC="$(cd "$(dirname "$0")"; pwd)/com.cortex.bounty_scanner.plist"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
PLIST_DST="$LAUNCH_AGENTS_DIR/$LABEL.plist"
LOG_DIR="$(cd "$(dirname "$0")/.."; pwd)/logs"

if [[ "${1:-}" == "--uninstall" ]]; then
  echo "→ Unloading $LABEL..."
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || launchctl unload "$PLIST_DST" 2>/dev/null || true
  rm -f "$PLIST_DST"
  echo "✓ Bounty scanner uninstalled."
  exit 0
fi

# Ensure logs dir exists
mkdir -p "$LOG_DIR"

# Copy plist to LaunchAgents
cp "$PLIST_SRC" "$PLIST_DST"
echo "→ Plist installed at $PLIST_DST"

# Unload any previous instance
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || launchctl unload "$PLIST_DST" 2>/dev/null || true

# Load and start
launchctl bootstrap "gui/$(id -u)" "$PLIST_DST" || launchctl load -w "$PLIST_DST"
echo "✓ Bounty scanner installed and started."
echo ""
echo "  Schedule  : every 6 hours (21600 seconds)"
echo "  Next scan : immediate (RunAtLoad=true)"
echo "  Results   : scripts/bounty_results/scan_<timestamp>.json"
echo "  Stdout    : $LOG_DIR/bounty_scanner.log"
echo "  Stderr    : $LOG_DIR/bounty_scanner_err.log"
echo ""
echo "  Status    : launchctl list | grep cortex"
echo "  Uninstall : bash scripts/install_bounty_scanner.sh --uninstall"
