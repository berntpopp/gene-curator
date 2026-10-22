"""#433: every route into review checks the item's required fields (review_guards)."""

from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.crud.precuration_required import MissingRequiredFieldsError
from app.crud.workflow_engine import WorkflowEngine
from app.models.methodology import MethodologyVersion
from app.models.models import (
    CurationNew,
    CurationSchema,
    PrecurationNew,
    Scope,
    UserNew,
    WorkflowPair,
    WorkflowStage,
)
from app.services.review_guards import check_review_content
from tests.api.scopes.factories import make_curation, make_gene, make_precuration

pytestmark = pytest.mark.unit

S = WorkflowStage
FIELDS = {"kind": {}, "detail": {"required_when": {"kind": "other"}}}


def _schema(db: Session, kind: str, fields: dict[str, Any]) -> CurationSchema:
    schema = CurationSchema(
        id=uuid4(),
        name=f"rc-{uuid4().hex[:6]}",
        version="1.0",
        schema_type=kind,
        field_definitions=fields,
        validation_rules={},
        workflow_states={},
        ui_configuration={},
        schema_hash=uuid4().hex + uuid4().hex,
    )
    db.add(schema)
    db.commit()
    return schema


def _item(
    db: Session, item_type: str, scope: Scope, creator: UserNew
) -> CurationNew | PrecurationNew:
    """A curation (schema via its workflow pair) or precuration, unpinned, with FIELDS."""
    gene = make_gene(db)
    if item_type == "curation":
        curation = make_curation(
            db, scope=scope, gene=gene, creator=creator, stage=S.CURATION
        )
        pair = db.get(WorkflowPair, curation.workflow_pair_id)
        assert pair
        pair.curation_schema_id = _schema(db, "curation", FIELDS).id
        db.commit()
        return curation
    precuration = make_precuration(db, scope=scope, gene=gene, creator=creator)
    schema = db.get(CurationSchema, precuration.precuration_schema_id)
    assert schema
    schema.field_definitions = FIELDS
    db.commit()
    return precuration


@pytest.mark.parametrize(
    ("item_type", "current"), [("curation", S.CURATION), ("precuration", S.PRECURATION)]
)
def test_entering_review_needs_the_required_fields(
    db_session: Session,
    engine: WorkflowEngine,
    scope: Scope,
    creator: UserNew,
    item_type: str,
    current: S,
) -> None:
    item = _item(db_session, item_type, scope, creator)

    def errors(evidence: dict[str, Any]) -> list[str]:
        item.evidence_data = evidence
        db_session.commit()
        return engine.validate_transition(
            db_session, current, S.REVIEW, creator.id, item.id, item_type
        ).errors

    assert "Missing required fields: detail" in errors({"kind": "other"})
    assert errors({"kind": "AD"}) == []


def test_a_re_review_of_an_active_curation_requires_complete_content(
    db_session: Session, engine: WorkflowEngine, scope: Scope, creator: UserNew
) -> None:
    item = _item(db_session, "curation", scope, creator)
    item.evidence_data = {"kind": "other"}
    item.workflow_stage = S.ACTIVE
    db_session.commit()
    errors = engine.validate_transition(
        db_session, S.ACTIVE, S.REVIEW, creator.id, item.id, "curation"
    ).errors
    assert "Missing required fields: detail" in errors


def test_a_pinned_version_wins_over_the_live_schema(
    db_session: Session, scope: Scope, creator: UserNew
) -> None:
    item = _item(db_session, "precuration", scope, creator)
    version = MethodologyVersion(
        schema_id=item.precuration_schema_id,  # type: ignore[union-attr]
        version=1,
        snapshot={"field_definitions": {"pinned": {"required": True}}},
    )
    db_session.add(version)
    db_session.commit()
    item.methodology_version_id = version.id
    item.evidence_data = {"kind": "other"}  # the live schema would require detail
    db_session.commit()
    with pytest.raises(MissingRequiredFieldsError) as refused:
        check_review_content(db_session, item)
    assert refused.value.fields == ["pinned"]


def test_an_unreadable_pin_fails(db_session: Session) -> None:
    item = PrecurationNew(methodology_version_id=uuid4(), evidence_data={})
    with pytest.raises(ValueError, match="methodology version"):
        check_review_content(db_session, item)


@pytest.mark.parametrize(
    ("decision", "error"),
    [
        (None, "no decision"),
        ("UNDECIDED", "no decision"),
        ("MERGE", "Invalid lumping/splitting decision 'MERGE'"),
    ],
)
def test_lumping_splitting_needs_a_valid_decision(
    db_session: Session, decision: str | None, error: str
) -> None:
    evidence = {
        "lumping_splitting_applicable": True,
        "lumping_splitting_decision": decision,
    }
    with pytest.raises(ValueError, match=error):
        check_review_content(db_session, PrecurationNew(evidence_data=evidence))
    evidence["lumping_splitting_decision"] = "LUMP"
    check_review_content(db_session, PrecurationNew(evidence_data=evidence))
