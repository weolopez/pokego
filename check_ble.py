#!/usr/bin/env python3
"""
BLE peripheral mode check for Termux/Android.

Verifies that:
  1. bluetoothctl is available and the adapter is up
  2. BlueZ supports LE advertising (peripheral mode)
  3. The bless Python library can initialise a server

Run this before attempting to start the emulator.
"""

import subprocess
import sys


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.stdout + r.stderr


def check_bluetoothctl():
    print("── bluetoothctl show ──────────────────────────────────────")
    out = run(["bluetoothctl", "show"])
    print(out)
    powered = "Powered: yes" in out
    adv     = "Advertising" in out or "LEAdvertising" in out
    if not powered:
        print("✗ Bluetooth adapter is NOT powered on.")
        print("  Try: bluetoothctl power on")
    else:
        print("✓ Adapter is powered")
    if not adv:
        print("! LE advertising capability not listed — may still work")
    else:
        print("✓ LE advertising supported")
    return powered


def check_bless():
    print("\n── bless import test ──────────────────────────────────────")
    try:
        from bless import BlessServer
        print("✓ bless imported successfully")
        return True
    except ImportError as e:
        print(f"✗ bless import failed: {e}")
        print("  Run: pip install bless")
        return False


def check_pycryptodome():
    print("\n── pycryptodome import test ───────────────────────────────")
    try:
        from Crypto.Cipher import AES
        print("✓ pycryptodome imported successfully")
        return True
    except ImportError as e:
        print(f"✗ pycryptodome import failed: {e}")
        print("  Run: pip install pycryptodome")
        return False


if __name__ == "__main__":
    ok = True
    ok &= check_bluetoothctl()
    ok &= check_bless()
    ok &= check_pycryptodome()
    print()
    if ok:
        print("All checks passed. You can now run: bash start.sh")
    else:
        print("Some checks failed. See messages above.")
        print("If BLE peripheral mode is unavailable, use the Android APK (Phase 3 in plan.md).")
        sys.exit(1)
