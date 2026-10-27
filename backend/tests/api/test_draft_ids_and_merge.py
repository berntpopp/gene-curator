"""Drafts warn on bad IDs and never block; submit refuses them; saves can merge-patch."""

from typing import Any

import pytest
from fastapi.testclient import TestClient
from pytest import MonkeyPatch
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.curation import merge_patch
from app.models import CurationNew, PrecurationNew
from app.models.models import Publication
from app.schemas.validation import PMIDValidationResult, PublicationData
from app.services import (
    evidence_ids,
    ontology_service,
    publication_service,
    review_entry,
)
from app.services.ontology_service import OntologyService
from app.services.publication_service import PublicationService
from tests.api.test_submit_unknown_pmids import _fake_fetch

ROWS = "genetic_evidence.case_control.single_variant_analysis"


def _evidence(pmid: str) -> dict[str, Any]:
    return {
        "status": "in_progress",
        "genetic_evidence": {
            "case_control": {"single_variant_analysis": [{"points": 2, "pmid": pmid}]}
        },
    }


def _h(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _draft(client: TestClient, token: str, item: Any, kind: str, **body: Any) -> Any:
    body.setdefault("lock_version", item.lock_version)
    url = f"/api/v1/{kind}/{item.id}/draft?detail=true"  # full result, dict warnings
    return client.patch(url, json=body, headers=_h(token))


def _terms(monkeypatch: MonkeyPatch, outcome: dict[str, bool | None]) -> None:
    """Real lookup chain; term_found answers from ``outcome`` (missing = found)."""

    async def found(self: OntologyService, curie: str) -> bool | None:
        return outcome.get(curie, True)

    monkeypatch.setattr(evidence_ids, "lookup_terms", ontology_service.lookup_terms)
    monkeypatch.setattr(review_entry, "lookup_terms", ontology_service.lookup_terms)
    monkeypatch.setattr(ontology_service, "_known_terms", set())
    monkeypatch.setattr(OntologyService, "term_found", found)


@pytest.fixture
def online(monkeypatch: MonkeyPatch) -> MonkeyPatch:
    monkeypatch.setattr(evidence_ids, "lookup_pmids", publication_service.lookup_pmids)
    _terms(monkeypatch, {})
    return monkeypatch


def test_merge_patch_follows_rfc_7396() -> None:
    target = {"a": {"b": 1, "c": 2}, "d": [1, 2], "e": 1}
    patch = {"a": {"b": None, "x": 3}, "d": [3], "e": {"f": 1}}
    assert merge_patch(target, patch) == {
        "a": {"c": 2, "x": 3},
        "d": [3],
        "e": {"f": 1},
    }
    assert merge_patch(target, [1]) == [1] and target["a"] == {"b": 1, "c": 2}


def test_one_field_patch_leaves_the_rest_and_a_stale_patch_409s(
    client: TestClient,
    admin_token: str,
    db_session: Session,
    test_curation: CurationNew,
) -> None:
    test_curation.evidence_data = {"status": "in_progress", "notes": {"a": 1, "b": 2}}
    db_session.commit()
    version = test_curation.lock_version

    r = _draft(
        client,
        admin_token,
        test_curation,
        "curations",
        evidence_data={"notes": {"a": None, "c": 3}},
        merge=True,
    )
    assert r.status_code == 200, r.text
    assert r.json()["evidence_data"] == {
        "status": "in_progress",
        "notes": {"b": 2, "c": 3},
    }
    assert r.json()["warnings"] == []

    stale = _draft(
        client,
        admin_token,
        test_curation,
        "curations",
        evidence_data={"status": "x"},
        merge=True,
        lock_version=version,
    )
    assert stale.status_code == 409, stale.text
    db_session.refresh(test_curation)
    assert test_curation.evidence_data["status"] == "in_progress"

    r = client.put(
        f"/api/v1/curations/{test_curation.id}?detail=true",
        headers=_h(admin_token),
        json={
            "evidence_data": {"notes": None},
            "merge": True,
            "lock_version": test_curation.lock_version,
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["evidence_data"] == {"status": "in_progress"}


def test_unknown_pmid_warns_and_scores_zero(
    client: TestClient,
    admin_token: str,
    test_curation: CurationNew,
    online: MonkeyPatch,
) -> None:
    _fake_fetch(online, {"99999999": "Publication not found: 99999999"})
    r = _draft(
        client,
        admin_token,
        test_curation,
        "curations",
        evidence_data=_evidence("99999999"),
    )
    assert r.status_code == 200, r.text
    assert r.json()["warnings"] == [
        {"path": f"{ROWS}[0].pmid", "message": "99999999 not found in PubMed"}
    ]
    assert r.json()["computed_scores"]["total_score"] == 0

    score = client.get(
        f"/api/v1/curations/{test_curation.id}/score", headers=_h(admin_token)
    )
    assert score.status_code == 200, score.text
    assert score.json()["total_score"] == 0
    assert score.json()["breakdown"]["excluded"] == [
        {
            "path": f"{ROWS}[0]",
            "pmid": "99999999",
            "reason": "PMID 99999999 not found in PubMed",
        }
    ]


def test_known_or_unverified_pmid_scores(
    client: TestClient,
    admin_token: str,
    test_curation: CurationNew,
    online: MonkeyPatch,
) -> None:
    _fake_fetch(online, {"31000001": "API timeout; retry lookup"})
    r = _draft(
        client,
        admin_token,
        test_curation,
        "curations",
        evidence_data=_evidence("31000001"),
    )
    assert r.status_code == 200, r.text
    assert "unverified" in r.json()["warnings"][0]["message"]
    assert r.json()["computed_scores"]["total_score"] == 2


def test_malformed_ids_warn_on_draft_and_refuse_submit(
    client: TestClient,
    admin_token: str,
    db_session: Session,
    test_curation: CurationNew,
    online: MonkeyPatch,
) -> None:
    evidence = {**_evidence("PMID12x"), "entity_definition": {"mondo_id": "MONDO:12"}}
    r = _draft(client, admin_token, test_curation, "curations", evidence_data=evidence)
    assert r.status_code == 200, r.text
    assert {w["path"] for w in r.json()["warnings"]} == {
        f"{ROWS}[0].pmid",
        "entity_definition.mondo_id",
    }
    assert r.json()["computed_scores"]["total_score"] == 0

    db_session.refresh(test_curation)
    submit = client.post(
        f"/api/v1/curations/{test_curation.id}/submit",
        json={"lock_version": test_curation.lock_version},
        headers=_h(admin_token),
    )
    assert submit.status_code == 422, submit.text
    errors = submit.json()["detail"]["errors"]
    assert {
        "path": f"{ROWS}[0].pmid",
        "message": "Expected 1-9 digits, e.g. 31558469",
    } in errors
    assert any(e["path"] == "entity_definition.mondo_id" for e in errors)
    db_session.refresh(test_curation)
    assert test_curation.workflow_stage == "curation"


def test_unknown_ontology_ids_warn_and_refuse_curation_submit(
    client: TestClient,
    admin_token: str,
    db_session: Session,
    test_curation: CurationNew,
    online: MonkeyPatch,
) -> None:
    _terms(online, {"MONDO:9999999": False, "OMIM:999999": None})
    evidence = {
        "status": "in_progress",
        "entity_definition": {"mondo_id": "MONDO:9999999", "omim_id": "MIM:999999"},
        "phenotypes": {"hpo_id": ["HP:0001250"]},
    }
    r = _draft(client, admin_token, test_curation, "curations", evidence_data=evidence)
    assert r.status_code == 200, r.text
    assert r.json()["warnings"] == [
        {
            "path": "entity_definition.mondo_id",
            "message": "MONDO:9999999 not found in MONDO",
        },
        {
            "path": "entity_definition.omim_id",
            "message": "MIM:999999 unverified: OMIM lookup unavailable, retry later",
        },
    ]
    db_session.refresh(test_curation)
    submit = client.post(
        f"/api/v1/curations/{test_curation.id}/submit",
        json={"lock_version": test_curation.lock_version},
        headers=_h(admin_token),
    )
    assert submit.status_code == 422, submit.text
    assert submit.json()["detail"]["errors"] == [
        {
            "path": "entity_definition.mondo_id",
            "message": "MONDO:9999999 not found in MONDO",
        }
    ]


def test_precuration_draft_merges_and_warns_submit_refuses_malformed(
    client: TestClient,
    curator_token: str,
    db_session: Session,
    test_precuration: PrecurationNew,
    online: MonkeyPatch,
) -> None:
    _terms(online, {"HP:0000006": False})
    r = _draft(
        client,
        curator_token,
        test_precuration,
        "precurations",
        evidence_data={"mondo_id": "mondo:1", "inheritance_hpo_id": "HP:0000006"},
        merge=True,
    )
    assert r.status_code == 200, r.text
    assert r.json()["evidence_data"]["disease_name"] == "Test Disease"
    assert [w["path"] for w in r.json()["warnings"]] == [
        "mondo_id",
        "inheritance_hpo_id",
    ]

    db_session.refresh(test_precuration)
    submit = client.post(
        f"/api/v1/precurations/{test_precuration.id}/submit",
        json={"lock_version": test_precuration.lock_version},
        headers=_h(curator_token),
    )
    assert submit.status_code == 422, submit.text
    # unknown HPO only warns: review entry does not refuse a precuration's unknown IDs
    assert [e["path"] for e in submit.json()["detail"]["errors"]] == ["mondo_id"]


def test_recompute_scores_bad_pmid_rows_as_zero(
    db_session: Session,
    test_curation: CurationNew,
    test_user_admin: object,
    monkeypatch: MonkeyPatch,
) -> None:
    from app.services import recompute_scores

    monkeypatch.setattr(
        recompute_scores, "lookup_pmids", lambda db, pmids: (["99999999"], [])
    )
    rows = _evidence("99999999")["genetic_evidence"]["case_control"]
    rows["single_variant_analysis"].append({"points": 1, "pmid": "PMID12x"})
    rows["single_variant_analysis"].append({"points": 1.5, "pmid": "31000001"})
    test_curation.evidence_data = {"genetic_evidence": {"case_control": rows}}
    db_session.commit()
    recompute_scores.recompute_all_scores(db_session)
    db_session.refresh(test_curation)
    assert test_curation.computed_scores["total_score"] == 1.5
    assert [e["pmid"] for e in test_curation.computed_scores["excluded"]] == [
        "99999999",
        "PMID12x",
    ]


def test_concise_draft_result_carries_id_warnings_and_merge_conflicts_name_keys(
    client: TestClient,
    admin_token: str,
    db_session: Session,
    test_curation: CurationNew,
) -> None:
    test_curation.evidence_data = {"status": "in_progress", "notes": "n"}
    db_session.commit()
    version = test_curation.lock_version
    url = f"/api/v1/curations/{test_curation.id}/draft"
    body = {
        "evidence_data": {"entity_definition": {"mondo_id": "MONDO:1"}},
        "merge": True,
    }
    r = client.patch(
        url, json={**body, "lock_version": version}, headers=_h(admin_token)
    )
    assert r.status_code == 200, r.text
    assert (
        "entity_definition.mondo_id: Expected MONDO:NNNNNNN, e.g. MONDO:0007739"
        in (r.json()["warnings"])
    )

    # a stale patch differs from the current state only where it changes things
    stale = {"evidence_data": {"notes": "mine"}, "merge": True, "lock_version": version}
    r = client.patch(url, json=stale, headers=_h(admin_token))
    assert r.status_code == 409, r.text
    assert r.json()["detail"]["changed_keys"] == ["notes"]


def _transition(client: TestClient, token: str, kind: str, item: Any) -> Any:
    return client.post(
        f"/api/v1/workflow/{kind}/{item.id}/transition",
        json={"target_stage": "review"},
        headers=_h(token),
    )


def test_workflow_transition_refuses_malformed_ids_with_the_path(
    client: TestClient,
    admin_token: str,
    curator_token: str,
    db_session: Session,
    test_curation: CurationNew,
    test_precuration: PrecurationNew,
) -> None:
    test_curation.evidence_data = _evidence("PMID12x")
    test_precuration.evidence_data = {
        **test_precuration.evidence_data,
        "mondo_id": "MONDO:1",
    }
    db_session.commit()

    r = _transition(client, admin_token, "curation", test_curation)
    assert r.status_code == 400, r.text
    assert f"{ROWS}[0].pmid: Expected 1-9 digits" in r.json()["detail"]
    r = _transition(client, curator_token, "precuration", test_precuration)
    assert r.status_code == 400, r.text
    assert "mondo_id: Expected MONDO:NNNNNNN" in r.json()["detail"]
    db_session.refresh(test_curation)
    db_session.refresh(test_precuration)
    assert (test_curation.workflow_stage, test_precuration.workflow_stage) == (
        "curation",
        "precuration",
    )


def test_workflow_transition_refuses_unknown_ontology_ids(
    client: TestClient,
    admin_token: str,
    db_session: Session,
    test_curation: CurationNew,
    online: MonkeyPatch,
) -> None:
    _terms(online, {"HP:0009999": False})
    test_curation.evidence_data = {
        "status": "x",
        "phenotypes": {"hpo_id": "HP:0009999"},
    }
    db_session.commit()
    r = _transition(client, admin_token, "curation", test_curation)
    assert r.status_code == 422, r.text
    assert r.json()["detail"]["errors"] == [
        {"path": "phenotypes.hpo_id", "message": "HP:0009999 not found in HPO"}
    ]


def test_found_pmids_are_cached_so_the_next_save_asks_no_one(
    client: TestClient,
    admin_token: str,
    db_session: Session,
    test_curation: CurationNew,
    online: MonkeyPatch,
) -> None:
    fetched: list[str] = []

    async def fetch(self: PublicationService, pmid: str) -> PMIDValidationResult:
        fetched.append(pmid)
        data = PublicationData(pmid=pmid, title="T", journal="J", year=2020)
        return PMIDValidationResult(pmid=pmid, is_valid=True, publication=data)

    online.setattr(PublicationService, "fetch_publication", fetch)
    for _ in range(2):
        r = _draft(
            client,
            admin_token,
            test_curation,
            "curations",
            evidence_data=_evidence("31000003"),
        )
        assert r.status_code == 200, r.text
        assert r.json()["warnings"] == []
        db_session.refresh(test_curation)
    assert fetched == ["31000003"]
    assert (
        db_session.get(
            Publication,
            db_session.scalars(
                select(Publication.id).where(Publication.pmid == "31000003")
            ).one(),
        ).title
        == "T"
    )


def test_put_and_create_exclude_unknown_pmids_and_warn(
    client: TestClient,
    admin_token: str,
    db_session: Session,
    test_curation: CurationNew,
    approved_precuration: PrecurationNew,
    online: MonkeyPatch,
) -> None:
    _fake_fetch(online, {"99999999": "Publication not found: 99999999"})
    warning = f"{ROWS}[0].pmid: 99999999 not found in PubMed"
    r = client.put(
        f"/api/v1/curations/{test_curation.id}",
        json={"evidence_data": _evidence("99999999"), "lock_version": 0},
        headers=_h(admin_token),
    )
    assert r.status_code == 200, r.text
    assert (r.json()["total_score"], r.json()["warnings"]) == (0, [warning])

    test_curation.status = "archived"  # an open curation blocks a new one
    db_session.commit()
    r = client.post(
        "/api/v1/curations/",
        json={
            "gene_id": str(test_curation.gene_id),
            "scope_id": str(test_curation.scope_id),
            "workflow_pair_id": str(test_curation.workflow_pair_id),
            "evidence_data": _evidence("99999999"),
        },
        headers=_h(admin_token),
    )
    assert r.status_code == 201, r.text
    assert r.json()["computed_scores"]["total_score"] == 0
    assert warning in r.json()["computed_scores"]["warnings"]


def test_a_merge_that_shortens_an_array_warns(
    client: TestClient,
    admin_token: str,
    db_session: Session,
    test_curation: CurationNew,
) -> None:
    test_curation.evidence_data = {"rows": [{"points": 1}, {"points": 2}], "x": [1]}
    db_session.commit()
    r = _draft(
        client,
        admin_token,
        test_curation,
        "curations",
        evidence_data={"rows": [{"points": 3}], "x": [1, 2]},
        merge=True,
    )
    assert r.status_code == 200, r.text
    assert r.json()["evidence_data"]["rows"] == [{"points": 3}]
    assert r.json()["warnings"] == [
        {
            "path": "rows",
            "message": "Merge replaced 2 items with 1; arrays are replaced whole, "
            "so send every row to keep it",
        }
    ]
    r = client.put(
        f"/api/v1/curations/{test_curation.id}",
        json={
            "evidence_data": {"x": []},
            "merge": True,
            "lock_version": r.json()["lock_version"],
        },
        headers=_h(admin_token),
    )
    assert r.status_code == 200, r.text
    assert any(
        w.startswith("x: Merge replaced 2 items with 0") for w in r.json()["warnings"]
    )
