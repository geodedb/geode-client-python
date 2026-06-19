"""Field-level encryption (FLE) for Geode (mirrors Go crypto/cipher.go).

Uses AES-256-GCM for authenticated encryption, HKDF-SHA256 to derive
separate encryption and HMAC keys from a master key (>= 32 bytes), and
HMAC-SHA256 for deterministic searchable hashing.
"""

import base64
import binascii
import hashlib
import hmac
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from .client import GeodeError

_KEY_SIZE = 32  # AES-256
_NONCE_SIZE = 12  # GCM nonce
_ENC_INFO = b"geode-encrypt"
_HMAC_INFO = b"geode-hmac"


class CryptoError(GeodeError):
    """Raised on encryption/decryption or key-derivation failure."""


def _derive_key(master_key: bytes, info: bytes) -> bytes:
    hkdf = HKDF(algorithm=SHA256(), length=_KEY_SIZE, salt=None, info=info)
    return bytes(hkdf.derive(master_key))


class Cipher:
    """Holds derived encryption and HMAC keys for field-level encryption."""

    def __init__(self, master_key: bytes) -> None:
        if len(master_key) < _KEY_SIZE:
            raise CryptoError(
                f"crypto: master key must be at least {_KEY_SIZE} bytes, "
                f"got {len(master_key)}"
            )
        self._enc_key = _derive_key(master_key, _ENC_INFO)
        self._hmac_key = _derive_key(master_key, _HMAC_INFO)
        self._aead = AESGCM(self._enc_key)

    def encrypt(self, plaintext: bytes) -> bytes:
        """Encrypt with AES-256-GCM; nonce is prepended to the ciphertext."""
        nonce = os.urandom(_NONCE_SIZE)
        ciphertext = bytes(self._aead.encrypt(nonce, plaintext, None))
        return nonce + ciphertext

    def decrypt(self, ciphertext: bytes) -> bytes:
        """Decrypt ciphertext produced by :meth:`encrypt`."""
        if len(ciphertext) < _NONCE_SIZE:
            raise CryptoError("crypto: ciphertext too short")
        nonce = ciphertext[:_NONCE_SIZE]
        data = ciphertext[_NONCE_SIZE:]
        try:
            return bytes(self._aead.decrypt(nonce, data, None))
        except InvalidTag as exc:
            raise CryptoError("crypto: decrypt: authentication failed") from exc

    def encrypt_string(self, plaintext: str) -> str:
        """Encrypt a string and return standard base64-encoded ciphertext."""
        return base64.b64encode(self.encrypt(plaintext.encode("utf-8"))).decode("ascii")

    def decrypt_string(self, encoded: str) -> str:
        """Base64-decode then decrypt, returning the original string."""
        try:
            raw = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise CryptoError("crypto: base64 decode") from exc
        return self.decrypt(raw).decode("utf-8")

    def hmac_hex(self, data: str) -> str:
        """HMAC-SHA256 of data as a 64-char lowercase hex digest."""
        mac = hmac.new(self._hmac_key, data.encode("utf-8"), hashlib.sha256)
        return mac.hexdigest()
