"""`make rotate-llm-keys`: re-encrypt every stored credential under the active kid.

Runs as the database owner (OWNER_DATABASE_URL): the API role cannot read ciphertexts.
Keep the old kid in LLM_CREDENTIAL_KEYS until this has run, then remove it.
"""

import os

from sqlalchemy import create_engine, func, select, update
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.llm.crypto import CredentialCipher
from app.models.llm import LLMCredential

logger = get_logger(__name__)


def rotate_all(db: Session, cipher: CredentialCipher, active_kid: str) -> int:
    """Re-encrypt credentials not yet on `active_kid`; returns how many changed."""
    rows = db.execute(
        select(LLMCredential.id, LLMCredential.ciphertext).where(
            LLMCredential.key_id != active_kid
        )
    ).all()
    for credential_id, ciphertext in rows:
        rotated = cipher.rotate(bytes(ciphertext))
        db.execute(
            update(LLMCredential)
            .where(LLMCredential.id == credential_id)
            .values(
                ciphertext=rotated.ciphertext,
                key_id=rotated.key_id,
                rotated_at=func.now(),
            )
        )
    db.commit()
    return len(rows)


def main() -> None:  # pragma: no cover - thin CLI wrapper around rotate_all
    from app.core.config import settings

    engine = create_engine(os.environ["OWNER_DATABASE_URL"])
    with Session(engine) as db:
        count = rotate_all(
            db, CredentialCipher.from_settings(), settings.LLM_CREDENTIAL_ACTIVE_KID
        )
    logger.info("LLM credentials rotated", count=count)


if __name__ == "__main__":  # pragma: no cover
    main()
