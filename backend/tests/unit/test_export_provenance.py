"""Delta review of #602: contribution dates in the export's own format (Z), assessors
only for visible reviews, latest software write chosen by datetime."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.schemas.provenance import Agent, EvidenceLine, contribution
from app.services.export_provenance import curation_contributions

pytestmark = pytest.mark.unit

SNAPSHOT = Path(__file__).parents[3] / "docs/examples/export-page.schema.json"
T = datetime(2026, 10, 2, 9, tzinfo=UTC)
AI = Agent(name="m", agentType="software")


def test_dates_serialize_like_the_other_export_timestamps() -> None:
    c = contribution("curator", Agent(name="A", agentType="person"), T)
    assert c.model_dump(mode="json")["date"] == "2026-10-02T09:00:00Z"
    date = json.loads(SNAPSHOT.read_text())["$defs"]["Contribution"]["properties"][
        "date"
    ]
    assert {"format": "date-time", "type": "string"} in date["anyOf"]


@pytest.mark.parametrize(
    ("given", "shown"),
    [
        ("2026-10-02", "2026-10-02T00:00:00Z"),  # bare date: midnight UTC
        ("2026-10-02T11:00:00+02:00", "2026-10-02T09:00:00Z"),  # offset: to UTC
    ],
)
def test_every_date_is_utc_with_z(given: str, shown: str) -> None:
    """#602 review: docs/EXPORT.md promises UTC with Z for every input."""
    c = contribution("curator", Agent(name="A", agentType="person"), given)
    assert c.model_dump(mode="json")["date"] == shown


def test_no_assessor_without_a_visible_review() -> None:
    roles = [c.activityType.name for c in curation_contributions("A", T, "B", T, [])]
    assert roles == ["curator", "approver"]
    with_review = curation_contributions("A", T, "B", T, [], [("R", T, False)])
    assert [c.activityType.name for c in with_review] == [
        "curator",
        "assessor",
        "approver",
    ]


def test_the_latest_software_write_wins_whatever_the_input_type() -> None:
    older = contribution("curator", AI, "2026-10-03T09:00:00+00:00")
    newer = contribution("curator", AI, datetime(2026, 10, 3, 10, tzinfo=UTC))
    lines = [EvidenceLine(path="r[0]", contributions=[older, newer])]
    [_, software] = curation_contributions("A", T, None, None, lines)
    assert software.date == datetime(2026, 10, 3, 10, tzinfo=UTC)


def test_a_prefixed_pmid_source_exports_bare_digits() -> None:
    """MUI-15: "PMID:20414234" is accepted and exported as 20414234."""
    from app.services.export_provenance import _source

    out = _source({"kind": "pmid", "id": "PMID:20414234"})
    assert (out.id, out.pmid) == ("20414234", "20414234")
