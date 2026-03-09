#!/bin/bash

PLIST_NAME="com.mbusq.domyosservice"
PLIST_PATH="/Users/mbusq/Library/LaunchAgents/${PLIST_NAME}.plist"

echo "🔄 Reloading service: $PLIST_NAME"

# Unload (ignore error if not loaded)
launchctl unload "$PLIST_PATH" 2>/dev/null

# Load
launchctl load "$PLIST_PATH"
if [ $? -ne 0 ]; then
    echo "❌ Failed to load plist: $PLIST_PATH"
    exit 1
fi

# Start
launchctl start "$PLIST_NAME"

sleep 1

# Check status
STATUS=$(launchctl list | grep "$PLIST_NAME")
if [ -n "$STATUS" ]; then
    echo "✅ Service running: $STATUS"
else
    echo "⚠️  Service not found in launchctl list — check your logs"
fi