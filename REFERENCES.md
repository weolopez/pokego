# References

All sources used in researching and implementing the GO Plus + BLE emulator.

---

## Primary Reference Implementations

### yohanes/pgpemu
- URL: <https://github.com/yohanes/pgpemu>
- License: MIT
- Language: C (ESP32 IDF)
- What we used: GATT profile UUIDs, LED command byte format, SFIDA crypto logic,
  AES-ECB / AES-CTR / AES-Hash mode definitions, button notification payloads,
  BLE advertising packet structure, manufacturer ID.
- Status: Original reverse-engineered emulator (2018). Targets the original
  GO Plus (device name `"Pokemon GO Plus"`), but the SFIDA protocol is identical
  to GO Plus+.
- Key files: `pgpemu-esp32/main/pgpemu.c`, `pgpemu-esp32/main/pgp-cert.c`,
  `pgpemu-esp32/main/aes.c`

### tristannottelman/Sulpog (fork of pgpemu)
- URL: <https://github.com/tristannottelman/Sulpog>
- License: MIT (derived from pgpemu)
- What we used: Confirmed LED command decoding; `pattern_id` heuristic for
  classifying game events (catch/spin/success/fail).

### Jesus805/pokeball-rs
- URL: <https://github.com/Jesus805/pokeball-rs>
- License: MIT
- Language: Rust
- What we used: Rust port confirming all service/characteristic UUIDs;
  SFIDA state machine structure; AES mode implementations cross-referenced
  against our Python port.
- Key module: `src/cert/`, `src/aes/`

---

## Device Key Extraction

### Jesus805/Suota-Go-Plus
- URL: <https://github.com/Jesus805/Suota-Go-Plus>
- Blog post: <https://coderjesus.com/blog/pgp-suota/>
- What it does: Exploits the DA14580 BLE SoC's SUOTA (Software Update Over The Air)
  mechanism to read OTP flash, extracting the `device_key`, `blob`, and `flash_data`
  from a real GO Plus without hardware modification.
- Required for: The three values that must go in `device_keys.json` before the SFIDA
  handshake will pass Niantic's server-side key verification.

---

## Reverse Engineering Writeup

### yohanes — "Reverse Engineering Pokemon GO Plus"
- URL: <https://tinyhack.com/2018/11/21/reverse-engineering-pokemon-go-plus/>
- What it covers: Initial protocol discovery, BLE sniffing methodology, SFIDA
  challenge-response structure, identification of DA14580 as the BLE SoC.

---

## Android BLE Reference

### Mygod/pogoplusle
- URL: <https://github.com/Mygod/pogoplusle>
- License: Apache 2.0
- Language: Kotlin (Android app)
- What we used: Confirmed `DEVICE_NAME_PGPP = "Pokemon GO Plus +"` (with trailing
  space-plus), confirmed same BLE service code paths for both GO Plus and GO Plus+,
  GO Plus+ MAC address prefixes (`7C:BB:8A:`, `98:B6:E9:`, `B8:78:26:`).

---

## BLE Peripheral Library

### bless
- PyPI: <https://pypi.org/project/bless/>
- GitHub: <https://github.com/kevincar/bless>
- License: MIT
- Used for: Python BLE GATT server (peripheral/advertiser role) via BlueZ/D-Bus
  on Linux / Android+Termux.

---

## Standard Bluetooth SIG UUIDs

- Battery Service (0x180F): <https://www.bluetooth.com/specifications/assigned-numbers/>
- Battery Level (0x2A19): same
- Device Information (0x180A): same
- CCCD (0x2902): same

---

## Known Gaps

1. **Synthetic key generation:** No open source project has demonstrated that
   Pokemon GO accepts auth responses from a device whose keys are not in Niantic's
   per-device database. Every working emulator uses keys extracted from a real device.

2. **GO Plus+ SFIDA confirmation:** The assumption that GO Plus+ uses identical
   SFIDA UUIDs and protocol to the original GO Plus is based on `pogoplusle` code
   analysis, not a documented successful full emulation of the GO Plus+ specifically.

3. **Termux BLE peripheral mode:** BlueZ's peripheral/advertiser role in Termux on
   Android is device- and firmware-dependent. Not confirmed on Samsung Galaxy A16 5G
   (One UI, non-rooted). The native Android APK path (Phase 3) is the reliable fallback.
