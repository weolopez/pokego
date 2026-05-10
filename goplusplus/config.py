"""
All tuneable constants and device identity values.

HOW TO OBTAIN DEVICE KEYS
--------------------------
You must own a physical Pokemon GO Plus + and extract three values from it:

  1. BT_ADDR  — The Bluetooth MAC address of your real device.
                Read it from the GO Plus + packaging or from the Pokemon GO
                accessory pairing screen (Settings → Pokemon GO Plus).

  2. DEVICE_KEY — 16-byte AES key burned into the DA14580 BLE SoC's OTP flash.
                  Extract using the SUOTA (Over-The-Air Update) exploit documented
                  at https://coderjesus.com/blog/pgp-suota/ with the tool at
                  https://github.com/Jesus805/Suota-Go-Plus

  3. BLOB — 256-byte certificate blob read from the same OTP region.
            Extracted by the same Suota-Go-Plus tool as DEVICE_KEY.

  4. FLASH_DATA — 10 bytes of device-specific flash data (also from OTP).

Without these values the SFIDA authentication handshake will fail.
The Pokemon GO app verifies responses against Niantic's server-side key database.
There is no known way to generate synthetic keys that pass verification.

SECURITY NOTE
-------------
Never commit real key material to version control. Store these in a
separate file (e.g. device_keys.json) excluded via .gitignore, or pass
them as environment variables.
"""

import os
import json
import logging

logger = logging.getLogger(__name__)

# ── BLE Advertising ────────────────────────────────────────────────────────────

ADV_INTERVAL_MIN_MS = 20
ADV_INTERVAL_MAX_MS = 40

# ── Battery ────────────────────────────────────────────────────────────────────

BATTERY_LEVEL = 80  # Reported battery percentage (any value 0-100 is accepted)

# ── Firmware Version ───────────────────────────────────────────────────────────

FIRMWARE_VERSION = bytes([0x00, 0x01])  # Arbitrary; not validated by Pokemon GO

# ── Device Key Material ────────────────────────────────────────────────────────
# Load from environment or a keys file. Defaults are placeholders that will
# cause auth to fail — replace with real extracted values.

def _load_keys() -> dict:
    keys_file = os.environ.get("GOPLUSPLUS_KEYS_FILE", "device_keys.json")
    if os.path.exists(keys_file):
        with open(keys_file) as f:
            return json.load(f)
    return {}


_keys = _load_keys()


def _hex(env_var: str, key: str, length: int, default: bytes) -> bytes:
    raw = os.environ.get(env_var) or _keys.get(key)
    if raw:
        return bytes.fromhex(raw)
    logger.warning(
        "Device key '%s' not configured — auth will fail. "
        "See config.py for extraction instructions.", key
    )
    return default


BT_ADDR: bytes = _hex(
    "GOPLUSPLUS_BT_ADDR", "bt_addr", 6,
    bytes([0xDE, 0xAD, 0xBE, 0xEF, 0x00, 0x00])
)

DEVICE_KEY: bytes = _hex(
    "GOPLUSPLUS_DEVICE_KEY", "device_key", 16,
    bytes(16)
)

BLOB: bytes = _hex(
    "GOPLUSPLUS_BLOB", "blob", 256,
    bytes(256)
)

FLASH_DATA: bytes = _hex(
    "GOPLUSPLUS_FLASH_DATA", "flash_data", 10,
    bytes(10)
)

# ── Controller Defaults ────────────────────────────────────────────────────────

AUTO_CATCH_DELAY_S  = 0.5   # Seconds before sending button press for a catch
AUTO_SPIN_DELAY_S   = 0.5   # Seconds before sending button press for a spin
BUTTON_HOLD_MS      = 100   # Milliseconds to hold button pressed
