"""Credential cipher: key ring, rotation, fail-closed config."""

import json

import pytest
from cryptography.fernet import Fernet

from app.llm.crypto import CredentialCipher, CredentialCipherError, fingerprint

K1, K2 = Fernet.generate_key().decode(), Fernet.generate_key().decode()
CRED = "sk-test-0123456789abcdef"


def test_encrypt_decrypt_roundtrip_reports_kid_and_fingerprint() -> None:
    cipher = CredentialCipher({"k1": K1}, "k1")
    enc = cipher.encrypt(CRED)
    assert enc.key_id == "k1"
    assert enc.fingerprint == fingerprint(CRED)
    assert CRED not in enc.fingerprint
    assert CRED.encode() not in enc.ciphertext
    assert cipher.decrypt(enc.ciphertext) == CRED


def test_decrypt_with_any_ring_key_and_rotate_to_active() -> None:
    old = CredentialCipher({"k1": K1}, "k1").encrypt(CRED)
    ring = CredentialCipher({"k1": K1, "k2": K2}, "k2")
    assert ring.decrypt(old.ciphertext) == CRED
    rotated = ring.rotate(old.ciphertext)
    assert rotated.key_id == "k2"
    assert rotated.fingerprint == old.fingerprint
    # Only k2 is needed after rotation.
    assert CredentialCipher({"k2": K2}, "k2").decrypt(rotated.ciphertext) == CRED


def test_unknown_ciphertext_fails_closed() -> None:
    other = CredentialCipher({"k2": K2}, "k2").encrypt(CRED)
    with pytest.raises(CredentialCipherError) as exc:
        CredentialCipher({"k1": K1}, "k1").decrypt(other.ciphertext)
    assert CRED not in str(exc.value)


@pytest.mark.parametrize(
    ("keys_json", "active"),
    [
        ("", "k1"),
        ("{}", "k1"),
        ("not json", "k1"),
        ('["a"]', "k1"),
        (json.dumps({"k1": 5}), "k1"),
        (json.dumps({"k1": K1}), "missing"),
        (json.dumps({"k1": "not-a-fernet-key"}), "k1"),
    ],
)
def test_bad_key_ring_fails_closed(keys_json: str, active: str) -> None:
    with pytest.raises(CredentialCipherError):
        CredentialCipher.from_env(keys_json, active)


def test_empty_secret_rejected() -> None:
    with pytest.raises(CredentialCipherError):
        CredentialCipher({"k1": K1}, "k1").encrypt("")


def test_from_settings_reads_dedicated_env_not_secret_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "LLM_CREDENTIAL_KEYS", "")
    monkeypatch.setattr(settings, "LLM_CREDENTIAL_ACTIVE_KID", "")
    with pytest.raises(CredentialCipherError):
        CredentialCipher.from_settings()  # SECRET_KEY is set, yet no ring is derived from it
    monkeypatch.setattr(settings, "LLM_CREDENTIAL_KEYS", json.dumps({"k1": K1}))
    monkeypatch.setattr(settings, "LLM_CREDENTIAL_ACTIVE_KID", "k1")
    assert CredentialCipher.from_settings().encrypt(CRED).key_id == "k1"
