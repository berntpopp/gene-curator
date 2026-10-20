"""Shared helpers for the schema API test modules."""

from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.models import CurationSchema, WorkflowPair

# Seeded production format for workflow_states (see database/sql/004_seed_data.sql)
SEEDED_WORKFLOW_STATES = {
    "states": [
        {"name": "draft", "description": "Initial", "permissions": ["curator"]},
        {"name": "submitted", "description": "Submitted", "permissions": ["admin"]},
    ],
    "transitions": {"draft": ["submitted"], "submitted": []},
    "initial_state": "draft",
}


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def schema_payload(name: str = "Test Schema", version: str = "1.0", **overrides):
    payload = {
        "name": name,
        "version": version,
        "schema_type": "curation",
        "field_definitions": {"gene": {"type": "text", "label": "Gene"}},
        "workflow_states": SEEDED_WORKFLOW_STATES,
        "ui_configuration": {"sections": []},
    }
    payload.update(overrides)
    return payload


def insert_schema(
    db: Session,
    *,
    name: str = "Schema",
    version: str = "1.0",
    schema_type: str = "curation",
    created_by=None,
    is_active: bool = True,
    institution: str | None = None,
    workflow_states=None,
    scoring_configuration=None,
) -> CurationSchema:
    schema = CurationSchema(
        id=uuid4(),
        name=name,
        version=version,
        schema_type=schema_type,
        field_definitions={"gene": {"type": "text", "label": "Gene"}},
        validation_rules={},
        workflow_states=workflow_states or SEEDED_WORKFLOW_STATES,
        ui_configuration={"sections": []},
        scoring_configuration=scoring_configuration,
        is_active=is_active,
        institution=institution,
        created_by=created_by,
        schema_hash=uuid4().hex,
    )
    db.add(schema)
    db.commit()
    db.refresh(schema)
    return schema


def insert_pair(
    db: Session,
    precuration: CurationSchema,
    curation: CurationSchema,
    *,
    name: str = "pair",
    version: str = "1.0",
    created_by=None,
) -> WorkflowPair:
    pair = WorkflowPair(
        id=uuid4(),
        name=name,
        version=version,
        precuration_schema_id=precuration.id,
        curation_schema_id=curation.id,
        is_active=True,
        created_by=created_by,
    )
    db.add(pair)
    db.commit()
    db.refresh(pair)
    return pair
