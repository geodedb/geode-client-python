"""Unit tests for field-level encryption (crypto.py)."""

import base64

import pytest

from geode_client import Cipher, CryptoError

KEY = b"0123456789abcdef0123456789abcdef"  # exactly 32 bytes


class TestCipherConstruction:
    def test_short_key_rejected(self):
        with pytest.raises(CryptoError):
            Cipher(b"too-short")

    def test_min_length_key_ok(self):
        Cipher(KEY)

    def test_longer_key_ok(self):
        Cipher(KEY + b"extra-bytes")


class TestEncryptDecrypt:
    def test_round_trip_bytes(self):
        c = Cipher(KEY)
        pt = b"sensitive payload"
        ct = c.encrypt(pt)
        assert ct != pt
        assert c.decrypt(ct) == pt

    def test_nonce_prepended_makes_ciphertext_longer(self):
        c = Cipher(KEY)
        ct = c.encrypt(b"x")
        # 12-byte nonce + 1 byte data + 16-byte GCM tag = 29
        assert len(ct) == 12 + 1 + 16

    def test_encrypt_is_randomised(self):
        c = Cipher(KEY)
        assert c.encrypt(b"same") != c.encrypt(b"same")

    def test_round_trip_string(self):
        c = Cipher(KEY)
        enc = c.encrypt_string("hello world")
        # std base64 round-trips
        base64.b64decode(enc)
        assert c.decrypt_string(enc) == "hello world"

    def test_decrypt_too_short_raises(self):
        c = Cipher(KEY)
        with pytest.raises(CryptoError):
            c.decrypt(b"short")

    def test_decrypt_tampered_raises(self):
        c = Cipher(KEY)
        ct = bytearray(c.encrypt(b"hello"))
        ct[-1] ^= 0xFF
        with pytest.raises(CryptoError):
            c.decrypt(bytes(ct))

    def test_decrypt_string_bad_base64_raises(self):
        c = Cipher(KEY)
        with pytest.raises(CryptoError):
            c.decrypt_string("!!!not base64!!!")

    def test_cross_key_decrypt_fails(self):
        c1 = Cipher(KEY)
        c2 = Cipher(b"ffffffffffffffffffffffffffffffff")
        ct = c1.encrypt(b"secret")
        with pytest.raises(CryptoError):
            c2.decrypt(ct)


class TestHMAC:
    def test_hmac_deterministic(self):
        c = Cipher(KEY)
        assert c.hmac_hex("alice@example.com") == c.hmac_hex("alice@example.com")

    def test_hmac_hex_format(self):
        c = Cipher(KEY)
        digest = c.hmac_hex("x")
        assert len(digest) == 64
        assert digest == digest.lower()
        int(digest, 16)  # valid hex

    def test_hmac_differs_by_input(self):
        c = Cipher(KEY)
        assert c.hmac_hex("a") != c.hmac_hex("b")

    def test_hmac_differs_by_key(self):
        c1 = Cipher(KEY)
        c2 = Cipher(b"ffffffffffffffffffffffffffffffff")
        assert c1.hmac_hex("a") != c2.hmac_hex("a")
