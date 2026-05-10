#!/data/data/com.termux/files/usr/bin/bash
# Compatibility wrapper for older instructions.
# Android service lifecycle is managed by the OS + START_STICKY.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

exec bash start.sh "$@"
