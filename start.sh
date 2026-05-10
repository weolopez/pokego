#!/data/data/com.termux/files/usr/bin/bash
# Launch the GO Plus + emulator in the foreground.
# For background / persistent operation, use watchdog.sh or the boot script.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

exec python3 -m goplusplus.main "$@"
