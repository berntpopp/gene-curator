"""Publish gate, score trace and upgrade impact (#269, #270, #266).

Publishing (and creating, which publishes v1 on PostgreSQL) runs the static checks and the
version's tests; an invalid definition or failing test is refused and inserts no version.
"""

import hashlib
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import CurationNew, CurationSchema, Gene, Scope, UserNew, WorkflowPair
from app.models.methodology import MethodologyVersion
from tests.api.schema_api_support import auth, insert_schema, schema_payload
from tests.unit.test_point_model import CUSTOM_EVIDENCE, _custom_model

pytestmark = pytest.mark.unit

BASE = "/api/v1/schemas/curation-schemas"
STAGES = {
    "entry": {"allowed_transitions": ["precuration"]},
    "precuration": {"allowed_transitions": ["curation", "review"]},
    "curation": {"allowed_transitions": ["review"]},
    "review": {"allowed_transitions": ["active", "curation"], "reviewers_required": 1},
    "active": {"allowed_transitions": ["review"]},
}
CLINGEN = {"engine": "clingen_sop_v11"}


def _publish(client: TestClient, token: str, schema: CurationSchema) -> Any:
    return client.post(f"{BASE}/{schema.id}/versions", headers=auth(token))


def _versions(client: TestClient, token: str, schema: CurationSchema) -> list[Any]:
    listed = client.get(f"{BASE}/{schema.id}/versions", headers=auth(token)).json()
    assert isinstance(listed, list)
    return listed


@pytest.mark.parametrize(
    ("workflow_states", "scoring", "error"),
    [
        # monkey bug 6: only review left, reviewers out of range
        ({"review": {"reviewers_required": 9}}, CLINGEN, "reviewers_required"),
        ({"review": {"reviewers_required": 2}}, CLINGEN, "required stage: entry"),
        (
            STAGES,
            {**CLINGEN, "point_model": {"sections": [{"key": "g"}]}},
            "point_model",
        ),
    ],
)
def test_invalid_definition_is_refused_and_inserts_no_version(
    client: TestClient,
    db_session: Session,
    admin_token: str,
    workflow_states: dict[str, Any],
    scoring: dict[str, Any],
    error: str,
) -> None:
    schema = insert_schema(
        db_session, workflow_states=workflow_states, scoring_configuration=scoring
    )
    r = _publish(client, admin_token, schema)
    assert r.status_code == 422, r.text
    assert any(error in e for e in r.json()["detail"]["errors"]), r.text
    assert _versions(client, admin_token, schema) == []


def _tested(expect: dict[str, Any]) -> dict[str, Any]:
    test = {"name": "registry", "evidence_data": CUSTOM_EVIDENCE, "expect": expect}
    return {**CLINGEN, "tests": [test]}


def test_version_tests_gate_publish(
    client: TestClient, db_session: Session, admin_token: str
) -> None:
    passing = insert_schema(
        db_session,
        name="passing",
        workflow_states=STAGES,
        scoring_configuration=_tested({"total": 2, "class": "limited"}),
    )
    assert _publish(client, admin_token, passing).status_code == 201

    for i, scoring in enumerate(
        (
            _tested({"total": 3}),
            _tested({"class": "strong"}),
            _tested({"verdict": "limited"}),  # unknown key never passes silently
            {**CLINGEN, "tests": [{"name": "no evidence"}]},
            {**CLINGEN, "tests": {"not": "a list"}},
        )
    ):
        schema = insert_schema(
            db_session, name=f"failing-{i}", scoring_configuration=scoring
        )
        r = _publish(client, admin_token, schema)
        assert r.status_code == 422, r.text
        assert r.json()["detail"]["errors"][0].startswith("scoring_configuration.tests")
        assert _versions(client, admin_token, schema) == []


def test_failing_test_message_names_expected_and_actual(
    client: TestClient, db_session: Session, admin_token: str
) -> None:
    schema = insert_schema(db_session, scoring_configuration=_tested({"total": 3}))
    errors = _publish(client, admin_token, schema).json()["detail"]["errors"]
    assert errors == [
        "scoring_configuration.tests[0] (registry): expected total 3, got 2.0"
    ]


def test_create_runs_the_same_gate(client: TestClient, admin_token: str) -> None:
    # creating a schema publishes v1 on PostgreSQL (042 trigger)
    r = client.post(
        f"{BASE}",
        json=schema_payload(scoring_configuration=_tested({"class": "strong"})),
        headers=auth(admin_token),
    )
    assert r.status_code == 400, r.text
    assert "expected class 'strong', got 'limited'" in r.json()["detail"]


# ---------------------------------------------------------------------------
# upgrade impact
# ---------------------------------------------------------------------------


def _gene(db: Session) -> Gene:
    n = uuid4().int % 10**8
    gene = Gene(
        id=uuid4(),
        hgnc_id=f"HGNC:{n}",
        approved_symbol=f"G{n}",
        record_hash=hashlib.sha256(str(n).encode()).hexdigest(),
        previous_symbols=[],
        alias_symbols=[],
        details={},
    )
    db.add(gene)
    return gene


def test_impact_lists_older_pinned_curations_whose_result_changes(
    client: TestClient,
    db_session: Session,
    admin_token: str,
    test_scope: Scope,
    test_user_curator: UserNew,
) -> None:
    db = db_session
    schema = insert_schema(db, workflow_states=STAGES, scoring_configuration=CLINGEN)
    v1 = _publish(client, admin_token, schema).json()
    # published before the gate: its point model cannot score, the row is skipped
    broken = MethodologyVersion(
        id=uuid4(),
        schema_id=schema.id,
        version=2,
        snapshot={"scoring_configuration": {"point_model": {"sections": [{}]}}},
    )
    db.add(broken)
    schema.scoring_configuration = {**CLINGEN, "point_model": _custom_model()}
    db.commit()
    v2 = _publish(client, admin_token, schema).json()
    pair = WorkflowPair(
        id=uuid4(), name="impact", version="1", curation_schema_id=schema.id
    )
    db.add(pair)

    def curation(version: str, evidence: dict[str, Any], **kw: Any) -> CurationNew:
        row = CurationNew(
            id=uuid4(),
            scope_id=test_scope.id,
            gene_id=_gene(db).id,
            workflow_pair_id=pair.id,
            methodology_version_id=version,
            evidence_data=evidence,
            created_by=test_user_curator.id,
            **kw,
        )
        db.add(row)
        return row

    changed = curation(v1["id"], CUSTOM_EVIDENCE)  # 2 -> 1.5
    curation(v1["id"], {})  # 0 -> 0
    curation(v1["id"], CUSTOM_EVIDENCE, status="archived", workflow_stage="archived")
    curation(v2["id"], CUSTOM_EVIDENCE)  # already on the target version
    curation(str(broken.id), CUSTOM_EVIDENCE)
    db.commit()

    r = client.get(
        f"{BASE}/{schema.id}/versions/{v2['id']}/impact", headers=auth(admin_token)
    )
    assert r.status_code == 200, r.text
    assert r.json() == [
        {
            "curation_id": str(changed.id),
            "gene_id": str(changed.gene_id),
            "scope_id": str(test_scope.id),
            "from_version": 1,
            "old_total": 2.0,
            "old_class": "limited",
            "new_total": 1.5,
            "new_class": "limited",
        }
    ]
    # the older version itself has nothing older to re-score
    old = client.get(
        f"{BASE}/{schema.id}/versions/{v1['id']}/impact", headers=auth(admin_token)
    )
    assert old.json() == []
    other = insert_schema(db, name="other")
    missing = client.get(
        f"{BASE}/{other.id}/versions/{v2['id']}/impact", headers=auth(admin_token)
    )
    assert missing.status_code == 404
    assert db.query(MethodologyVersion).filter_by(schema_id=schema.id).count() == 3


def test_score_returns_trace_that_sums_to_the_total(
    client: TestClient,
    db_session: Session,
    admin_token: str,
    test_curation: CurationNew,
) -> None:
    test_curation.evidence_data = CUSTOM_EVIDENCE
    db_session.commit()
    r = client.get(
        f"/api/v1/curations/{test_curation.id}/score", headers=auth(admin_token)
    )
    assert r.status_code == 200, r.text
    body = r.json()
    trace = body["trace"]
    assert "trace" not in body["breakdown"]  # the trace is sent once
    assert trace["total"] == body["total_score"] == 2
    assert sum(s["score"] for s in trace["sections"]) == trace["raw_total"]
    for section in trace["sections"]:
        assert sum(c["score"] for c in section["categories"]) == section["raw"]


def test_validate_reports_missing_required_stages(
    client: TestClient, db_session: Session, admin_token: str
) -> None:
    schema = insert_schema(
        db_session, workflow_states={"review": {"reviewers_required": 2}}
    )
    r = client.post(f"{BASE}/{schema.id}/validate", headers=auth(admin_token))
    assert r.status_code == 200, r.text
    assert not r.json()["is_valid"]
    assert [e for e in r.json()["errors"] if "required stage" in e] == [
        "workflow_states: Missing required stage: entry",
        "workflow_states: Missing required stage: precuration",
    ]
