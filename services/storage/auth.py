from __future__ import annotations

import os
import hashlib
import hmac
import binascii
from threading import Lock
from typing import Optional

_USERS: dict[str, dict[str, str]] = {}
_LOCK = Lock()


def reset_users() -> None:
    with _LOCK:
        _USERS.clear()


def user_exists(username: str) -> bool:
    with _LOCK:
        return username in _USERS


def _hash_password(password: str, salt: Optional[bytes] = None) -> tuple[bytes, bytes]:
    if salt is None:
        salt = hashlib.sha256(os.urandom(60)).digest()
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return salt, dk


def create_user(username: str, password: str) -> bool:
    with _LOCK:
        if username in _USERS:
            return False
        salt, dk = _hash_password(password)
        _USERS[username] = {"salt": binascii.hexlify(salt).decode(), "hash": binascii.hexlify(dk).decode()}
        return True


def verify_user(username: str, password: str) -> bool:
    with _LOCK:
        row = _USERS.get(username)
        if not row:
            return False
        salt = binascii.unhexlify(row["salt"].encode())
        dk = binascii.unhexlify(row["hash"].encode())
    _, attempt = _hash_password(password, salt=salt)
    return hmac.compare_digest(attempt, dk)
