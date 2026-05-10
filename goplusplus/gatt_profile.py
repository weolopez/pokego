"""
All UUIDs and characteristic definitions for the GO Plus + GATT profile.

Sources:
  yohanes/pgpemu   https://github.com/yohanes/pgpemu  (MIT)
  Jesus805/pokeball-rs  https://github.com/Jesus805/pokeball-rs  (MIT)

The GO Plus+ uses the same GATT profile as the original GO Plus; only
the advertised device name differs. The SFIDA auth protocol (certificate
service) is also identical.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List

# ── Identity ──────────────────────────────────────────────────────────────────

DEVICE_NAME = "Pokemon GO Plus +"
MANUFACTURER_ID = 0x0462  # Nintendo Co. Ltd.

# ── Service UUIDs ─────────────────────────────────────────────────────────────

SERVICE_UUID_BATTERY    = "0000180f-0000-1000-8000-00805f9b34fb"
SERVICE_UUID_DEVICE_INFO = "0000180a-0000-1000-8000-00805f9b34fb"
SERVICE_UUID_LED_BUTTON = "21c50462-67cb-63a3-5c4c-82b5b9939aeb"
SERVICE_UUID_CERT       = "bbe87709-5b89-4433-ab7f-8b8eef0d8e37"

# ── LED/Button Characteristic UUIDs ───────────────────────────────────────────

CHAR_LED            = "21c50462-67cb-63a3-5c4c-82b5b9939aec"  # write
CHAR_BUTTON         = "21c50462-67cb-63a3-5c4c-82b5b9939aed"  # notify
CHAR_UNKNOWN_WRITE  = "21c50462-67cb-63a3-5c4c-82b5b9939aee"  # write
CHAR_UPDATE_REQUEST = "21c50462-67cb-63a3-5c4c-82b5b9939aef"  # write
CHAR_FW_VERSION     = "21c50462-67cb-63a3-5c4c-82b5b9939af0"  # read

# ── Certificate / SFIDA Characteristic UUIDs ──────────────────────────────────

CHAR_CENTRAL_TO_SFIDA = "bbe87709-5b89-4433-ab7f-8b8eef0d8e38"  # write
CHAR_SFIDA_COMMANDS   = "bbe87709-5b89-4433-ab7f-8b8eef0d8e39"  # notify
CHAR_SFIDA_TO_CENTRAL = "bbe87709-5b89-4433-ab7f-8b8eef0d8e3a"  # read

# ── Battery Characteristic ────────────────────────────────────────────────────

CHAR_BATTERY_LEVEL = "00002a19-0000-1000-8000-00805f9b34fb"  # read + notify

# ── Descriptor ───────────────────────────────────────────────────────────────

CCCD_UUID = "00002902-0000-1000-8000-00805f9b34fb"

# ── Button Notification Payloads ──────────────────────────────────────────────

BUTTON_PRESSED  = bytes([0x03, 0xFF])
BUTTON_RELEASED = bytes([0x00, 0x00])

# ── LED Command Decoder ───────────────────────────────────────────────────────

class LEDColor(Enum):
    OFF     = (0, 0, 0)
    RED     = (15, 0, 0)
    YELLOW  = (15, 15, 0)
    GREEN   = (0, 15, 0)
    CYAN    = (0, 15, 15)
    BLUE    = (0, 0, 15)
    MAGENTA = (15, 0, 15)
    WHITE   = (15, 15, 15)


@dataclass
class LEDPattern:
    duration: int
    red: int
    green: int
    blue: int


@dataclass
class LEDCommand:
    """Decoded LED/vibration command written by Pokemon GO to CHAR_LED."""
    priority: int
    patterns: List[LEDPattern] = field(default_factory=list)

    @classmethod
    def decode(cls, data: bytes) -> "LEDCommand":
        """
        Byte layout (from pgpemu.c):
          data[3] = (num_patterns & 0x1F) | ((priority & 0x07) << 5)
          For each pattern (3 bytes at data[4 + 3*i]):
            byte 0: duration
            byte 1: (green << 4) | red
            byte 2: blue (lower nibble)
        """
        if len(data) < 4:
            return cls(priority=0)
        num_patterns = data[3] & 0x1F
        priority     = (data[3] >> 5) & 0x07
        patterns = []
        for i in range(num_patterns):
            p = 4 + 3 * i
            if p + 2 >= len(data):
                break
            duration = data[p]
            red      = data[p + 1] & 0x0F
            green    = (data[p + 1] >> 4) & 0x0F
            blue     = data[p + 2] & 0x0F
            patterns.append(LEDPattern(duration, red, green, blue))
        return cls(priority=priority, patterns=patterns)

    def pattern_id(self) -> int:
        """Identify event type by summing all RGB values (pgpemu heuristic)."""
        total = 0
        for p in self.patterns:
            total += p.red + p.green + p.blue
        return total


# Pattern ID ranges observed in the wild (from pgpemu / community notes)
PATTERN_POKEMON_NEARBY  = range(1, 5)    # Yellow flash
PATTERN_POKESTOP_NEARBY = range(5, 9)    # Blue flash
PATTERN_CATCH_SUCCESS   = range(9, 13)   # Green flash
PATTERN_CATCH_FAIL      = range(13, 17)  # Red flash
PATTERN_SPIN_SUCCESS    = range(17, 21)  # Blue solid
PATTERN_SPIN_FAIL       = range(21, 25)  # Red flash


@dataclass
class CharacteristicDef:
    uuid: str
    properties: List[str]
    description: str


CHARACTERISTICS = {
    "led":              CharacteristicDef(CHAR_LED,            ["write"],           "LED/vibration command"),
    "button":           CharacteristicDef(CHAR_BUTTON,         ["notify"],          "Button press notifications"),
    "unknown_write":    CharacteristicDef(CHAR_UNKNOWN_WRITE,  ["write"],           "Unknown (write)"),
    "update_request":   CharacteristicDef(CHAR_UPDATE_REQUEST, ["write"],           "Firmware update request"),
    "fw_version":       CharacteristicDef(CHAR_FW_VERSION,     ["read"],            "Firmware version"),
    "central_to_sfida": CharacteristicDef(CHAR_CENTRAL_TO_SFIDA, ["write"],        "Auth: phone → device"),
    "sfida_commands":   CharacteristicDef(CHAR_SFIDA_COMMANDS, ["notify"],          "Auth: SFIDA commands"),
    "sfida_to_central": CharacteristicDef(CHAR_SFIDA_TO_CENTRAL, ["read"],          "Auth: device → phone"),
    "battery":          CharacteristicDef(CHAR_BATTERY_LEVEL,  ["read", "notify"],  "Battery level (0-100)"),
}
