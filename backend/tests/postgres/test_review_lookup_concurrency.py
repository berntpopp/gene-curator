"""PMID preflight never holds the curation lock; stale remote results cannot submit."""

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Event, Lock
from uuid import uuid4

import psycopg2
import pytest

from app.core.security import create_access_token
from app.schemas.validation import PMIDValidationResult
from app.services.publication_service import PublicationService
from tests.postgres.test_submit_unknown_pmids import W, _owner, client as client, w as w

pytestmark = pytest.mark.postgres


def _headers(w: W):
    return {
        "Authorization": f"Bearer {create_access_token(data={'sub': str(w.alice)})}"
    }


def _evidence(pmid="31000001"):
    return {
        "entity_definition": {
            "mondo_id": "MONDO:0000001",
            "disease_name": "disease",
            "mode_of_inheritance": "AD",
        },
        "rows": [{"pmid": pmid}],
    }


def _create(client, w):
    response = client.post(
        "/api/v1/curations/",
        headers=_headers(w),
        json={
            "gene_id": str(w.gene),
            "scope_id": str(w.scope),
            "workflow_pair_id": w.pair,
            "evidence_data": _evidence(),
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _submit(client, w, item, route):
    if route == "submit":
        return client.post(
            f"/api/v1/curations/{item['id']}/submit",
            headers=_headers(w),
            json={"lock_version": item["lock_version"]},
        )
    if route == "direct":
        return client.post(
            f"/api/v1/workflow/curation/{item['id']}/transition",
            headers=_headers(w),
            json={"target_stage": "review"},
        )
    return client.post(
        "/api/v1/workflow/bulk-transition",
        headers=_headers(w),
        json={
            "item_ids": [item["id"]],
            "item_type": "curation",
            "target_stage": "review",
        },
    )


@pytest.mark.parametrize("route", ["submit", "direct", "bulk"])
def test_save_completes_during_lookup_and_stale_submission_conflicts(
    client, w, monkeypatch, route
):
    if route == "bulk":
        with _owner() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET role = 'admin' WHERE id = %s", (str(w.alice),)
            )
    item = _create(client, w)
    started, release = Event(), Event()

    async def fetch(self, pmid):
        started.set()
        assert await asyncio.to_thread(release.wait, 4)
        return PMIDValidationResult(pmid=pmid, is_valid=True)

    monkeypatch.setattr(PublicationService, "fetch_publication", fetch)
    with ThreadPoolExecutor(max_workers=2) as pool:
        submitted = pool.submit(_submit, client, w, item, route)
        try:
            assert started.wait(2)
            saved_future = pool.submit(
                client.patch,
                f"/api/v1/curations/{item['id']}/draft",
                headers=_headers(w),
                json={
                    "lock_version": item["lock_version"],
                    "evidence_data": _evidence("99999999"),
                },
            )
            saved = saved_future.result(timeout=1)
            assert saved.status_code == 200, saved.text
        finally:
            release.set()
        refused = submitted.result(timeout=3)
    if route == "bulk":
        assert refused.status_code == 200
        assert refused.json()["total_failed"] == 1, refused.text
        assert "Concurrent" in refused.text
    else:
        assert refused.status_code == 409, refused.text
    loaded = client.get(f"/api/v1/curations/{item['id']}", headers=_headers(w)).json()
    assert loaded["evidence_data"] == _evidence("99999999")
    assert loaded["lock_version"] == item["lock_version"] + 1
    assert loaded["workflow_stage"] == "curation"


@pytest.mark.parametrize("change", ["membership", "status", "pin"])
def test_permissions_and_state_are_rechecked_after_lookup(
    client, w, monkeypatch, change
):
    item = _create(client, w)
    started, release = Event(), Event()

    async def fetch(self, pmid):
        started.set()
        assert await asyncio.to_thread(release.wait, 4)
        return PMIDValidationResult(pmid=pmid, is_valid=True)

    monkeypatch.setattr(PublicationService, "fetch_publication", fetch)
    with ThreadPoolExecutor(max_workers=1) as pool:
        submitted = pool.submit(_submit, client, w, item, "submit")
        try:
            assert started.wait(2)
            with _owner() as conn, conn.cursor() as cur:
                if change == "membership":
                    cur.execute(
                        "UPDATE scope_memberships SET accepted_at = NULL WHERE user_id = %s AND scope_id = %s",
                        (str(w.alice), str(w.scope)),
                    )
                elif change == "status":
                    cur.execute(
                        "UPDATE curations SET status = 'rejected' WHERE id = %s",
                        (item["id"],),
                    )
                else:
                    # A changed pin must never use results captured from the old snapshot.
                    with pytest.raises(
                        psycopg2.errors.IntegrityConstraintViolation,
                        match="pinned at creation",
                    ):
                        cur.execute(
                            "UPDATE curations SET methodology_version_id = NULL WHERE id = %s",
                            (item["id"],),
                        )
                    conn.rollback()
        finally:
            release.set()
        refused = submitted.result(timeout=3)
    assert (
        refused.status_code == ({"membership": 403, "status": 409, "pin": 200}[change])
    ), refused.text
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT workflow_stage, submitted_at, methodology_version_id FROM curations WHERE id = %s",
            (item["id"],),
        )
        stage, submitted_at, pin = cur.fetchone()
        if change == "pin":
            assert stage == "review" and submitted_at is not None
            assert str(pin) == item["methodology_version_id"]
        else:
            assert (stage, submitted_at) == ("curation", None)


def test_two_simultaneous_submits_create_only_one_review_entry(client, w, monkeypatch):
    item = _create(client, w)
    both_started, release, counter_lock = Event(), Event(), Lock()
    count = 0

    async def fetch(self, pmid):
        nonlocal count
        with counter_lock:
            count += 1
            if count == 2:
                both_started.set()
        assert await asyncio.to_thread(release.wait, 4)
        return PMIDValidationResult(pmid=pmid, is_valid=True)

    monkeypatch.setattr(PublicationService, "fetch_publication", fetch)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(_submit, client, w, item, "submit") for _ in range(2)]
        try:
            assert both_started.wait(2)
        finally:
            release.set()
        responses = [future.result(timeout=3) for future in futures]
    assert sorted(r.status_code for r in responses) == [200, 409], [
        r.text for r in responses
    ]
    loaded = client.get(f"/api/v1/curations/{item['id']}", headers=_headers(w)).json()
    assert loaded["workflow_stage"] == "review"
    assert loaded["lock_version"] == item["lock_version"] + 1


def _another(client, w, pmid):
    gene = uuid4()
    w.extra_genes.append(gene)
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO genes (id, hgnc_id, approved_symbol, record_hash) VALUES (%s, %s, %s, %s)",
            (str(gene), f"HGNC:{gene.int % 10**9}", f"G{gene.hex[:8]}", gene.hex * 2),
        )
        cur.execute(
            "INSERT INTO precurations (gene_id, scope_id, precuration_schema_id, status, workflow_stage, is_draft, created_by) "
            "SELECT %s, scope_id, precuration_schema_id, 'approved', 'curation', false, created_by FROM precurations WHERE id = %s",
            (str(gene), str(w.pre)),
        )
    made = client.post(
        "/api/v1/curations/",
        headers=_headers(w),
        json={
            "gene_id": str(gene),
            "scope_id": str(w.scope),
            "workflow_pair_id": w.pair,
            "evidence_data": _evidence(pmid),
        },
    )
    assert made.status_code == 201, made.text
    return made.json()


def test_mixed_bulk_deduplicates_lookup_and_keeps_rls_after_each_commit(
    client, w, monkeypatch
):
    with _owner() as conn, conn.cursor() as cur:
        cur.execute("UPDATE users SET role = 'admin' WHERE id = %s", (str(w.alice),))
    items = [
        _create(client, w),
        _another(client, w, "99999999"),
        _another(client, w, "31000001"),
    ]
    fetched = []

    async def fetch(self, pmid):
        fetched.append(pmid)
        return PMIDValidationResult(
            pmid=pmid,
            is_valid=pmid != "99999999",
            error="Publication not found: 99999999" if pmid == "99999999" else None,
        )

    monkeypatch.setattr(PublicationService, "fetch_publication", fetch)
    response = client.post(
        "/api/v1/workflow/bulk-transition",
        headers=_headers(w),
        json={
            "item_ids": [i["id"] for i in items],
            "item_type": "curation",
            "target_stage": "review",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["successful_transitions"] == [items[0]["id"], items[2]["id"]]
    assert response.json()["total_failed"] == 1
    assert "99999999" in response.json()["failed_transitions"][0]["error"]
    assert sorted(fetched) == ["31000001", "99999999"]
    for index, item in enumerate(items):
        result = client.get(f"/api/v1/curations/{item['id']}", headers=_headers(w))
        assert result.status_code == 200
        assert result.json()["workflow_stage"] == (
            "curation" if index == 1 else "review"
        )


def test_bulk_never_looks_up_an_ineligible_curation(client, w, monkeypatch):
    item = _create(client, w)
    with _owner() as conn, conn.cursor() as cur:
        cur.execute("UPDATE users SET role = 'admin' WHERE id = %s", (str(w.alice),))
        cur.execute(
            "UPDATE curations SET workflow_stage = 'archived', status = 'archived' WHERE id = %s",
            (item["id"],),
        )
    fetched = []

    async def fetch(self, pmid):
        fetched.append(pmid)
        return PMIDValidationResult(pmid=pmid, is_valid=True)

    monkeypatch.setattr(PublicationService, "fetch_publication", fetch)
    response = _submit(client, w, item, "bulk")
    assert response.status_code == 200, response.text
    assert response.json()["total_failed"] == 1
    assert not fetched


def test_viewer_cannot_start_remote_lookup_for_private_work(client, w, monkeypatch):
    item = _create(client, w)
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE scope_memberships SET role = 'viewer' WHERE user_id = %s AND scope_id = %s",
            (str(w.alice), str(w.scope)),
        )
    fetched = []

    async def fetch(self, pmid):
        fetched.append(pmid)
        return PMIDValidationResult(pmid=pmid, is_valid=True)

    monkeypatch.setattr(PublicationService, "fetch_publication", fetch)
    response = _submit(client, w, item, "direct")
    assert response.status_code == 400, response.text
    assert not fetched


@pytest.mark.parametrize("route", ["submit", "direct", "bulk"])
@pytest.mark.parametrize("remove_linked_disease", [False, True])
def test_inherited_disease_is_rechecked_after_remote_lookup(
    client, w, monkeypatch, route, remove_linked_disease
):
    disease = _evidence()["entity_definition"]
    with _owner() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE precurations SET evidence_data = %s WHERE id = %s",
            (json.dumps(disease), str(w.pre)),
        )
        if route == "bulk":
            cur.execute(
                "UPDATE users SET role = 'admin' WHERE id = %s", (str(w.alice),)
            )
    evidence = {"rows": [{"pmid": "31000001"}]}
    made = client.post(
        "/api/v1/curations/",
        headers=_headers(w),
        json={
            "gene_id": str(w.gene),
            "scope_id": str(w.scope),
            "workflow_pair_id": w.pair,
            "precuration_id": str(w.pre),
            "evidence_data": evidence,
        },
    )
    assert made.status_code == 201, made.text
    item = made.json()
    fetched = []

    async def fetch(self, pmid):
        fetched.append(pmid)
        if remove_linked_disease:
            # A separate connection changes the inherited source during remote I/O.
            with _owner() as conn, conn.cursor() as cur:
                cur.execute(
                    "UPDATE precurations SET evidence_data = '{}' WHERE id = %s",
                    (str(w.pre),),
                )
        return PMIDValidationResult(pmid=pmid, is_valid=True)

    monkeypatch.setattr(PublicationService, "fetch_publication", fetch)
    result = _submit(client, w, item, route)
    assert fetched == ["31000001"]
    loaded = client.get(f"/api/v1/curations/{item['id']}", headers=_headers(w))
    assert loaded.status_code == 200, loaded.text
    after = loaded.json()
    assert after["evidence_data"] == evidence
    if remove_linked_disease:
        assert result.status_code == (200 if route == "bulk" else 400), result.text
        if route == "bulk":
            assert result.json()["total_failed"] == 1
        assert "entity_definition.disease_name" in result.text
        for field in (
            "status",
            "workflow_stage",
            "lock_version",
            "evidence_data",
            "is_draft",
        ):
            assert after[field] == item[field]
    else:
        assert result.status_code == 200, result.text
        if route == "bulk":
            assert result.json()["total_successful"] == 1
        assert after["workflow_stage"] == "review"
        assert after["lock_version"] == item["lock_version"] + 1
