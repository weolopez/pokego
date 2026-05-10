#!/data/data/com.termux/files/usr/bin/bash
# Watchdog: restart the emulator on crash.
# Run this instead of start.sh for persistent operation.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

while true; do
    echo "$(date '+%Y-%m-%d %H:%M:%S') [watchdog] Starting emulator..."
    python3 -m goplusplus "$@"
    echo "$(date '+%Y-%m-%d %H:%M:%S') [watchdog] Emulator exited (code $?). Restarting in 5s..."
    sleep 5
done
