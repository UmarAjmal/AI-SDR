import pytest
from packages.common.encryption import TokenEncryptor, TokenEncryptionError

def test_token_encryption_and_decryption():
    encryptor = TokenEncryptor()
    token = "test-sample-crm-token-verification-12345"
    
    # Encrypt
    encrypted_token = encryptor.encrypt(token)
    assert encrypted_token != token
    assert len(encrypted_token) > 20

    # Decrypt
    decrypted_token = encryptor.decrypt(encrypted_token)
    assert decrypted_token == token

def test_fresh_nonce_per_encryption():
    encryptor = TokenEncryptor()
    token = "constant-oauth-token-12345"

    enc1 = encryptor.encrypt(token)
    enc2 = encryptor.encrypt(token)

    # AES-256-GCM uses a fresh 12-byte random nonce for every call
    assert enc1 != enc2
    assert encryptor.decrypt(enc1) == token
    assert encryptor.decrypt(enc2) == token

def test_tampered_ciphertext_fails_auth_tag():
    encryptor = TokenEncryptor()
    token = "secret-refresh-token"
    enc = encryptor.encrypt(token)

    # Tamper with the ciphertext
    tampered = enc[:-4] + "AAAA"
    with pytest.raises(TokenEncryptionError):
        encryptor.decrypt(tampered)
