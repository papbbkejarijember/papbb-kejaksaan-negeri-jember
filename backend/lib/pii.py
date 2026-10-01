import os

from cryptography.fernet import Fernet, InvalidToken


def _cipher() -> Fernet:
    key = os.environ.get("PII_ENCRYPTION_KEY")
    if not key:
        raise RuntimeError("PII_ENCRYPTION_KEY belum dikonfigurasi")
    return Fernet(key.encode())


def encrypt_pii(value: str) -> str:
    return _cipher().encrypt(value.encode()).decode()


def decrypt_pii(value: str) -> str:
    try:
        return _cipher().decrypt(value.encode()).decode()
    except InvalidToken as exc:
        raise RuntimeError("Data identitas tidak dapat didekripsi") from exc
