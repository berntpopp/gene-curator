"""Publish gate and upgrade impact as app_user through the API (#269, #270).

A refused publish inserts no version; the impact preview only lists curations the caller
can see under RLS.
"""

import json

import pytest
from fastapi.testclient import TestClient

from tests.postgres.test_methodology_versions import W, _h, _owner, client, w

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
