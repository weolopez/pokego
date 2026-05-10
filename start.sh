#!/data/data/com.termux/files/usr/bin/bash
# Start the native Android GO Plus + app/service from Termux.
# Python BLE peripheral mode is not supported on Android/Termux.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

PKG="com.pokego.plus"
ACTIVITY="$PKG/.MainActivity"
SERVICE="$PKG/.GOPlusService"

if [ "$#" -gt 0 ]; then
	echo "Note: CLI flags are ignored in Android APK mode: $*"
fi

if ! cmd package list packages "$PKG" | grep -q "$PKG"; then
	cat <<'EOF'
Android app is not installed.

Install the APK:
  https://github.com/weolopez/pokego/releases

Then re-run:
  ./start.sh
EOF
	exit 1
fi

if [ ! -f /sdcard/goplusplus/device_keys.json ]; then
	echo "Warning: /sdcard/goplusplus/device_keys.json is missing; auth will fail until keys are added."
fi

# Bring app UI to foreground so permissions can be granted on first run.
am start -n "$ACTIVITY" >/dev/null 2>&1 || true

# Start/restart emulator foreground service.
if am start-foreground-service -n "$SERVICE" >/dev/null 2>&1; then
	echo "GO Plus + foreground service started via Android app."
	exit 0
fi

# Fallback for Android versions where start-foreground-service is unavailable.
if am startservice -n "$SERVICE" >/dev/null 2>&1; then
	echo "GO Plus + service start requested."
	exit 0
fi

echo "Failed to start Android service. Open the GO Plus + app and grant Bluetooth/location/storage permissions."
exit 1
