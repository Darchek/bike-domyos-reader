#!/bin/bash

PLIST_NAME="com.mbusq.domyosservice"
PLIST_PATH="/Users/mbusq/Library/LaunchAgents/${PLIST_NAME}.plist"

echo "🛑 Stopping service: $PLIST_NAME"

launchctl stop "$PLIST_NAME"
launchctl unload "$PLIST_PATH"

sleep 1

STATUS=$(launchctl list | grep "$PLIST_NAME")
if [ -z "$STATUS" ]; then
    echo "✅ Service stopped and unloaded"
else
    echo "⚠️  Service still running: $STATUS"
fi
