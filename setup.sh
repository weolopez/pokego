#!/data/data/com.termux/files/usr/bin/bash
# GO Plus + Emulator — Termux setup script
# Idempotent: safe to run multiple times.
#
# NOTE: Android does NOT use BlueZ — it has its own BLE stack.
# The Python package handles the crypto/protocol logic only.
# BLE advertising requires the companion Android APK (see android/).
set -e

echo "=== GO Plus + Emulator Setup ==="

# ── System packages ────────────────────────────────────────────────────────────
pkg update -y && pkg upgrade -y
pkg install -y python git termux-api

# ── Python dependencies (crypto only — BLE is handled by the Android APK) ─────
pip install --user pycryptodome

# ── Verify crypto library ──────────────────────────────────────────────────────
python3 -c "from Crypto.Cipher import AES; print('pycryptodome OK')"

# ── Device keys reminder ───────────────────────────────────────────────────────
echo ""
echo "=== Next steps ==="
echo ""
echo "1. Install the Android APK for BLE advertising:"
echo "   Download goplusplus.apk from:"
echo "   https://github.com/weolopez/pokego/releases"
echo "   Then: Settings -> Install Unknown Apps -> allow your browser"
echo ""
echo "2. Provide device keys (extracted from your real GO Plus):"
echo "   mkdir -p /sdcard/goplusplus"
echo '   nano /sdcard/goplusplus/device_keys.json'
echo '   {"bt_addr":"AABBCCDDEEFF","device_key":"..32 hex..","blob":"..512 hex..","flash_data":"..20 hex.."}'
echo ""
echo "See REFERENCES.md for key extraction instructions."
echo ""
echo "=== Setup complete ==="
