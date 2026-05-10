"""
SFIDA Authentication Handshake — AES-128 Implementation

The GO Plus / GO Plus+ uses a proprietary certificate-based protocol
called SFIDA (from the Italian word for "challenge"). It runs over two
custom BLE characteristics (CHAR_CENTRAL_TO_SFIDA / CHAR_SFIDA_COMMANDS)
and uses three custom AES-128 modes.

Ported from:
  yohanes/pgpemu  (MIT) — https://github.com/yohanes/pgpemu
  Jesus805/pokeball-rs (MIT) — https://github.com/Jesus805/pokeball-rs

HANDSHAKE SUMMARY
-----------------
State 0 (INIT):
  Phone → device: 20 bytes (initiation bytes, content not critical)
  Device → phone: 378-byte ChallengeData struct

State 1 (CHALLENGE_SENT):
  Phone → device: 20-byte response (AES-derived from session key)
  Device verifies response; transitions to AUTHENTICATED or fails

State 2 (AUTHENTICATED):
  Normal BLE operation; button/LED characteristics active

States 3-5: Reconnect challenge-response using stored session key

State 6 (OPERATIONAL): Equivalent to state 2 after reconnect.

CHALLENGE DATA STRUCT (378 bytes, LE):
  [0:4]    state       uint32
  [4:20]   nonce       16 bytes (random per session)
  [20:100] enc_challenge  80 bytes (AES-CTR encrypted main challenge)
  [100:116] enc_hash    16 bytes (AES-Hash of enc_challenge)
  [116:122] bt_addr     6 bytes (device MAC, not reversed)
  [122:378] blob        256 bytes (device cert blob from OTP)

MAIN CHALLENGE PLAINTEXT (80 bytes):
  [0:6]   bt_addr reversed
  [6:22]  session_key (16 bytes, random)
  [22:38] nonce (16 bytes)
  [38:54] aes_ecb(device_key, session_key XOR nonce)
  [54:70] aes_hash(device_key, nonce, plaintext[0:54])
  [70:80] flash_data (10 bytes, device-specific)

AES MODES:
  ECB:  Standard AES-128-ECB on a single 16-byte block.
  CTR:  Nonce = [0x00][base[0:12]][0x00][counter_lo][counter_hi], counter from 1.
  Hash: Nonce = [0x39][base[1:13]][0x00][size_lo][size_hi];
        state = ECB(nonce); for each 16-byte block: state = ECB(state XOR block).
"""

import os
import struct
import logging
from enum import IntEnum
from typing import Optional, Tuple

from Crypto.Cipher import AES

from . import config

logger = logging.getLogger(__name__)


class SFIDAState(IntEnum):
    INIT               = 0
    CHALLENGE_SENT     = 1
    AUTHENTICATED      = 2
    RECONNECT_CHALLENGE = 3
    RECONNECT_VERIFYING = 4
    RECONNECT_VERIFIED  = 5
    OPERATIONAL        = 6


# ── Low-level AES primitives ──────────────────────────────────────────────────

def _ecb(key: bytes, block: bytes) -> bytes:
    return AES.new(key, AES.MODE_ECB).encrypt(block)


def _ctr_keystream_block(key: bytes, base_nonce: bytes, counter: int) -> bytes:
    nonce = bytearray(16)
    nonce[0] = 0x00
    nonce[1:13] = base_nonce[:12]
    nonce[13] = 0x00
    nonce[14] = counter & 0xFF
    nonce[15] = (counter >> 8) & 0xFF
    return _ecb(key, bytes(nonce))


def _aes_ctr(key: bytes, base_nonce: bytes, data: bytes) -> bytes:
    """Custom CTR encryption; counter starts at 1."""
    out = bytearray()
    for i, offset in enumerate(range(0, len(data), 16)):
        block = data[offset:offset + 16]
        keystream = _ctr_keystream_block(key, base_nonce, i + 1)
        out.extend(b ^ k for b, k in zip(block, keystream[:len(block)]))
    return bytes(out)


def _aes_hash(key: bytes, base_nonce: bytes, data: bytes, first_byte: int = 0x39) -> bytes:
    """Custom AES-Hash (SFIDA MAC). Returns 16 bytes."""
    nonce = bytearray(16)
    nonce[0] = first_byte
    nonce[1:13] = base_nonce[1:13]
    nonce[13] = 0x00
    size = len(data)
    nonce[14] = size & 0xFF
    nonce[15] = (size >> 8) & 0xFF

    state = _ecb(key, bytes(nonce))
    for offset in range(0, len(data), 16):
        block = (data[offset:offset + 16]).ljust(16, b'\x00')
        state = _ecb(key, bytes(s ^ b for s, b in zip(state, block)))
    return state


# ── Challenge builder ─────────────────────────────────────────────────────────

def _build_challenge(device_key: bytes, bt_addr: bytes, blob: bytes,
                     flash_data: bytes) -> Tuple[bytes, bytes, bytes]:
    """
    Build the 378-byte ChallengeData payload.
    Returns (challenge_bytes, session_key, nonce).
    """
    nonce       = os.urandom(16)
    session_key = os.urandom(16)

    # ── Main challenge plaintext (80 bytes) ───────────────────────────────────
    bt_addr_rev = bytes(reversed(bt_addr))
    inner_enc   = _ecb(device_key, bytes(session_key[i] ^ nonce[i] for i in range(16)))

    plaintext = (
        bt_addr_rev                                         # [0:6]
        + session_key                                       # [6:22]
        + nonce                                             # [22:38]
        + inner_enc                                         # [38:54]
        + b'\x00' * 16                                      # [54:70] hash placeholder
        + flash_data[:10].ljust(10, b'\x00')                # [70:80]
    )

    # Hash covers first 54 bytes of plaintext (up to and including inner_enc)
    inner_hash = _aes_hash(device_key, nonce, plaintext[:54])

    # Replace the placeholder at [54:70] with the real hash
    plaintext = plaintext[:54] + inner_hash + plaintext[70:]

    # ── Encrypt plaintext with AES-CTR ────────────────────────────────────────
    enc_challenge = _aes_ctr(device_key, nonce, plaintext)

    # ── Outer hash covers the encrypted challenge ─────────────────────────────
    outer_hash = _aes_hash(device_key, nonce, enc_challenge)

    # ── Assemble 378-byte struct ──────────────────────────────────────────────
    challenge = (
        struct.pack("<I", SFIDAState.CHALLENGE_SENT)  # [0:4]   state = 1
        + nonce                                        # [4:20]
        + enc_challenge                                # [20:100]
        + outer_hash                                   # [100:116]
        + bt_addr                                      # [116:122]
        + blob[:256].ljust(256, b'\x00')               # [122:378]
    )
    assert len(challenge) == 378
    return challenge, session_key, nonce


def _verify_response(device_key: bytes, session_key: bytes, nonce: bytes,
                     response: bytes) -> bool:
    """
    Verify the 20-byte response from Pokemon GO (state 1).
    The app derives a MAC over the session key using AES-Hash with first_byte=0x01.
    """
    expected = _aes_hash(device_key, nonce, session_key, first_byte=0x01)[:20]
    return response[:20] == expected


# ── Auth state machine ────────────────────────────────────────────────────────

class SFIDAAuth:
    """
    Manages the SFIDA auth state machine for one BLE connection.

    Usage:
        auth = SFIDAAuth()
        challenge = auth.handle_central_write(init_bytes)  # → 378 bytes to send
        result = auth.handle_central_write(response_bytes) # → None; check is_authenticated()
    """

    def __init__(self):
        self._state       = SFIDAState.INIT
        self._session_key: Optional[bytes] = None
        self._nonce:       Optional[bytes] = None

    @property
    def state(self) -> SFIDAState:
        return self._state

    def is_authenticated(self) -> bool:
        return self._state in (SFIDAState.AUTHENTICATED, SFIDAState.OPERATIONAL)

    def handle_central_write(self, data: bytes) -> Optional[bytes]:
        """
        Process bytes written to CHAR_CENTRAL_TO_SFIDA.
        Returns bytes to send via CHAR_SFIDA_COMMANDS notify, or None.
        """
        if self._state == SFIDAState.INIT:
            return self._handle_init(data)
        elif self._state == SFIDAState.CHALLENGE_SENT:
            return self._handle_response(data)
        else:
            logger.warning("Unexpected write in state %s", self._state.name)
            return None

    def _handle_init(self, data: bytes) -> Optional[bytes]:
        logger.info("SFIDA: received init (%d bytes), sending challenge", len(data))
        try:
            challenge, session_key, nonce = _build_challenge(
                config.DEVICE_KEY, config.BT_ADDR, config.BLOB, config.FLASH_DATA
            )
        except Exception:
            logger.exception("Failed to build SFIDA challenge")
            return None
        self._session_key = session_key
        self._nonce       = nonce
        self._state       = SFIDAState.CHALLENGE_SENT
        return challenge

    def _handle_response(self, data: bytes) -> Optional[bytes]:
        ok = _verify_response(config.DEVICE_KEY, self._session_key,
                               self._nonce, data)
        if ok:
            logger.info("SFIDA: authentication successful")
            self._state = SFIDAState.AUTHENTICATED
        else:
            logger.warning("SFIDA: authentication FAILED (wrong keys?)")
            self.reset()
        return None

    def reset(self):
        """Reset auth state on disconnect or failure."""
        self._state       = SFIDAState.INIT
        self._session_key = None
        self._nonce       = None
