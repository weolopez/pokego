"""
BLE GATT Server + Advertiser

Android does NOT use BlueZ — it has its own BLE stack that is not accessible
from Termux/Python. BLE peripheral mode (advertising + GATT server) requires
the native Android APK in the android/ directory.

The Python package handles the SFIDA crypto (crypto.py) which the Android APK
calls out to via a local socket, OR which you can port directly from crypto.py
into the Kotlin implementation in android/app/.

To run the emulator: install android/goplusplus.apk on your Samsung A6.
Download a pre-built APK from: https://github.com/weolopez/pokego/releases
"""

raise RuntimeError(
    "BLE peripheral mode is not available from Python/Termux on Android.\n"
    "Install the Android APK instead:\n"
    "  https://github.com/weolopez/pokego/releases\n"
    "See plus/android/ for source code."
)
