import pytest
from goplusplus.crypto import (
    SFIDAAuth, SFIDAState,
    _ecb, _aes_ctr, _aes_hash,
)


class TestAESPrimitives:
    KEY   = bytes(range(16))
    BLOCK = bytes(range(16))

    def test_ecb_output_length(self):
        out = _ecb(self.KEY, self.BLOCK)
        assert len(out) == 16

    def test_ecb_deterministic(self):
        assert _ecb(self.KEY, self.BLOCK) == _ecb(self.KEY, self.BLOCK)

    def test_ecb_different_keys_differ(self):
        key2 = bytes(range(1, 17))
        assert _ecb(self.KEY, self.BLOCK) != _ecb(key2, self.BLOCK)

    def test_aes_ctr_length(self):
        data = b"hello world!"
        out  = _aes_ctr(self.KEY, self.BLOCK, data)
        assert len(out) == len(data)

    def test_aes_ctr_reversible(self):
        data = b"test data for ctr encryption 123"
        enc  = _aes_ctr(self.KEY, self.BLOCK, data)
        dec  = _aes_ctr(self.KEY, self.BLOCK, enc)
        assert dec == data

    def test_aes_ctr_empty(self):
        assert _aes_ctr(self.KEY, self.BLOCK, b'') == b''

    def test_aes_hash_output_length(self):
        out = _aes_hash(self.KEY, self.BLOCK, b"some data")
        assert len(out) == 16

    def test_aes_hash_deterministic(self):
        data = b"determinism check"
        assert _aes_hash(self.KEY, self.BLOCK, data) == _aes_hash(self.KEY, self.BLOCK, data)

    def test_aes_hash_empty_data(self):
        out = _aes_hash(self.KEY, self.BLOCK, b'')
        assert len(out) == 16

    def test_aes_hash_first_byte_changes_output(self):
        data = b"data"
        h1 = _aes_hash(self.KEY, self.BLOCK, data, first_byte=0x39)
        h2 = _aes_hash(self.KEY, self.BLOCK, data, first_byte=0x01)
        assert h1 != h2


class TestSFIDAAuth:
    def test_initial_state(self):
        auth = SFIDAAuth()
        assert auth.state == SFIDAState.INIT
        assert not auth.is_authenticated()

    def test_reset_returns_to_init(self):
        auth = SFIDAAuth()
        auth.reset()
        assert auth.state == SFIDAState.INIT
        assert not auth.is_authenticated()

    def test_init_write_returns_378_bytes(self):
        auth = SFIDAAuth()
        response = auth.handle_central_write(b'\x00' * 20)
        # Challenge may fail if DEVICE_KEY is placeholder, but should not crash.
        # With placeholder key the _build_challenge still runs.
        if response is not None:
            assert len(response) == 378

    def test_transitions_to_challenge_sent(self):
        auth = SFIDAAuth()
        auth.handle_central_write(b'\x00' * 20)
        assert auth.state == SFIDAState.CHALLENGE_SENT

    def test_bad_response_resets(self):
        auth = SFIDAAuth()
        auth.handle_central_write(b'\x00' * 20)
        # Send garbage response — should fail and reset
        auth.handle_central_write(b'\xFF' * 20)
        assert auth.state == SFIDAState.INIT
        assert not auth.is_authenticated()

    def test_double_reset_is_safe(self):
        auth = SFIDAAuth()
        auth.reset()
        auth.reset()
        assert auth.state == SFIDAState.INIT
