import base64
import hashlib
from typing import Optional, Any
from cryptography.fernet import Fernet
from app.core.config import settings

def _get_fernet_key() -> bytes:
    key_bytes = settings.PROFILE_ENCRYPTION_KEY.encode('utf-8')
    # Hash to 32 bytes and base64-encode to get valid Fernet key
    digest = hashlib.sha256(key_bytes).digest()
    return base64.urlsafe_b64encode(digest)

def encrypt_value(val: Any) -> Optional[str]:
    if val is None:
        return None
    try:
        f = Fernet(_get_fernet_key())
        val_str = str(val)
        return f.encrypt(val_str.encode('utf-8')).decode('utf-8')
    except Exception:
        return str(val)

def decrypt_value(val: Optional[str]) -> Optional[str]:
    if not val:
        return val
    try:
        f = Fernet(_get_fernet_key())
        return f.decrypt(val.encode('utf-8')).decode('utf-8')
    except Exception:
        return val
