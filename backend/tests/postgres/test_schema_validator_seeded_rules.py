"""#408: validate-evidence on the seeded precuration methodology, as app_user via the API."""

import os
from collections.abc import Generator
from typing import Any

import psycopg2
import pytest
from fastapi.testclient import TestClient

from app.core import database
from app.core.security import create_access_token
from app.main import app

pytestmark = pytest.mark.postgres

SCHEMA_ID = "e8f9a0b1-c2d3-4e5f-6a7b-8c9d0e1f2a3b"  # 016_seed_precuration_schema.sql
DATA = {
    "mondo_id": "MONDO:0000001",
    "disease_name": "Example disease",
    "mode_of_inheritance": "AD",
    "lumping_splitting_applicable": True,
    "lumping_splitting_decision": "LUMP",
    "lumping_splitting_rationale": "Same mechanism and phenotype spectrum",
    "affiliation": "Kidney Expert Panel",
}


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    database.engine.dispose()
    with TestClient(app) as c:
        yield c
    database.engine.dispose()


def test_seeded_precuration_rules_apply_without_warnings(client: TestClient) -> None:
    with (
        psycopg2.connect(os.environ["OWNER_DATABASE_URL"]) as conn,
        conn.cursor() as cur,
    ):
        cur.execute("SELECT id FROM users WHERE email = 'alice.smith@genecurator.org'")
        alice = str(cur.fetchone()[0])
    token = create_access_token(data={"sub": alice})

    def validate(data: dict[str, Any]) -> dict[str, Any]:
        response = client.post(
            "/api/v1/validation/validate-evidence",
            json={"evidence_data": data, "schema_id": SCHEMA_ID},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200, response.text
        body: dict[str, Any] = response.json()
        return body

    ok = validate(DATA)
    bad = validate({**DATA, "mondo_id": "MONDO:1", "lumping_splitting_rationale": ""})

    assert [w for w in ok["warnings"] if "Error applying" in w["message"]] == []
    assert ok["is_valid"] is True, ok["errors"]
    assert [e["field"] for e in bad["errors"]] == [
        "lumping_splitting_rationale",
        "mondo_id",
    ]
