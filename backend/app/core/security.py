import hashlib
import hmac
import json
import base64
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from app.core.config import settings

# Password Hashing Helper using PBKDF2 HMAC SHA256 (standard Python hashlib)
def hash_password(password: str) -> str:
    salt = settings.SECRET_KEY[:16].encode("utf-8")
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return base64.b64encode(key).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hmac.compare_digest(hash_password(plain_password), hashed_password)

# Lightweight, robust JWT implementation using standard library hashlib & hmac
def b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')

def b64_decode(data_str: str) -> bytes:
    padding = '=' * (4 - (len(data_str) % 4))
    return base64.urlsafe_b64decode(data_str + padding)

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": int(expire.timestamp())})
    
    header = {"alg": "HS256", "typ": "JWT"}
    header_encoded = b64_encode(json.dumps(header).encode('utf-8'))
    payload_encoded = b64_encode(json.dumps(to_encode).encode('utf-8'))
    
    signature_base = f"{header_encoded}.{payload_encoded}".encode('utf-8')
    signature = hmac.new(settings.JWT_SECRET.encode('utf-8'), signature_base, hashlib.sha256).digest()
    signature_encoded = b64_encode(signature)
    
    return f"{header_encoded}.{payload_encoded}.{signature_encoded}"

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        
        header_encoded, payload_encoded, signature_encoded = parts
        signature_base = f"{header_encoded}.{payload_encoded}".encode('utf-8')
        
        expected_sig = b64_encode(hmac.new(settings.JWT_SECRET.encode('utf-8'), signature_base, hashlib.sha256).digest())
        if not hmac.compare_digest(signature_encoded, expected_sig):
            return None
        
        payload_bytes = b64_decode(payload_encoded)
        payload = json.loads(payload_bytes.decode('utf-8'))
        
        # Expiry check
        if "exp" in payload and payload["exp"] < int(time.time()):
            return None
        
        return payload
    except Exception:
        return None
