"""MCP study round 5 (T8): PMIDs cited in free text are checked against PubMed like pmid
fields; an unknown one warns with its path and never blocks the save."""

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from app.models.models import CurationNew
from tests.api.test_draft_ids_and_merge import (  # noqa: F401 (fixture)
    ROWS,
    _draft,
    _fake_fetch,
    online,
)


def test_unknown_pmid_in_free_text_warns_with_its_path(
    client: TestClient,
    admin_token: str,
    test_curation: CurationNew,
    online: MonkeyPatch,  # noqa: F811
) -> None:
    _fake_fetch(online, {"99999999": "Publication not found: 99999999"})
    row = {
        "points": 2,
        "pmid": "31000001",
        "explanation": "as in PMID: 99999999 and pubmed 31000002",
    }
    evidence = {
        "genetic_evidence": {"case_control": {"single_variant_analysis": [row]}},
        "evidence_summary": "see https://pubmed.ncbi.nlm.nih.gov/99999999/",
    }
    r = _draft(client, admin_token, test_curation, "curations", evidence_data=evidence)
    assert r.status_code == 200, r.text
    assert r.json()["warnings"] == [
        {
            "path": f"{ROWS}[0].explanation",
            "message": "PMID: 99999999 not found in PubMed",
        },
        {
            "path": "evidence_summary",
            "message": "pubmed.ncbi.nlm.nih.gov/99999999 not found in PubMed",
        },
    ]
    assert (
        r.json()["computed_scores"]["total_score"] == 2
    )  # the row's own PMID is known
