#!/bin/bash
# [C5-REAL] Exergy-Maximized
# Author: borjamoskv
# Installs and loads com.moskv1.daemon.plist into macOS launchd.

PLIST_NAME="com.moskv1.daemon.plist"
SOURCE_PLIST="/Users/borjafernandezangulo/30_BABYLON-60/babylon60/extensions/training/$PLIST_NAME"
TARGET_DIR="/Users/borjafernandezangulo/Library/LaunchAgents"
TARGET_PLIST="$TARGET_DIR/$PLIST_NAME"

echo "⚙️ Installing MOSKV-1 Launchd Daemon..."

# Ensure target directory exists
mkdir -p "$TARGET_DIR"

# Unload existing daemon if loaded
if launchctl list | grep -q "com.moskv1.daemon"; then
    echo "🔄 Unloading existing daemon..."
    launchctl unload "$TARGET_PLIST" 2>/dev/null
fi

# Copy plist to User's LaunchAgents directory
echo "📁 Copying plist to $TARGET_PLIST..."
cp "$SOURCE_PLIST" "$TARGET_PLIST"
chmod 644 "$TARGET_PLIST"

# Load the daemon
echo "🚀 Loading daemon into launchd..."
launchctl load "$TARGET_PLIST"

# Verify status
sleep 1
if launchctl list | grep -q "com.moskv1.daemon"; then
    PID=$(launchctl list | grep "com.moskv1.daemon" | awk '{print $1}')
    echo "✅ Daemon loaded successfully! PID: $PID"
else
    echo "❌ Failed to load daemon. Check console logs."
    exit 1
fi
