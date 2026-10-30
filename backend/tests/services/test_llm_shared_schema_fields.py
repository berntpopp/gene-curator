"""#534: a derived schema's field reaches the provider only when flagged llm_share."""

from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.models import CurationSchema
from app.models.methodology import MethodologyVersion
from app.services.llm_runs import curation_values
from tests.api.llm_api_support import llm_env  # noqa: F401
from tests.services.llm_run_support import World, world_fixture  # noqa: F401

pytestmark = [pytest.mark.unit, pytest.mark.usefixtures("llm_env")]

DERIVED = {
    "kidney_relevance": {"type": "text", "llm_share": True},
    "binning": {"type": "select"},  # not flagged: dropped
    "genetic_evidence": {
        "type": "object",
        "properties": {"lumped_mondo_terms": {"type": "text", "llm_share": True}},
    },
    "points": {"type": "number", "llm_share": True},  # judgement: never sent
}


def test_flagged_derived_fields_are_sent_and_the_rest_dropped(
    db_session: Session, world: World
) -> None:
    schema = CurationSchema(
        id=uuid4(),
        name=f"derived-{uuid4().hex[:6]}",
        version="1",
        schema_type="curation",
        field_definitions=DERIVED,
        workflow_states={},
        ui_configuration={},
        schema_hash=uuid4().hex * 2,
    )
    db_session.add(schema)
    db_session.flush()
    version = MethodologyVersion(
        schema_id=schema.id, version=1, snapshot={"field_definitions": DERIVED}
    )
    db_session.add(version)
    db_session.flush()
    world.curation.methodology_version_id = version.id
    world.curation.evidence_data = {
        "kidney_relevance": "renal-cysts",
        "binning": "syndromic-bin",
        "points": 99.5,
        "genetic_evidence": {
            "lumped_mondo_terms": "MONDO:0000001",
            "case_level": [{"description": "segregates"}],
        },
    }
    db_session.commit()
    sent = curation_values(db_session, world.curation)["curation_data"]
    for shared in ("renal-cysts", "MONDO:0000001", "segregates"):
        assert shared in sent
    for dropped in ("syndromic-bin", "binning", "99.5"):
        assert dropped not in sent
