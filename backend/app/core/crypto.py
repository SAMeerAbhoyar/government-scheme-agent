import base64
import hashlib
import logging
from typing import Optional, Any
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.types import TypeDecorator, Text
from app.core.config import settings

logger = logging.getLogger(__name__)

def get_fernet_key(key: Optional[str] = None) -> bytes:
    raw_key = key if key is not None else getattr(settings, "ENCRYPTION_KEY", None)
    if not raw_key:
        raise ValueError("ENCRYPTION_KEY is required for encryption")
    digest = hashlib.sha256(raw_key.encode('utf-8')).digest()
    return base64.urlsafe_b64encode(digest)

def encrypt_value(val: Any, key: Optional[str] = None) -> Optional[str]:
    if val is None:
        return None
    f = Fernet(get_fernet_key(key))
    val_str = str(val)
    return f.encrypt(val_str.encode('utf-8')).decode('utf-8')

def decrypt_value(val: Optional[str], key: Optional[str] = None) -> Optional[str]:
    if val is None or val == "":
        return val
    val_str = str(val)
    if not val_str.startswith("gAAAA"):
        # Plaintext legacy value fallback
        return val_str

    try:
        f = Fernet(get_fernet_key(key))
        return f.decrypt(val_str.encode('utf-8')).decode('utf-8')
    except Exception as e:
        logger.warning(f"Failed to decrypt Fernet token: {e}. Treating value as None.")
        return None

class EncryptedString(TypeDecorator):
    """
    SQLAlchemy TypeDecorator using Fernet (cryptography).
    Encrypts values at rest in DB and decrypts when loaded.
    """
    impl = Text
    cache_ok = True

    def __init__(self, underlying_type=str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.underlying_type = underlying_type

    def process_bind_param(self, value: Any, dialect) -> Optional[str]:
        if value is None:
            return None
        return encrypt_value(value)

    def process_result_value(self, value: Optional[str], dialect) -> Any:
        if value is None:
            return None
        decrypted_str = decrypt_value(value)
        if decrypted_str is None:
            return None

        if self.underlying_type is bool:
            if isinstance(decrypted_str, bool):
                return decrypted_str
            if str(decrypted_str).lower() in ("true", "1"):
                return True
            if str(decrypted_str).lower() in ("false", "0"):
                return False
            return bool(decrypted_str)
        elif self.underlying_type is float:
            try:
                return float(decrypted_str)
            except (ValueError, TypeError):
                return decrypted_str
        elif self.underlying_type is int:
            try:
                return int(decrypted_str)
            except (ValueError, TypeError):
                return decrypted_str
        return decrypted_str
