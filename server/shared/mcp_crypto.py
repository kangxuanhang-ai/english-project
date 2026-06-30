import base64
import hashlib
import json

from cryptography.fernet import Fernet

from app.config import settings


def _fernet() -> Fernet:
    digest = hashlib.sha256(settings.secret_key.encode()).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_headers(headers: dict[str, str]) -> str:
    return _fernet().encrypt(json.dumps(headers).encode()).decode()


def decrypt_headers(token: str) -> dict[str, str]:
    raw = _fernet().decrypt(token.encode())
    data = json.loads(raw.decode())
    if not isinstance(data, dict):
        raise ValueError("invalid headers payload")
    return {str(k): str(v) for k, v in data.items()}
