from cryptography.fernet import Fernet


def encrypt_token(raw_token: str, key: str) -> str:
    """Encrypt a token with a URL-safe Fernet key."""
    return Fernet(key.encode() if isinstance(key, str) else key).encrypt(raw_token.encode()).decode()


def decrypt_token(encrypted: str, key: str) -> str:
    return Fernet(key.encode() if isinstance(key, str) else key).decrypt(encrypted.encode()).decode()


# This is for Bot Builder wizard-session storage, not the generated bot runtime .env.
# A deployed bot uses its plain token in its own environment variables.
