import os
import hashlib
import jwt
from datetime import datetime, timedelta
from cryptography.fernet import Fernet

KEY_FILE = os.path.join(os.path.dirname(__file__), "secret.key")

def get_encryption_key():
    env_key = os.environ.get("CIRRUS_SECRET_KEY")
    if env_key:
        return env_key.encode()
        
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as f:
            return f.read()
    else:
        key = Fernet.generate_key()
        try:
            with open(KEY_FILE, "wb") as f:
                f.write(key)
        except Exception as e:
            print(f"Warning: Could not write secret.key file: {e}")
        return key

def encrypt_data(data: str) -> str:
    if not data:
        return ""
    key = get_encryption_key()
    fernet = Fernet(key)
    return fernet.encrypt(data.encode()).decode()

def decrypt_data(encrypted_data: str) -> str:
    if not encrypted_data:
        return ""
    key = get_encryption_key()
    fernet = Fernet(key)
    try:
        return fernet.decrypt(encrypted_data.encode()).decode()
    except Exception:
        return ""

# JWT and Password Hashing helpers
JWT_SECRET = os.environ.get("CIRRUS_JWT_SECRET", "super-secret-jwt-signing-key-for-cirrus-app-1234")
JWT_ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days expiration

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    # NIST-compliant PBKDF2-HMAC-SHA256
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
    return f"{salt.hex()}:{pwd_hash.hex()}"

def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, hash_hex = stored_hash.split(":")
        salt = bytes.fromhex(salt_hex)
        expected_hash = bytes.fromhex(hash_hex)
        pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        return pwd_hash == expected_hash
    except Exception:
        return False

def create_access_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_access_token(token: str) -> dict:
    try:
        # If token starts with Bearer, clean it up
        if token.startswith("Bearer "):
            token = token.replace("Bearer ", "")
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None
