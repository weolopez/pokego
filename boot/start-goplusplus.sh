#!/data/data/com.termux/files/usr/bin/bash
# Termux:Boot auto-start script.
# Installed by setup.sh to ~/.termux/boot/start-goplusplus.sh

# Wait for system to settle after reboot
sleep 10

EMULATOR_DIR="$HOME/goplusplus-plus"
LOG="$HOME/goplusplus.log"

cd "$EMULATOR_DIR" || exit 1

echo "$(date '+%Y-%m-%d %H:%M:%S') [boot] Starting GO Plus + emulator" >> "$LOG"
bash watchdog.sh >> "$LOG" 2>&1 &

echo "$(date '+%Y-%m-%d %H:%M:%S') [boot] Started (PID $!)" >> "$LOG"
