import re
import pytest
from goplusplus.gatt_profile import (
    DEVICE_NAME, MANUFACTURER_ID,
    SERVICE_UUID_BATTERY, SERVICE_UUID_LED_BUTTON, SERVICE_UUID_CERT,
    CHAR_LED, CHAR_BUTTON, CHAR_FW_VERSION,
    CHAR_CENTRAL_TO_SFIDA, CHAR_SFIDA_COMMANDS, CHAR_SFIDA_TO_CENTRAL,
    CHAR_BATTERY_LEVEL,
    BUTTON_PRESSED, BUTTON_RELEASED,
    LEDCommand, LEDPattern,
)

UUID_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    re.IGNORECASE,
)

ALL_UUIDS = [
    SERVICE_UUID_BATTERY, SERVICE_UUID_LED_BUTTON, SERVICE_UUID_CERT,
    CHAR_LED, CHAR_BUTTON, CHAR_FW_VERSION,
    CHAR_CENTRAL_TO_SFIDA, CHAR_SFIDA_COMMANDS, CHAR_SFIDA_TO_CENTRAL,
    CHAR_BATTERY_LEVEL,
]


def test_device_name():
    assert DEVICE_NAME == "Pokemon GO Plus +"


def test_manufacturer_id():
    assert MANUFACTURER_ID == 0x0462  # Nintendo Co. Ltd.


def test_all_uuids_are_valid():
    for uuid in ALL_UUIDS:
        assert UUID_RE.match(uuid), f"Invalid UUID: {uuid}"


def test_uuid_uniqueness():
    assert len(ALL_UUIDS) == len(set(ALL_UUIDS)), "Duplicate UUID found"


def test_button_payloads():
    assert BUTTON_PRESSED  == bytes([0x03, 0xFF])
    assert BUTTON_RELEASED == bytes([0x00, 0x00])


class TestLEDCommand:
    def _make_cmd(self, patterns):
        """Build raw LED command bytes for a list of (duration, r, g, b) tuples."""
        num = len(patterns)
        data = bytearray(4 + 3 * num)
        data[3] = num & 0x1F
        for i, (dur, r, g, b) in enumerate(patterns):
            p = 4 + 3 * i
            data[p]     = dur
            data[p + 1] = (g << 4) | r
            data[p + 2] = b
        return bytes(data)

    def test_decode_single_pattern(self):
        raw = self._make_cmd([(10, 1, 2, 3)])
        cmd = LEDCommand.decode(raw)
        assert len(cmd.patterns) == 1
        assert cmd.patterns[0].duration == 10
        assert cmd.patterns[0].red   == 1
        assert cmd.patterns[0].green == 2
        assert cmd.patterns[0].blue  == 3

    def test_decode_multiple_patterns(self):
        raw = self._make_cmd([(5, 15, 0, 0), (5, 0, 15, 0)])
        cmd = LEDCommand.decode(raw)
        assert len(cmd.patterns) == 2

    def test_priority_field(self):
        data = bytearray(4)
        data[3] = (2 << 5) | 1  # priority=2, num_patterns=1
        cmd = LEDCommand.decode(bytes(data))
        assert cmd.priority == 2

    def test_pattern_id_sum(self):
        raw = self._make_cmd([(10, 3, 0, 0)])  # red=3
        cmd = LEDCommand.decode(raw)
        assert cmd.pattern_id() == 3

    def test_empty_data(self):
        cmd = LEDCommand.decode(b'')
        assert cmd.priority == 0
        assert cmd.patterns == []

    def test_truncated_data(self):
        # Only 3 bytes — shouldn't crash
        cmd = LEDCommand.decode(b'\x00\x00\x00')
        assert cmd.patterns == []
