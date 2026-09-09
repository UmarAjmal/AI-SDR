import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

class TokenEncryptionError(Exception):
    pass

class TokenEncryptor:
    """
    AES-256-GCM authenticated envelope encryption for credentials,
    OAuth tokens, and secrets at rest.
    """
    def __init__(self, key: bytes | str | None = None):
        if key is None:
            raw_key = os.getenv("ENCRYPTION_KEY_SECRET", "k9_F_8a9B_3zQ2x1W_7vP0m5L4j3H2g1S0d9F8a7B6c=")
            if isinstance(raw_key, str):
                try:
                    self.key = base64.urlsafe_b64decode(raw_key.encode())
                except Exception:
                    # If not b64, pad or hash to 32 bytes
                    self.key = raw_key.encode().ljust(32, b"0")[:32]
            else:
                self.key = raw_key
        elif isinstance(key, str):
            try:
                self.key = base64.urlsafe_b64decode(key.encode())
            except Exception:
                self.key = key.encode().ljust(32, b"0")[:32]
        else:
            self.key = key

        if len(self.key) != 32:
            raise ValueError(f"AES-256 key must be exactly 32 bytes, got {len(self.key)}")

        self.aesgcm = AESGCM(self.key)

    def encrypt(self, plaintext: str, associated_data: str | None = None) -> str:
        """
        Encrypts plaintext using AES-256-GCM with a fresh 12-byte nonce.
        Returns base64url encoded string containing nonce + ciphertext + tag.
        """
        if not plaintext:
            return ""
        try:
            nonce = os.urandom(12)  # 96-bit nonce standard for GCM
            ad = associated_data.encode("utf-8") if associated_data else None
            ciphertext = self.aesgcm.encrypt(nonce, plaintext.encode("utf-8"), ad)
            combined = nonce + ciphertext
            return base64.urlsafe_b64encode(combined).decode("utf-8")
        except Exception as e:
            raise TokenEncryptionError(f"Encryption failed: {str(e)}") from e

    def decrypt(self, encrypted_b64: str, associated_data: str | None = None) -> str:
        """
        Decrypts base64url encoded string using AES-256-GCM.
        """
        if not encrypted_b64:
            return ""
        try:
            combined = base64.urlsafe_b64decode(encrypted_b64.encode("utf-8"))
            if len(combined) < 28:  # 12-byte nonce + 16-byte tag minimum
                raise ValueError("Encrypted data is too short")
            nonce = combined[:12]
            ciphertext = combined[12:]
            ad = associated_data.encode("utf-8") if associated_data else None
            decrypted = self.aesgcm.decrypt(nonce, ciphertext, ad)
            return decrypted.decode("utf-8")
        except Exception as e:
            raise TokenEncryptionError(f"Decryption failed: {str(e)}") from e

# Default instance
encryptor = TokenEncryptor()
