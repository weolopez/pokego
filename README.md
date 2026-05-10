# Pokemon GO Plus + BLE Emulator

Emulates a Pokemon GO Plus + accessory over Bluetooth LE on an Android phone.
The BLE peripheral implementation runs in the native Android app (`plus/android`).
Termux scripts are helper wrappers that launch the installed APK.

---

## Requirements

- Android phone with Bluetooth LE
- GO Plus + Android APK installed (`com.pokego.plus`)
- Optional: Termux + Termux:Boot (only for script-based launch on boot)
- A real Pokemon GO Plus or GO Plus+ to extract device keys from (see below)

---

## Installation

```bash
# 1. Clone the project onto your Android phone (optional if using release APK only)
git clone https://github.com/weolopez/pokego ~/pokego
cd ~/pokego/plus

# 2. Run setup (installs helper tools and prints APK/key setup steps)
bash setup.sh
```

Install the APK from:
https://github.com/weolopez/pokego/releases

---

## Device Key Extraction

**This is the hardest step.** The SFIDA auth protocol requires three values
burned into the OTP flash of your physical GO Plus / GO Plus+:

| Value | Size | Description |
|-------|------|-------------|
| `bt_addr` | 6 bytes | Bluetooth MAC of your real device |
| `device_key` | 16 bytes | AES-128 key from OTP flash |
| `blob` | 256 bytes | Certificate blob from OTP flash |
| `flash_data` | 10 bytes | Device-specific flash data |

**Extraction tool:** [Suota-Go-Plus](https://github.com/Jesus805/Suota-Go-Plus)
by Jesus805 — uses the DA14580's OTA update mechanism to read OTP memory
without hardware modification.

Full extraction writeup: <https://coderjesus.com/blog/pgp-suota/>

Once you have the values, create `plus/device_keys.json`:

```json
{
  "bt_addr":    "AABBCCDDEEFF",
  "device_key": "0102030405060708090a0b0c0d0e0f10",
  "blob":       "..512 hex chars..",
  "flash_data": "00000000000000000000"
}
```

Alternatively, export them as environment variables:
```bash
export GOPLUSPLUS_BT_ADDR=AABBCCDDEEFF
export GOPLUSPLUS_DEVICE_KEY=...
export GOPLUSPLUS_BLOB=...
export GOPLUSPLUS_FLASH_DATA=...
```

**Never commit `device_keys.json` to version control.**

---

## Usage

```bash
# Start from Termux (launches app + foreground service)
bash start.sh

# Compatibility wrapper (currently same as start.sh)
bash watchdog.sh
```

First run: open the app and grant Bluetooth/location/storage permissions.

---

## Verify BLE Advertising

From a laptop or third device:

```bash
# Linux
sudo hcitool lescan | grep "Pokemon GO Plus"

# More detail
sudo btmgmt find | grep -A5 "Pokemon GO"
```

Expected: `XX:XX:XX:XX:XX:XX  Pokemon GO Plus +`

---

## Auto-Start on Reboot

`setup.sh` installs `boot/start-goplusplus.sh` into `~/.termux/boot/`.

Required manual steps:
1. Settings → Battery → Background usage limits → Never sleeping apps → Add **Termux**
2. Settings → Apps → Termux → Battery → **Unrestricted**
3. Notification shade → long-press Termux notification → **Always show**

---

## Architecture

```
goplusplus/
  gatt_profile.py   All UUIDs, LED command decoder, characteristic definitions
  crypto.py         SFIDA AES-128 handshake (3 custom modes + 6-state machine)
  config.py         Device key loading from file / env vars
  peripheral.py     BLE GATT server via bless (BlueZ/D-Bus)
  controller.py     LED→state machine→button-press logic
  main.py           CLI entry point
```

The LED/Button and Certificate GATT services run on the same BLE peripheral.
Pokemon GO writes LED commands to signal game events; the emulator responds
with button-press notifications to trigger catches and spins.

---

## Known Limitations

1. **Auth requires real device keys.** No synthetic key generation is known to
   work against Niantic's server-side validation. See REFERENCES.md.

2. **Python BLE mode is disabled on Android/Termux.** BLE peripheral mode is
  provided by the native Android app in `android/`.

3. **GO Plus+ vs original GO Plus.** The GATT service UUIDs and SFIDA protocol
   are assumed identical (based on `Mygod/pogoplusle` code analysis).
   This has not been confirmed by a documented successful GO Plus+ emulation.

---

## Running Tests

```bash
pip install pytest
cd plus/
pytest tests/ -v
```

---

## Project Layout

```
plus/
  goplusplus/        Python crypto/protocol reference code
  android/           Native Android BLE emulator (runtime path)
  tests/             Unit tests
  boot/              Termux:Boot script (launches Android app via start.sh)
  plan.md            Full implementation plan
  setup.sh           Termux helper setup + APK/key instructions
  start.sh           Starts installed Android app/service from Termux
  watchdog.sh        Compatibility wrapper for start.sh
  check_ble.py       BLE environment checker
  requirements.txt
  README.md
  REFERENCES.md
```
# pokego
