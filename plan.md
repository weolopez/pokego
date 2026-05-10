# Coding Agent Prompt: Pokémon GO Plus + BLE Emulator on Android (Termux/Python)

## Project Overview

You are implementing a Pokémon GO Plus + device emulator that runs on an Android phone (Samsung Galaxy A16 5G) inside Termux using Python. The emulator advertises itself over Bluetooth Low Energy (BLE) as a legitimate GO Plus + accessory, allowing a second Android phone running Pokémon GO to connect to it as if it were the real hardware device.

The goal is to use existing open source reverse engineering work — do not reverse engineer the protocol yourself. Find, analyze, and build on top of existing community implementations.

---

## Target Environment

- **Device:** Samsung Galaxy A16 5G (non-rooted, no OEM unlock, AT&T firmware)
- **OS:** Android (latest One UI)
- **Runtime:** Termux (installed via GitHub APK, arm64-v8a)
- **Language:** Python 3 (preferred), Node.js acceptable as fallback
- **Network:** WiFi only, no SIM/cellular
- **BLE:** Peripheral mode (advertising + GATT server)
- **Persistence:** Must survive screen off via Termux:Boot + battery unrestricted mode

---

## Phase 0 — Research & Protocol Extraction

Before writing any implementation code, complete the following research tasks:

### 0.1 — Find Reference Implementations

Search GitHub for existing GO Plus / GO Plus + BLE emulators. Priority targets:

- ESP32-based emulators (most mature, protocol is fully documented in these)
- Raspberry Pi Python implementations
- Any Android-specific BLE peripheral emulators for GO Plus

Recommended search queries:
```
pokemon go plus BLE emulator ESP32
pokemon go plus GATT characteristics python
goplusplus bluetooth peripheral android
pogo accessory BLE protocol
```

Key repositories to check:
- Search for forks/stars on any repo with "goplusplus", "go-plus-plus", "pokemon-go-ble"
- Check XDA Developers and r/pokemongodev for linked repositories

### 0.2 — Extract the GATT Profile

From whichever reference implementation you find, document the complete GATT profile:

```
Device Name (advertised): "Pokemon GO Plus +"
Service UUIDs: [extract from reference]
Characteristics:
  - [UUID]: Button state notification
  - [UUID]: LED/Vibration control (write)
  - [UUID]: Certificate/auth (read/write)
  - [UUID]: Any others found
Descriptor UUIDs: [extract any CCCD or custom descriptors]
```

### 0.3 — Document the Encryption Handshake

The GO Plus + uses a certificate-based authentication handshake with Pokémon GO. Document:
- What cryptographic algorithm is used (AES? EC?)
- What keys/certificates are exchanged
- Whether existing implementations have hardcoded working keys or require per-device certs
- Whether the handshake has been fully solved in any open source project

**This is the highest risk item.** If no open source project has solved the handshake, document exactly where it is stuck and what is known.

---

## Phase 1 — Environment Setup (Termux)

Generate a complete setup script for Termux. The script must be idempotent (safe to run twice).

### 1.1 — setup.sh

```bash
#!/data/data/com.termux/files/usr/bin/bash
set -e

echo "=== GO Plus + Emulator Setup ==="

# Update package index
pkg update -y && pkg upgrade -y

# Core dependencies
pkg install -y python git bluez termux-api

# Python BLE library
# Prefer 'bleak' if BLE peripheral mode is supported on this Android version
# Fall back to 'bluepy' or direct bluetoothctl/D-Bus approach if not
pip install bleak

# Check if BLE peripheral (advertiser) mode is available
python3 -c "
import asyncio
from bleak import BleakScanner
print('bleak installed OK')
"

# Clone reference implementation (fill in after Phase 0)
# git clone <reference_repo_url> reference/

echo "=== Setup Complete ==="
```

### 1.2 — Verify BLE Peripheral Support

Before any implementation, verify the A16 5G supports BLE peripheral/advertiser mode in Termux:

```python
# check_ble.py
import subprocess
import sys

def check_ble_peripheral():
    """Check if BLE advertising (peripheral mode) is available."""
    
    # Check bluetoothctl availability
    result = subprocess.run(['bluetoothctl', 'show'], 
                          capture_output=True, text=True)
    print("bluetoothctl output:")
    print(result.stdout)
    
    # Look for advertising support
    if 'Advertising' in result.stdout:
        print("✓ BLE advertising may be supported")
    else:
        print("✗ BLE advertising not found in bluetoothctl output")
    
    # Check for le-advertising-manager
    result2 = subprocess.run(['bluetoothctl', 'list'], 
                           capture_output=True, text=True)
    print(result2.stdout)

check_ble_peripheral()
```

**If BLE peripheral mode is not available in Termux:** Document this clearly and provide the Android Java/Kotlin alternative implementation path (see Phase 3).

---

## Phase 2 — Core Python Emulator

Implement the emulator as a clean Python package. Structure:

```
goplusplus/
  __init__.py
  gatt_profile.py      # All UUIDs and characteristic definitions
  crypto.py            # Handshake/encryption logic
  peripheral.py        # BLE advertising + GATT server
  controller.py        # Button/LED/vibration state machine
  main.py              # Entry point
  config.py            # All tuneable constants
README.md
requirements.txt
start.sh               # Simple launcher
```

### 2.1 — gatt_profile.py

Define ALL UUIDs and characteristic properties extracted from reference implementation:

```python
# gatt_profile.py
from dataclasses import dataclass
from enum import Enum
from typing import List

# Device identity
DEVICE_NAME = "Pokemon GO Plus +"
MANUFACTURER_ID = 0x0001  # Fill from reference

# Service UUIDs (fill from Phase 0 research)
SERVICE_UUID_MAIN = "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
SERVICE_UUID_BATTERY = "0000180f-0000-1000-8000-00805f9b34fb"
SERVICE_UUID_DEVICE_INFO = "0000180a-0000-1000-8000-00805f9b34fb"

# Characteristic UUIDs (fill from Phase 0 research)
CHAR_UUID_BUTTON = "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
CHAR_UUID_LED_VIBRATE = "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
CHAR_UUID_CERTIFICATE = "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
CHAR_UUID_BATTERY_LEVEL = "00002a19-0000-1000-8000-00805f9b34fb"

class ButtonState(Enum):
    RELEASED = 0x00
    PRESSED = 0x01

class LEDColor(Enum):
    OFF = 0x00
    RED = 0x01
    YELLOW = 0x02
    GREEN = 0x03
    CYAN = 0x04
    BLUE = 0x05
    MAGENTA = 0x06
    WHITE = 0x07

@dataclass
class CharacteristicDef:
    uuid: str
    properties: List[str]  # ["read", "write", "notify", etc.]
    description: str

CHARACTERISTICS = {
    "button": CharacteristicDef(
        uuid=CHAR_UUID_BUTTON,
        properties=["notify"],
        description="Button press notifications"
    ),
    "led_vibrate": CharacteristicDef(
        uuid=CHAR_UUID_LED_VIBRATE,
        properties=["write"],
        description="LED color and vibration control"
    ),
    "certificate": CharacteristicDef(
        uuid=CHAR_UUID_CERTIFICATE,
        properties=["read", "write"],
        description="Authentication certificate exchange"
    ),
}
```

### 2.2 — crypto.py

Implement the authentication handshake based on the reference implementation:

```python
# crypto.py
"""
GO Plus + Authentication Handshake

Based on: [cite reference implementation URL here]

The handshake flow (document from reference):
1. [Step 1]
2. [Step 2]
3. [Step 3]
"""

import hashlib
import hmac
from typing import Optional, Tuple

class GOPlusAuth:
    """Handles the certificate-based auth handshake with Pokemon GO."""
    
    def __init__(self):
        # Keys extracted from reference implementation
        # Document their origin clearly
        self._device_cert = None  # Fill from reference
        self._private_key = None  # Fill from reference
        self._session_key = None
        self._authenticated = False
    
    def handle_challenge(self, challenge_bytes: bytes) -> bytes:
        """
        Process incoming auth challenge from Pokemon GO app.
        Returns response bytes to send back.
        """
        raise NotImplementedError(
            "Fill in from reference implementation. "
            "See: [reference repo URL]"
        )
    
    def is_authenticated(self) -> bool:
        return self._authenticated
    
    def reset(self):
        """Reset auth state on disconnect."""
        self._session_key = None
        self._authenticated = False
```

### 2.3 — peripheral.py

The main BLE peripheral using bleak or bluetoothctl:

```python
# peripheral.py
"""
BLE Peripheral (GATT Server + Advertiser)

Advertises as "Pokemon GO Plus +" and handles connections
from the Pokemon GO app.
"""

import asyncio
import logging
from typing import Callable, Optional
from .gatt_profile import (
    DEVICE_NAME, SERVICE_UUID_MAIN, 
    CHAR_UUID_BUTTON, CHAR_UUID_LED_VIBRATE, CHAR_UUID_CERTIFICATE
)
from .crypto import GOPlusAuth

logger = logging.getLogger(__name__)

class GOPlusPeripheral:
    """
    BLE GATT server that emulates the GO Plus + hardware.
    
    NOTE: bleak's peripheral/server API differs by platform and version.
    On Android via Termux, you may need to use D-Bus directly or 
    a different approach. Implement whichever works and document why.
    """
    
    def __init__(self):
        self.auth = GOPlusAuth()
        self._connected = False
        self._notify_enabled = False
        self._on_led_command: Optional[Callable] = None
        self._on_connect: Optional[Callable] = None
        self._on_disconnect: Optional[Callable] = None
    
    def on_led_command(self, callback: Callable):
        """Register callback for LED/vibration commands from the app."""
        self._on_led_command = callback
    
    async def start_advertising(self):
        """Start BLE advertising as GO Plus +."""
        logger.info(f"Starting BLE advertising as '{DEVICE_NAME}'")
        # Implementation depends on available BLE stack
        # Try: bleak server API, bluetoothctl advertise, or D-Bus
        raise NotImplementedError
    
    async def stop(self):
        """Stop advertising and disconnect any clients."""
        raise NotImplementedError
    
    def _handle_write(self, characteristic_uuid: str, data: bytes):
        """Handle incoming writes from Pokemon GO app."""
        if characteristic_uuid == CHAR_UUID_CERTIFICATE:
            # Authentication handshake
            response = self.auth.handle_challenge(data)
            return response
        elif characteristic_uuid == CHAR_UUID_LED_VIBRATE:
            # Decode LED/vibration command
            self._decode_led_command(data)
    
    def _decode_led_command(self, data: bytes):
        """Parse LED color + vibration pattern from command bytes."""
        # Format: [fill from reference implementation]
        if self._on_led_command:
            self._on_led_command(data)
    
    async def send_button_press(self):
        """Notify Pokemon GO app of a button press event."""
        if not self._notify_enabled:
            logger.warning("Notifications not enabled, can't send button press")
            return
        button_payload = bytes([0x01])  # Fill from reference
        # Send notification on button characteristic
        raise NotImplementedError
    
    async def send_button_release(self):
        """Notify Pokemon GO app of button release."""
        button_payload = bytes([0x00])  # Fill from reference
        raise NotImplementedError
```

### 2.4 — controller.py

State machine for the button/LED interaction loop:

```python
# controller.py
"""
GO Plus + Interaction Controller

Manages the state machine for:
- Auto-catching nearby Pokemon (vibrate yellow → press → vibrate based on result)  
- Auto-spinning PokéStops (vibrate blue → press → vibrate based on result)
- Manual button override
"""

import asyncio
import logging
from enum import Enum, auto
from .peripheral import GOPlusPeripheral

logger = logging.getLogger(__name__)

class DeviceState(Enum):
    IDLE = auto()
    POKEMON_NEARBY = auto()          # Yellow flash
    CATCHING = auto()                 # Sending button press
    CATCH_SUCCESS = auto()            # Green flash
    CATCH_FAILED = auto()             # Red flash
    POKESTOP_NEARBY = auto()          # Blue flash
    SPINNING = auto()                 # Sending button press
    SPIN_SUCCESS = auto()             # Blue solid
    SPIN_FAILED = auto()              # Red flash
    INVENTORY_FULL = auto()           # Yellow flash (can't catch/spin)

class GOPlusController:
    """
    High-level controller that drives the peripheral
    based on incoming LED/vibration commands from Pokemon GO.
    
    Pokemon GO sends LED commands to tell the device what's happening:
    - Yellow flash = Pokemon nearby
    - Blue flash = PokeStop nearby
    - Green flash = Catch success
    - etc.
    
    The device responds by sending button press notifications
    to trigger the catch/spin action.
    """
    
    def __init__(self, peripheral: GOPlusPeripheral):
        self.peripheral = peripheral
        self.state = DeviceState.IDLE
        self.auto_catch = True
        self.auto_spin = True
        self._setup_callbacks()
    
    def _setup_callbacks(self):
        self.peripheral.on_led_command(self._on_led_command)
    
    def _on_led_command(self, data: bytes):
        """Decode LED command and update state, trigger auto-press if configured."""
        # Decode color + pattern from data bytes
        # Reference implementation will show exact byte format
        color = data[0] if data else 0x00
        
        logger.debug(f"LED command: {data.hex()} (color={color})")
        
        # Map LED color to state
        # Fill these mappings from reference implementation
        STATE_MAP = {
            0x01: DeviceState.POKEMON_NEARBY,
            0x03: DeviceState.CATCH_SUCCESS,
            # etc.
        }
        
        new_state = STATE_MAP.get(color, DeviceState.IDLE)
        self._transition(new_state)
    
    def _transition(self, new_state: DeviceState):
        logger.info(f"State: {self.state.name} → {new_state.name}")
        self.state = new_state
        asyncio.create_task(self._handle_state(new_state))
    
    async def _handle_state(self, state: DeviceState):
        if state == DeviceState.POKEMON_NEARBY and self.auto_catch:
            await asyncio.sleep(0.5)  # Brief delay like real device
            await self.peripheral.send_button_press()
            await asyncio.sleep(0.1)
            await self.peripheral.send_button_release()
        
        elif state == DeviceState.POKESTOP_NEARBY and self.auto_spin:
            await asyncio.sleep(0.5)
            await self.peripheral.send_button_press()
            await asyncio.sleep(0.1)
            await self.peripheral.send_button_release()
```

### 2.5 — main.py

```python
# main.py
"""
GO Plus + Emulator — Entry Point

Usage:
  python3 -m goplusplus
  python3 main.py [--no-auto-catch] [--no-auto-spin] [--debug]
"""

import asyncio
import argparse
import logging
import signal
import sys

from goplusplus.peripheral import GOPlusPeripheral
from goplusplus.controller import GOPlusController

def parse_args():
    parser = argparse.ArgumentParser(description="Pokemon GO Plus + Emulator")
    parser.add_argument("--no-auto-catch", action="store_true", 
                       help="Disable auto-catching Pokemon")
    parser.add_argument("--no-auto-spin", action="store_true",
                       help="Disable auto-spinning PokeStops")
    parser.add_argument("--debug", action="store_true",
                       help="Enable debug logging")
    return parser.parse_args()

async def main():
    args = parse_args()
    
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    
    logger = logging.getLogger("main")
    logger.info("=== Pokemon GO Plus + Emulator ===")
    
    peripheral = GOPlusPeripheral()
    controller = GOPlusController(peripheral)
    
    if args.no_auto_catch:
        controller.auto_catch = False
        logger.info("Auto-catch disabled")
    
    if args.no_auto_spin:
        controller.auto_spin = False
        logger.info("Auto-spin disabled")
    
    # Graceful shutdown on Ctrl+C
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()
    
    def shutdown():
        logger.info("Shutting down...")
        stop_event.set()
    
    loop.add_signal_handler(signal.SIGINT, shutdown)
    loop.add_signal_handler(signal.SIGTERM, shutdown)
    
    try:
        logger.info("Starting BLE advertising...")
        await peripheral.start_advertising()
        logger.info("Ready. Waiting for Pokemon GO to connect...")
        await stop_event.wait()
    finally:
        await peripheral.stop()
        logger.info("Stopped.")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Phase 3 — Fallback: Android App (If Termux BLE Peripheral Fails)

If Termux cannot run a BLE GATT server (common limitation), implement a minimal Android APK.

### 3.1 — Architecture

```
MainActivity.java          # Minimal UI (just a toggle + status)
GOPlusService.java         # Foreground service with BLE GATT server
GattServerCallback.java    # Handles connect/read/write/notify
GOPlusAdvertiser.java      # Manages BLE advertising
GOPlusAuth.java            # Handshake logic (port from crypto.py)
```

### 3.2 — BLE Peripheral in Android

```kotlin
// GOPlusAdvertiser.kt
class GOPlusAdvertiser(private val context: Context) {
    
    private val bluetoothManager = 
        context.getSystemService(Context.BLUETOOTH_SERVICE) as BluetoothManager
    private val bluetoothAdapter = bluetoothManager.adapter
    private val advertiser = bluetoothAdapter.bluetoothLeAdvertiser
    
    fun startAdvertising() {
        val settings = AdvertiseSettings.Builder()
            .setAdvertiseMode(AdvertiseSettings.ADVERTISE_MODE_LOW_LATENCY)
            .setConnectable(true)
            .setTimeout(0)
            .setTxPowerLevel(AdvertiseSettings.ADVERTISE_TX_POWER_HIGH)
            .build()
        
        val data = AdvertiseData.Builder()
            .setIncludeDeviceName(true)
            .addServiceUuid(ParcelUuid.fromString(SERVICE_UUID_MAIN))
            .build()
        
        // Set device name
        bluetoothAdapter.name = "Pokemon GO Plus +"
        
        advertiser.startAdvertising(settings, data, advertiseCallback)
    }
}
```

### 3.3 — Build Without Android Studio

Use **Termux** to build the APK directly on the phone:

```bash
pkg install gradle openjdk-17
# Build minimal debug APK without needing Android Studio
gradle assembleDebug
adb install app/build/outputs/apk/debug/app-debug.apk
```

---

## Phase 4 — Persistence & Reliability

### 4.1 — Termux:Boot Auto-Start

```bash
# ~/.termux/boot/start-goplusplus.sh
#!/data/data/com.termux/files/usr/bin/bash
# Auto-starts emulator on device reboot

# Wait for system to settle
sleep 10

# Start emulator in background with logging
cd /data/data/com.termux/files/home/goplusplus
python3 main.py >> ~/goplusplus.log 2>&1 &

echo "GO Plus + emulator started (PID: $!)"
```

### 4.2 — Battery Optimization

Manual steps to document for the user:
1. Settings → Battery → Background usage limits → Never sleeping apps → Add Termux
2. Settings → Apps → Termux → Battery → Unrestricted
3. Pull down notification shade → Long press Termux notification → Always show

### 4.3 — Watchdog

```python
# watchdog.sh — restart emulator if it crashes
#!/data/data/com.termux/files/usr/bin/bash
while true; do
    python3 /data/data/com.termux/files/home/goplusplus/main.py
    echo "$(date): Emulator crashed, restarting in 5s..."
    sleep 5
done
```

---

## Phase 5 — Testing & Validation

### 5.1 — Unit Tests

```python
# tests/test_gatt_profile.py
import pytest
from goplusplus.gatt_profile import DEVICE_NAME, SERVICE_UUID_MAIN

def test_device_name():
    assert DEVICE_NAME == "Pokemon GO Plus +"

def test_uuids_are_valid():
    import re
    uuid_pattern = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        re.IGNORECASE
    )
    assert uuid_pattern.match(SERVICE_UUID_MAIN)

# tests/test_crypto.py
from goplusplus.crypto import GOPlusAuth

def test_auth_initial_state():
    auth = GOPlusAuth()
    assert not auth.is_authenticated()

def test_auth_reset():
    auth = GOPlusAuth()
    auth.reset()
    assert not auth.is_authenticated()
```

### 5.2 — BLE Scan Verification

From a third device or laptop, verify the emulator is advertising correctly:

```bash
# On Linux laptop
sudo hcitool lescan | grep "Pokemon GO Plus"
# Should see: XX:XX:XX:XX:XX:XX Pokemon GO Plus +

# More detail
sudo btmgmt find | grep -A5 "Pokemon GO"
```

### 5.3 — Integration Test Checklist

```
[ ] Phone advertising "Pokemon GO Plus +" visible to BLE scanner
[ ] Pokemon GO app detects the device in accessory pairing
[ ] Authentication handshake completes without error
[ ] App shows device as "connected"
[ ] LED command received when Pokemon nearby
[ ] Auto button press sent within 1 second
[ ] Catch attempt registered in game
[ ] PokeStop spin works same way
[ ] Device survives screen-off for 30 minutes
[ ] Device auto-reconnects after app restart
```

---

## Deliverables Checklist

Upon completion, the following must exist and work:

- [ ] `setup.sh` — one-command Termux setup
- [ ] `goplusplus/` — complete Python package
- [ ] `start.sh` — simple launch script
- [ ] `~/.termux/boot/start-goplusplus.sh` — auto-start on reboot
- [ ] `tests/` — passing unit tests
- [ ] `README.md` — complete with install instructions, known issues, reference links
- [ ] `REFERENCES.md` — all source repos/issues/writeups used, with commit hashes
- [ ] If Termux BLE peripheral unsupported: working Android APK alternative

---

## Constraints & Ground Rules

1. **Do not reverse engineer the protocol yourself.** Use existing community work.
2. **Document every reference used** — URL, commit hash, what you took from it.
3. **If the encryption handshake is unsolved,** document exactly what is known and where the gap is. Do not fabricate a solution.
4. **If BLE peripheral mode is unavailable in Termux,** say so clearly and pivot to the Android APK path.
5. **All code must run on arm64-v8a Android in Termux** — no x86-only libraries.
6. **No root required.** If any step requires root, flag it and provide a non-root alternative.
7. **Follow existing code style** from whichever reference implementation you port from.

---

## What Success Looks Like

A second Android phone running Pokémon GO can:
1. Open the accessory pairing screen
2. See "Pokemon GO Plus +" in the device list
3. Successfully pair and authenticate
4. Auto-catch nearby Pokémon via the emulator
5. Auto-spin nearby PokéStops via the emulator

All of this while the emulating phone sits nearby with its screen off, running persistently on WiFi.

