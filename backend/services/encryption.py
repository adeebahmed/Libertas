import base64
import os
from typing import Optional


from cryptography.hazmat.primitives.ciphers.aead import AESGCM

PREFIX = "enc1:"

_active_key: Optional[bytes] = None


def get_active_key() -> Optional[bytes]:
    return _active_key


def set_active_key(key: bytes) -> None:
    global _active_key
    _active_key = key


def clear_active_key() -> None:
    global _active_key
    _active_key = None


def init_keychain_key() -> bytes:
    import keyring
    stored = keyring.get_password("libertas", "db_encryption_key")
    if stored:
        return base64.b64decode(stored)
    key = os.urandom(32)
    keyring.set_password("libertas", "db_encryption_key", base64.b64encode(key).decode())
    return key


def derive_passphrase_key(passphrase: str, salt: bytes) -> bytes:
    from argon2.low_level import hash_secret_raw, Type
    return hash_secret_raw(
        secret=passphrase.encode(),
        salt=salt,
        time_cost=3,
        memory_cost=65536,
        parallelism=4,
        hash_len=32,
        type=Type.ID,
    )


def encrypt_value(plaintext: str, key: bytes) -> str:
    nonce = os.urandom(12)
    ct = AESGCM(key).encrypt(nonce, plaintext.encode(), None)
    return base64.b64encode(nonce + ct).decode()


def decrypt_value(token: str, key: bytes) -> str:
    data = base64.b64decode(token)
    nonce, ct = data[:12], data[12:]
    return AESGCM(key).decrypt(nonce, ct, None).decode()


def load_key_on_startup(db) -> None:
    from ..models import Setting
    row = db.query(Setting).filter(Setting.key == "encryption_mode").first()
    mode = row.value.strip('"') if row and row.value else "keychain"
    if mode == "keychain":
        try:
            key = init_keychain_key()
            set_active_key(key)
        except Exception:
            pass  # keyring unavailable (CI/headless) — run without encryption
