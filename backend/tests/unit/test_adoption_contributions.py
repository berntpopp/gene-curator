"""Review #602 item 3: adoption contributions come from the shared VA-Spec builder and
the export output stays exactly as before."""

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.services.clingen_adoption import adoption_statement

pytestmark = pytest.mark.unit

RECORD = {
    "cggv_id": "CGGV:assertion_x",
    "classification": "definitive",
    "moi": "AR",
    "mondo": "MONDO:1",
    "citation": "c",
    "permalink": "https://search.clinicalgenome.org/x",
    "expert_panel": "Kidney GCEP",
    "classified_date": "2024-05-01",
    "retrieved_at": "2026-10-01T00:00:00Z",
    "record_sha256": "0" * 64,
}


def _coding(name: str, code: str) -> dict:
    return {"name": name, "primaryCoding": {"system": "SEPIO", "code": code}}


def test_adoption_contributions_are_unchanged() -> None:
    curation = SimpleNamespace(
        clingen_adoption=RECORD,
        created_at=datetime(2026, 10, 2, 9, tzinfo=UTC),
        approved_by="someone",
        approved_at=datetime(2026, 10, 3, 9, tzinfo=UTC),
    )
    statement = adoption_statement(curation, "Alice", "Bob")  # type: ignore[arg-type]
    assert statement is not None
    assert statement["contributions"] == [
        {
            "contributor": {"name": "Kidney GCEP", "agentType": "organization"},
            "activityType": _coding("interpreter", "SEPIO:0000331"),
            "date": "2024-05-01",
        },
        {
            "contributor": {"name": "Alice", "agentType": "person"},
            "activityType": _coding("curator", "SEPIO:0000156"),
            "date": "2026-10-02T09:00:00+00:00",
        },
        {
            "contributor": {"name": "Bob", "agentType": "person"},
            "activityType": _coding("approver", "SEPIO:0000155"),
            "date": "2026-10-03T09:00:00+00:00",
        },
    ]
