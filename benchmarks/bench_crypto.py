"""Benchmarks for field-level encryption (crypto.py)."""

from geode_client import Cipher

KEY = b"0123456789abcdef0123456789abcdef"
PAYLOAD = b"x" * 256
TEXT = "user@example.com"


class TestCryptoBenchmarks:
    def test_cipher_construction(self, benchmark):
        benchmark(Cipher, KEY)

    def test_encrypt(self, benchmark):
        cipher = Cipher(KEY)
        benchmark(cipher.encrypt, PAYLOAD)

    def test_decrypt(self, benchmark):
        cipher = Cipher(KEY)
        ct = cipher.encrypt(PAYLOAD)
        benchmark(cipher.decrypt, ct)

    def test_encrypt_string(self, benchmark):
        cipher = Cipher(KEY)
        benchmark(cipher.encrypt_string, TEXT)

    def test_hmac_hex(self, benchmark):
        cipher = Cipher(KEY)
        benchmark(cipher.hmac_hex, TEXT)
