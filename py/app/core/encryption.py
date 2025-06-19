"""
Simple Encryption Utilities
"""
import base64
import json
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import uuid

from .config import settings


def _generate_key(user_id: uuid.UUID) -> bytes:
    """Generate encryption key from user ID"""
    # Use user ID + encryption key to generate consistent encryption key
    encryption_key = settings.ENCRYPTION_KEY or settings.SECRET_KEY  # Fallback to SECRET_KEY
    password = f"{encryption_key}:{str(user_id)}".encode()
    salt = b"salt_1234567890"  # In production, use random salt per user
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password))
    return key


def encrypt_credentials(user_id: uuid.UUID, credentials: dict) -> str:
    """Encrypt user credentials"""
    key = _generate_key(user_id)
    f = Fernet(key)
    
    # Convert dict to JSON string then encrypt
    credentials_json = json.dumps(credentials)
    encrypted_data = f.encrypt(credentials_json.encode())
    
    return base64.urlsafe_b64encode(encrypted_data).decode()


def decrypt_credentials(user_id: uuid.UUID, encrypted_data: str) -> dict:
    """Decrypt user credentials"""
    key = _generate_key(user_id)
    f = Fernet(key)
    
    # Decode and decrypt
    encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
    decrypted_data = f.decrypt(encrypted_bytes)
    
    # Convert back to dict
    return json.loads(decrypted_data.decode())


def _generate_tool_key(tool_name: str) -> bytes:
    """Generate encryption key from tool name"""
    # Use tool name + encryption key to generate consistent encryption key
    encryption_key = settings.ENCRYPTION_KEY or settings.SECRET_KEY  # Fallback to SECRET_KEY
    password = f"{encryption_key}:tool:{tool_name}".encode()
    salt = b"tool_salt_123456"  # Tool-specific salt
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password))
    return key


def encrypt_tool_variable(tool_name: str, variable_value: str) -> str:
    """Encrypt tool environment variable"""
    key = _generate_tool_key(tool_name)
    f = Fernet(key)
    
    # Encrypt the variable value
    encrypted_data = f.encrypt(variable_value.encode())
    
    return base64.urlsafe_b64encode(encrypted_data).decode()


def decrypt_tool_variable(tool_name: str, encrypted_data: str) -> str:
    """Decrypt tool environment variable"""
    key = _generate_tool_key(tool_name)
    f = Fernet(key)
    
    # Decode and decrypt
    encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
    decrypted_data = f.decrypt(encrypted_bytes)
    
    return decrypted_data.decode() 