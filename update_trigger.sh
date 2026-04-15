#!/bin/bash

# Antigravity IDE Forced Update Trigger
# Version: 2026.0.1.0

echo "--- [ANTIGRAVITY UPDATE] Initiating forced update sequence ---"

# 1. Create the update marker in App Support
TRIGGER_PATH="$HOME/Library/Application Support/Antigravity/.force_update"
touch "$TRIGGER_PATH"
echo "[1/3] Created update trigger: $TRIGGER_PATH"

# 2. Identify the process and shut it down cleanly
# We use pkill with the app bundle ID if possible, or the process name
if pgrep -x "Antigravity" > /dev/null; then
    echo "[2/3] Found running Antigravity instance. Shutting down..."
    pkill -x "Antigravity"
    sleep 2
else
    echo "[2/3] No running Antigravity instance found."
fi

# 3. Relaunch with update flags
# This initiates the silent update handler
echo "[3/3] Relaunching Antigravity with update flags..."
open -a Antigravity --args --update-extensions --force

echo "--- [ANTIGRAVITY UPDATE] Update sequence activated. Please wait for the IDE to relaunch. ---"
