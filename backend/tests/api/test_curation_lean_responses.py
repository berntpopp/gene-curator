"""MCP study round 2 finding 3: saves and submits answer concisely unless detail=true, and
GET leaves the score trace out unless detail=true (MCP study round 5)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import CurationNew
from app.schemas.curation import lean_scores

pytestmark = pytest.mark.unit

_TRACE = {
    "total_score": 2,
    "trace": {
        "total": 2,
        "sections": [
            {
                "key": "genetic",
                "score": 2,
                "categories": [
                    {
                        "key": "cases",
                        "score": 2,
                        "raw": 2,
                        "types": [
                            {"path": "a", "items": 1, "score": 2},
                            {"path": "b", "items": 0, "score": 0},
                        ],
                    },
                    {"key": "empty", "score": 0, "raw": 0, "types": [{"path": "c"}]},
                ],
            }
        ],
    },
}


def test_lean_scores_drops_zero_rows_only() -> None:
    (section,) = lean_scores(_TRACE)["trace"]["sections"]
    assert [c["key"] for c in section["categories"]] == ["cases"]
    assert [t["path"] for t in section["categories"][0]["types"]] == ["a"]
    assert lean_scores({"total_score": 0}) == {"total_score": 0}


def test_draft_save_is_concise_and_get_is_lean_by_default(
    client: TestClient,
    db_session: Session,
    admin_token: str,
    test_curation: CurationNew,
) -> None:
    headers = {"Authorization": f"Bearer {admin_token}"}
    url = f"/api/v1/curations/{test_curation.id}"
    saved = client.patch(
        f"{url}/draft",
        json={"evidence_data": {"x": 1}, "lock_version": test_curation.lock_version},
        headers=headers,
    )
    assert saved.status_code == 200, saved.text
    assert set(saved.json()) == {
        "id",
        "status",
        "workflow_stage",
        "lock_version",
        "total_score",
        "verdict",
        "warnings",
    }

    test_curation.computed_scores = _TRACE
    db_session.commit()
    lean = client.get(url, headers=headers).json()["computed_scores"]
    full = client.get(f"{url}?detail=true", headers=headers).json()["computed_scores"]
    assert lean == {"total_score": 2}  # no trace unless asked for
    assert full == _TRACE


def test_repeated_row_warnings_collapse_to_a_count() -> None:
    from app.schemas.curation import EvidenceWarning, collapse, collapse_warnings

    rows = [f"genetic.cases[{i}]: no variant" for i in range(5)]
    assert collapse([*rows, "genetic.cases[9]: other", "Free text warning"]) == [
        "no variant (5 rows: genetic.cases[0], genetic.cases[1], genetic.cases[2], ...)",
        "genetic.cases[9]: other",
        "Free text warning",
    ]
    ws = [EvidenceWarning(path=f"r[{i}].pmid", message="bad") for i in range(2)]
    assert [(w.path, w.message) for w in collapse_warnings(ws)] == [
        ("2 rows: r[0].pmid, r[1].pmid", "bad")
    ]
    one = [EvidenceWarning(path="r[0].pmid", message="bad")]
    assert collapse_warnings(one)[0].path == "r[0].pmid"


def test_get_curation_through_mcp_carries_the_evidence_once(
    client: TestClient,
    db_session: Session,
    test_user_curator,
    test_curation: CurationNew,
    approved_precuration,
) -> None:
    """MCP study round 6, T5a: "the evidence payload twice". One read returns it once,
    with the precuration linked and the score trace left out by default."""
    import json

    from tests.api.test_mcp import call, pat

    test_curation.precuration_id = approved_precuration.id
    test_curation.evidence_data = {
        "genetic_evidence": {"rows": [{"label": "ONCE-ONLY"}]}
    }
    test_curation.computed_scores = {**_TRACE, "warnings": []}
    db_session.commit()
    result = call(
        client,
        pat(db_session, test_user_curator),
        "get_curation",
        "/mcp",
        curation_id=str(test_curation.id),
        fields=["evidence_data", "computed_scores"],  # /mcp omits evidence by default
    )
    (block,) = result["content"]
    assert json.dumps(result).count("ONCE-ONLY") == 1
    assert "trace" not in json.loads(block["text"])["computed_scores"]
