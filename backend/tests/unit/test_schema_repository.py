"""Tests for the schema and workflow-pair repositories (app/crud/schema_repository.py).

Exercises lookup, filtering and ordering, owner stamping, the in-use guards that
protect deletion, usage statistics and the schema checksum. Runs on the in-memory
SQLite session from conftest.
"""

import re
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.crud.schema_repository import (
    _schema_content_hash,
    schema_crud,
    workflow_pair_crud,
)
from app.models.models import (
    CurationNew,
    CurationSchema,
    Gene,
    PrecurationNew,
    Scope,
    UserNew,
    WorkflowPair,
)
from app.schemas.schema_repository import CurationSchemaCreate, WorkflowPairCreate

pytestmark = pytest.mark.unit

GOOD_STATES = {"states": [{"name": "draft"}, {"name": "submitted"}]}


def _schema(
    db: Session,
    name: str = "S",
    version: str = "1.0",
    schema_type: str = "curation",
    **extra,
) -> CurationSchema:
    schema = CurationSchema(
        id=uuid4(),
        name=name,
        version=version,
        schema_type=schema_type,
        field_definitions={"f": {"type": "text"}},
        validation_rules={},
        workflow_states=GOOD_STATES,
        ui_configuration={"sections": []},
        schema_hash=uuid4().hex,
        **extra,
    )
    db.add(schema)
    db.commit()
    db.refresh(schema)
    return schema


def _pair(
    db: Session,
    precuration: CurationSchema,
    curation: CurationSchema,
    name: str = "pair",
    version: str = "1.0",
) -> WorkflowPair:
    pair = WorkflowPair(
        id=uuid4(),
        name=name,
        version=version,
        precuration_schema_id=precuration.id,
        curation_schema_id=curation.id,
        is_active=True,
    )
    db.add(pair)
    db.commit()
    db.refresh(pair)
    return pair


def _curation(
    db: Session,
    scope: Scope,
    gene: Gene,
    user: UserNew,
    pair: WorkflowPair,
) -> CurationNew:
    curation = CurationNew(
        id=uuid4(),
        scope_id=scope.id,
        gene_id=gene.id,
        workflow_pair_id=pair.id,
        workflow_stage="curation",
        evidence_data={},
        created_by=user.id,
    )
    db.add(curation)
    db.commit()
    db.refresh(curation)
    return curation


def _precuration(
    db: Session,
    scope: Scope,
    gene: Gene,
    user: UserNew,
    schema: CurationSchema,
) -> PrecurationNew:
    precuration = PrecurationNew(
        id=uuid4(),
        scope_id=scope.id,
        gene_id=gene.id,
        precuration_schema_id=schema.id,
        workflow_stage="precuration",
        evidence_data={},
        created_by=user.id,
        updated_by=user.id,
    )
    db.add(precuration)
    db.commit()
    db.refresh(precuration)
    return precuration


# =============================================================================
# Curation schemas
# =============================================================================


class TestCurationSchemaLookup:
    def test_get_by_name_and_version(self, db_session: Session):
        target = _schema(db_session, name="Lookup", version="2.1")
        _schema(db_session, name="Lookup", version="2.2")

        found = schema_crud.get_by_name_and_version(
            db_session, name="Lookup", version="2.1"
        )
        missing = schema_crud.get_by_name_and_version(
            db_session, name="Lookup", version="9.9"
        )

        assert found is not None and found.id == target.id
        assert missing is None

    def test_get_multi_orders_by_name_then_version_desc(self, db_session: Session):
        _schema(db_session, name="Beta", version="1.0")
        _schema(db_session, name="Alpha", version="1.0")
        _schema(db_session, name="Alpha", version="2.0")

        rows = schema_crud.get_multi(db_session)

        assert [(r.name, r.version) for r in rows] == [
            ("Alpha", "2.0"),
            ("Alpha", "1.0"),
            ("Beta", "1.0"),
        ]

    def test_get_multi_filters_and_active_only(self, db_session: Session):
        _schema(db_session, name="A", schema_type="precuration", institution="I1")
        _schema(db_session, name="B", schema_type="curation", institution="I1")
        _schema(db_session, name="C", schema_type="curation", institution="I2")
        _schema(db_session, name="D", schema_type="curation", is_active=False)

        by_type = schema_crud.get_multi(db_session, schema_type="curation")
        by_inst = schema_crud.get_multi(db_session, institution="I1")
        all_rows = schema_crud.get_multi(db_session, active_only=False)

        assert {r.name for r in by_type} == {"B", "C"}
        assert {r.name for r in by_inst} == {"A", "B"}
        assert "D" in {r.name for r in all_rows}
        assert "D" not in {r.name for r in schema_crud.get_multi(db_session)}

    def test_get_multi_pagination(self, db_session: Session):
        for i in range(4):
            _schema(db_session, name=f"P{i}")

        page = schema_crud.get_multi(db_session, skip=1, limit=2)

        assert [r.name for r in page] == ["P1", "P2"]


class TestCurationSchemaCreate:
    def test_create_stamps_owner_and_hash(self, db_session: Session, test_user_admin):
        payload = CurationSchemaCreate(
            name="Created",
            version="1.0",
            schema_type="curation",
            field_definitions={"f": {"type": "text"}},
            workflow_states=GOOD_STATES,
            ui_configuration={"sections": []},
        )

        created = schema_crud.create_with_owner(
            db_session, obj_in=payload, owner_id=test_user_admin.id
        )

        assert created.created_by == test_user_admin.id
        assert re.fullmatch(r"[0-9a-f]{64}", created.schema_hash)

    def test_client_supplied_hash_is_kept(self, db_session: Session, test_user_admin):
        payload = CurationSchemaCreate(
            name="Hashed",
            version="1.0",
            schema_type="curation",
            field_definitions={},
            workflow_states=GOOD_STATES,
            ui_configuration={},
            schema_hash="a" * 64,
        )

        created = schema_crud.create_with_owner(
            db_session, obj_in=payload, owner_id=test_user_admin.id
        )

        assert created.schema_hash == "a" * 64

    def test_content_hash_is_deterministic_and_content_sensitive(self):
        base = {
            "name": "N",
            "version": "1",
            "field_definitions": {"a": 1},
            "workflow_states": GOOD_STATES,
        }
        changed = {**base, "field_definitions": {"a": 2}}

        assert _schema_content_hash(base) == _schema_content_hash(dict(base))
        assert _schema_content_hash(base) != _schema_content_hash(changed)

    def test_hash_ignores_unrelated_keys(self):
        base = {"name": "N", "version": "1", "description": "one"}

        assert _schema_content_hash(base) == _schema_content_hash(
            {**base, "description": "two"}
        )


class TestCurationSchemaInUse:
    def test_unused_schema_not_in_use(self, db_session: Session):
        schema = _schema(db_session, name="Idle")

        assert schema_crud.is_schema_in_use(db_session, schema_id=schema.id) is False

    def test_in_use_by_workflow_pair_either_side(self, db_session: Session):
        precur = _schema(db_session, name="P", schema_type="precuration")
        cur = _schema(db_session, name="C")
        _pair(db_session, precur, cur)

        assert schema_crud.is_schema_in_use(db_session, schema_id=precur.id)
        assert schema_crud.is_schema_in_use(db_session, schema_id=cur.id)

    def test_in_use_by_precuration(
        self,
        db_session: Session,
        test_scope: Scope,
        test_gene: Gene,
        test_user_curator: UserNew,
    ):
        schema = _schema(db_session, name="Direct", schema_type="precuration")
        _precuration(db_session, test_scope, test_gene, test_user_curator, schema)

        assert schema_crud.is_schema_in_use(db_session, schema_id=schema.id)

    def test_in_use_by_curation_through_pair(
        self,
        db_session: Session,
        test_scope: Scope,
        test_gene: Gene,
        test_user_curator: UserNew,
    ):
        precur = _schema(db_session, name="P2", schema_type="precuration")
        cur = _schema(db_session, name="C2")
        pair = _pair(db_session, precur, cur, name="via-curation")
        _curation(db_session, test_scope, test_gene, test_user_curator, pair)

        assert schema_crud.is_schema_in_use(db_session, schema_id=cur.id)


class TestCurationSchemaStructure:
    def test_valid_structure_result(self):
        result = schema_crud.validate_schema_structure(
            {
                "field_definitions": {
                    "a": {"type": "text", "label": "A"},
                    "b": {"type": "number", "label": "B"},
                },
                "workflow_states": GOOD_STATES,
                "ui_configuration": {"sections": []},
                "scoring_configuration": {"engine": "clingen_sop_v11"},
                "validation_rules": {"r": {}},
            }
        )

        assert result.is_valid is True
        assert result.errors == []
        assert result.field_count == 2
        assert result.has_scoring is True
        assert result.has_validation is True

    def test_missing_keys_reported(self):
        result = schema_crud.validate_schema_structure({"field_definitions": {}})

        assert result.is_valid is False
        assert result.has_scoring is False
        assert result.has_validation is False
        assert any("workflow_states" in e for e in result.errors)
        assert any("ui_configuration" in e for e in result.errors)


# =============================================================================
# Workflow pairs
# =============================================================================


class TestWorkflowPairRepository:
    def test_lookup_and_listing(self, db_session: Session):
        precur = _schema(db_session, name="WP-P", schema_type="precuration")
        cur = _schema(db_session, name="WP-C")
        active = _pair(db_session, precur, cur, name="wp", version="1.0")
        inactive = _pair(db_session, precur, cur, name="wp", version="2.0")
        inactive.is_active = False
        db_session.commit()

        assert (
            workflow_pair_crud.get_by_name_and_version(
                db_session, name="wp", version="1.0"
            ).id
            == active.id
        )
        listed = workflow_pair_crud.get_multi(db_session)
        assert [p.id for p in listed] == [active.id]
        everything = workflow_pair_crud.get_multi(db_session, active_only=False)
        assert {p.version for p in everything} == {"1.0", "2.0"}

    def test_create_stamps_owner(self, db_session: Session, test_user_admin):
        precur = _schema(db_session, name="CP", schema_type="precuration")
        cur = _schema(db_session, name="CC")
        payload = WorkflowPairCreate(
            name="created",
            version="1.0",
            precuration_schema_id=precur.id,
            curation_schema_id=cur.id,
        )

        pair = workflow_pair_crud.create_with_owner(
            db_session, obj_in=payload, owner_id=test_user_admin.id
        )

        assert pair.created_by == test_user_admin.id

    def test_in_use_by_scope_default(self, db_session: Session, test_scope: Scope):
        precur = _schema(db_session, name="SD-P", schema_type="precuration")
        cur = _schema(db_session, name="SD-C")
        pair = _pair(db_session, precur, cur, name="scoped")
        test_scope.default_workflow_pair_id = pair.id
        db_session.commit()

        assert workflow_pair_crud.is_workflow_pair_in_use(
            db_session, workflow_pair_id=pair.id
        )

    def test_in_use_by_precuration_of_same_schema(
        self,
        db_session: Session,
        test_scope: Scope,
        test_gene: Gene,
        test_user_curator: UserNew,
    ):
        precur = _schema(db_session, name="PP", schema_type="precuration")
        cur = _schema(db_session, name="PC")
        pair = _pair(db_session, precur, cur, name="precur-used")
        _precuration(db_session, test_scope, test_gene, test_user_curator, precur)

        assert workflow_pair_crud.is_workflow_pair_in_use(
            db_session, workflow_pair_id=pair.id
        )

    def test_unused_pair_and_unknown_id(self, db_session: Session):
        precur = _schema(db_session, name="UP", schema_type="precuration")
        cur = _schema(db_session, name="UC")
        pair = _pair(db_session, precur, cur, name="idle")

        assert not workflow_pair_crud.is_workflow_pair_in_use(
            db_session, workflow_pair_id=pair.id
        )
        assert not workflow_pair_crud.is_workflow_pair_in_use(
            db_session, workflow_pair_id=uuid4()
        )

    def test_scope_lookup_returns_active_pairs(self, db_session: Session, test_scope):
        precur = _schema(db_session, name="SC-P", schema_type="precuration")
        cur = _schema(db_session, name="SC-C")
        pair = _pair(db_session, precur, cur, name="for-scope")

        pairs = workflow_pair_crud.get_workflow_pairs_for_scope(
            db_session, scope_id=test_scope.id
        )

        assert [p.id for p in pairs] == [pair.id]

    def test_usage_statistics(
        self,
        db_session: Session,
        test_scope: Scope,
        test_gene: Gene,
        test_user_curator: UserNew,
    ):
        precur = _schema(db_session, name="US-P", schema_type="precuration")
        cur = _schema(db_session, name="US-C")
        pair = _pair(db_session, precur, cur, name="stats")
        test_scope.default_workflow_pair_id = pair.id
        _precuration(db_session, test_scope, test_gene, test_user_curator, precur)
        _curation(db_session, test_scope, test_gene, test_user_curator, pair)
        db_session.commit()

        stats = workflow_pair_crud.get_usage_statistics(
            db_session, workflow_pair_id=pair.id
        )

        assert stats["scopes_using_as_default"] == 1
        assert stats["active_precurations"] == 1
        assert stats["active_curations"] == 1
        assert stats["total_usage"] == 3

    def test_usage_statistics_for_unknown_pair_is_empty(self, db_session: Session):
        assert (
            workflow_pair_crud.get_usage_statistics(
                db_session, workflow_pair_id=uuid4()
            )
            == {}
        )
