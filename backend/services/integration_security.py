import base64
import hashlib
import os
from functools import lru_cache

from cryptography.fernet import Fernet

from ..database import DB_PATH


def _derive_fallback_key() -> bytes:
    seed = f"{os.path.abspath(DB_PATH)}|{os.getenv('USER','libertas')}|libertas-local".encode()
    digest = hashlib.sha256(seed).digest()
    return base64.urlsafe_b64encode(digest)


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    key = os.getenv("LIBERTAS_SECRET_KEY")
    if key:
        raw = key.encode()
        if len(raw) != 44:
            raw = base64.urlsafe_b64encode(hashlib.sha256(raw).digest())
    else:
        raw = _derive_fallback_key()
    return Fernet(raw)


def encrypt_secret(value: str) -> str:
    if not value:
        return ""
    return _fernet().encrypt(value.encode()).decode()


def decrypt_secret(value: str) -> str:
    if not value:
        return ""
    return _fernet().decrypt(value.encode()).decode()
