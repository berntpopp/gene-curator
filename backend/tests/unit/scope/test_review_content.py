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
from tests.api.scopes.factories import (
    make_curation,
    make_gene,
    make_precuration,
    make_scope,
)

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


@pytest.mark.parametrize(
    ("own", "allowed"),
    [
        ({}, True),
        ({"entity_definition": {"disease_name": "Own disease"}}, True),
        ({"disease_name": "Own flat disease"}, True),
        ({"entity_definition": {"disease_name": ""}}, False),
        ({"entity_definition": {"disease_name": None}}, False),
        ({"disease_name": ""}, False),
        ({"disease_name": None}, False),
        ({"entity_definition": None}, False),
        ({"entity_definition": "malformed"}, False),
    ],
)
def test_linked_disease_fills_only_absent_values_without_mutating_evidence(
    db_session: Session,
    scope: Scope,
    creator: UserNew,
    own: dict[str, Any],
    allowed: bool,
) -> None:
    item = _item(db_session, "curation", scope, creator)
    assert isinstance(item, CurationNew)
    precuration = make_precuration(
        db_session, scope=scope, gene=item.gene, creator=creator
    )
    disease = {
        "disease_name": "Linked disease",
        "mondo_id": "MONDO:0000001",
        "mode_of_inheritance": "AD",
    }
    precuration.evidence_data = disease
    item.precuration_id = precuration.id
    evidence = {"summary": "Actual curation evidence", **own}
    item.evidence_data = evidence
    pair = db_session.get(WorkflowPair, item.workflow_pair_id)
    assert pair
    schema = db_session.get(CurationSchema, pair.curation_schema_id)
    assert schema
    schema.field_definitions = {
        "entity_definition": {
            "type": "object",
            "readonly": True,
            "properties": {key: {"required": True} for key in disease},
        }
    }
    # Own disease wins over the linked value in condition evaluation, too.
    schema.validation_rules = {
        "conditional_required": {
            "own_note": {"when": {"entity_definition.disease_name": "Linked disease"}}
        }
    }
    if not own:
        evidence["own_note"] = "present"
    db_session.commit()
    if allowed:
        check_review_content(db_session, item)
    else:
        with pytest.raises(MissingRequiredFieldsError):
            check_review_content(db_session, item)
    assert item.evidence_data == evidence
    assert precuration.evidence_data == disease
    assert not db_session.is_modified(item)


@pytest.mark.parametrize("mismatch", ["scope", "gene"])
def test_linked_disease_must_belong_to_the_same_gene_and_scope(
    db_session: Session, scope: Scope, creator: UserNew, mismatch: str
) -> None:
    item = _item(db_session, "curation", scope, creator)
    assert isinstance(item, CurationNew)
    precuration = make_precuration(
        db_session, scope=scope, gene=item.gene, creator=creator
    )
    precuration.evidence_data = {"disease_name": "Private disease"}
    if mismatch == "scope":
        precuration.scope_id = make_scope(db_session).id
    elif mismatch == "gene":
        precuration.gene_id = make_gene(db_session).id
    item.precuration_id = precuration.id
    pair = db_session.get(WorkflowPair, item.workflow_pair_id)
    assert pair
    schema = db_session.get(CurationSchema, pair.curation_schema_id)
    assert schema
    schema.field_definitions = {
        "entity_definition": {
            "type": "object",
            "properties": {"disease_name": {"required": True}},
        }
    }
    db_session.commit()
    with pytest.raises(
        MissingRequiredFieldsError, match=r"entity_definition\.disease_name"
    ):
        check_review_content(db_session, item)
