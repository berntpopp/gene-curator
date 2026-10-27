"""Credential cipher: a MultiFernet key ring for provider API keys.

Keys come from LLM_CREDENTIAL_KEYS (JSON {kid: fernet_key}) and
LLM_CREDENTIAL_ACTIVE_KID. They are never derived from SECRET_KEY, so rotating
the JWT secret does not touch stored credentials and vice versa.
"""

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass

from cryptography.fernet import Fernet, InvalidToken, MultiFernet


class CredentialCipherError(Exception):
    """Key ring misconfigured or ciphertext unreadable. Messages never carry secrets."""


@dataclass(frozen=True)
class EncryptedCredential:
    ciphertext: bytes
    key_id: str
    fingerprint: str


def fingerprint(secret: str) -> str:
    """Short, non-reversible identifier shown to admins instead of the key."""
    return "sha256:" + hashlib.sha256(secret.encode()).hexdigest()[:16]


class CredentialCipher:
    def __init__(self, keys: Mapping[str, str], active_kid: str) -> None:
        if not keys or active_kid not in keys:
            raise CredentialCipherError(
                "LLM credential key ring missing or active kid unknown"
            )
        try:
            self._fernets = {kid: Fernet(key) for kid, key in keys.items()}
        except (ValueError, TypeError):
            raise CredentialCipherError(
                "LLM credential key ring holds an invalid key"
            ) from None
        self._active_kid = active_kid
        others = [f for kid, f in self._fernets.items() if kid != active_kid]
        self._ring = MultiFernet([self._fernets[active_kid], *others])

    @classmethod
    def from_env(cls, keys_json: str, active_kid: str) -> "CredentialCipher":
        try:
            keys = json.loads(keys_json) if keys_json else {}
        except json.JSONDecodeError:
            raise CredentialCipherError(
                "LLM_CREDENTIAL_KEYS is not valid JSON"
            ) from None
        if not isinstance(keys, dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in keys.items()
        ):
            raise CredentialCipherError(
                "LLM_CREDENTIAL_KEYS must be a JSON object of strings"
            )
        return cls(keys, active_kid)

    @classmethod
    def from_settings(cls) -> "CredentialCipher":
        from app.core.config import settings

        return cls.from_env(
            settings.LLM_CREDENTIAL_KEYS, settings.LLM_CREDENTIAL_ACTIVE_KID
        )

    def encrypt(self, secret: str) -> EncryptedCredential:
        if not secret:
            raise CredentialCipherError("Refusing to encrypt an empty credential")
        return EncryptedCredential(
            ciphertext=self._fernets[self._active_kid].encrypt(secret.encode()),
            key_id=self._active_kid,
            fingerprint=fingerprint(secret),
        )

    def decrypt(self, ciphertext: bytes) -> str:
        try:
            return self._ring.decrypt(ciphertext).decode()
        except InvalidToken:
            raise CredentialCipherError(
                "Credential cannot be decrypted with the key ring"
            ) from None

    def rotate(self, ciphertext: bytes) -> EncryptedCredential:
        """Re-encrypt under the active kid (for `make rotate-llm-keys`)."""
        return self.encrypt(self.decrypt(ciphertext))
