"""Publish gate and upgrade impact as app_user through the API (#269, #270).

A refused publish inserts no version; the impact preview only lists curations the caller
can see under RLS.
"""

import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.security import get_password_hash
from tests.postgres.test_methodology_versions import W, _h, _owner, client, w
from tests.postgres.test_point_model_pinned import _create
from tests.unit.test_point_model import _custom_model

pytestmark = pytest.mark.postgres
__all__ = ["client", "w"]  # fixtures shared with the methodology version tests

COUNT = "SELECT count(*) FROM methodology_versions WHERE schema_id = %s"


def _set(w: W, column: str, value: object) -> None:
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            f"UPDATE curation_schemas SET {column} = %s WHERE id = %s",
            (json.dumps(value), w.schema),
        )


def _count(w: W) -> int:
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(COUNT, (w.schema,))
        return int(cur.fetchone()[0])


@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("workflow_states", {"review": {"reviewers_required": 9}}),
        (
            "scoring_configuration",
            {"engine": "clingen_sop_v11", "point_model": {"sections": [{"key": "g"}]}},
        ),
        (
            "scoring_configuration",
            {
                "engine": "clingen_sop_v11",
                "tests": [{"name": "t", "evidence_data": {}, "expect": {"total": 1}}],
            },
        ),
    ],
)
def test_refused_publish_inserts_no_version(
    client: TestClient, w: W, column: str, value: object
) -> None:
    _set(w, column, value)
    r = client.post(
        f"/api/v1/schemas/curation-schemas/{w.schema}/versions", headers=_h(w.admin)
    )
    assert r.status_code == 422, r.text
    assert _count(w) == 1  # only the auto-published v1


def test_impact_lists_only_visible_curations(client: TestClient, w: W) -> None:
    curation = _create(client, w, w.genes[0])  # v1 (ClinGen template): total 2
    _set(
        w,
        "scoring_configuration",
        {"engine": "clingen_sop_v11", "point_model": _custom_model()},
    )
    r = client.post(
        f"/api/v1/schemas/curation-schemas/{w.schema}/versions", headers=_h(w.admin)
    )
    assert r.status_code == 201, r.text
    url = (
        f"/api/v1/schemas/curation-schemas/{w.schema}/versions/{r.json()['id']}/impact"
    )

    seen = client.get(url, headers=_h(w.alice))
    assert seen.status_code == 200, seen.text
    assert [
        (i["curation_id"], i["old_total"], i["new_total"]) for i in seen.json()
    ] == [(curation["id"], 2.0, 1.5)]

    outsider = uuid4()
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO users (id, email, hashed_password, name, role) "
            "VALUES (%s, %s, %s, 'out', 'user')",
            (str(outsider), f"out-{outsider.hex[:8]}@mv.org", get_password_hash("pw")),
        )
    try:
        hidden = client.get(url, headers=_h(outsider))
        assert hidden.status_code == 200, hidden.text
        assert hidden.json() == []  # private scope: RLS hides the curation
    finally:
        with _owner() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM audit_log WHERE user_id = %s", (str(outsider),))
            cur.execute("DELETE FROM users WHERE id = %s", (str(outsider),))
