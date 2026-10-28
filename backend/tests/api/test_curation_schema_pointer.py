"""Curation responses name their field contract (round 5: T2b-1 guessed a schema id)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import CurationNew, CurationSchema, UserNew
from app.schemas.curation import Curation
from tests.api.test_mcp import call, pat

pytestmark = pytest.mark.unit


def test_curation_responses_carry_the_curation_schema_id(
    client: TestClient,
    db_session: Session,
    test_user_curator: UserNew,
    test_curation: CurationNew,
    evidence_schema: CurationSchema,
) -> None:
    db_session.refresh(test_curation)
    assert (
        Curation.model_validate(test_curation).curation_schema_id == evidence_schema.id
    )
    # The id leads straight to the schema read; an unknown one says where ids are
    token = pat(db_session, test_user_curator)
    read = call(
        client, token, "get_curation_schema", path="/mcp",
        schema_id=str(evidence_schema.id),
    )  # fmt: skip
    assert not read.get("isError"), read
    missing = call(
        client, token, "get_curation_schema", path="/mcp",
        schema_id="00000000-0000-0000-0000-000000000000",
    )  # fmt: skip
    assert "curation_schema_id on get_curation" in missing["content"][0]["text"]
