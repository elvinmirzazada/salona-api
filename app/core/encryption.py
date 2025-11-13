from cryptography.fernet import Fernet, InvalidToken
from app.core.config import settings
import base64
import logging

logger = logging.getLogger(__name__)


def get_encryption_key() -> bytes:
    """Get or generate encryption key from settings"""
    try:
        # Use SECRET_KEY as base for encryption key
        # Ensure it's exactly 32 bytes for Fernet
        if not settings.SECRET_KEY:
            raise ValueError("SECRET_KEY is not configured")

        key = settings.SECRET_KEY.encode()
        # Pad or truncate to 32 bytes, then base64 encode for Fernet
        key = key[:32].ljust(32, b'0')
        return base64.urlsafe_b64encode(key)
    except Exception as e:
        logger.error(f"Error generating encryption key: {str(e)}")
        raise


def encrypt_token(token: str) -> str:
    """Encrypt a token string"""
    try:
        if not token:
            raise ValueError("Token cannot be empty")

        fernet = Fernet(get_encryption_key())
        encrypted = fernet.encrypt(token.encode())
        return encrypted.decode()
    except ValueError as e:
        logger.error(f"Validation error during encryption: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error encrypting token: {str(e)}")
        raise RuntimeError(f"Failed to encrypt token: {str(e)}")


def decrypt_token(encrypted_token: str) -> str:
    """Decrypt an encrypted token string"""
    try:
        if not encrypted_token:
            raise ValueError("Encrypted token cannot be empty")

        fernet = Fernet(get_encryption_key())
        decrypted = fernet.decrypt(encrypted_token.encode())
        return decrypted.decode()
    except InvalidToken:
        logger.error("Invalid token provided for decryption")
        raise ValueError("Invalid or corrupted encrypted token")
    except ValueError as e:
        logger.error(f"Validation error during decryption: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error decrypting token: {str(e)}")
        raise RuntimeError(f"Failed to decrypt token: {str(e)}")
