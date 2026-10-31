"""#593: an MCP write's agent block becomes a software contribution on behalf of the
token's user (row provenance and export); without it nothing changes; no AI approves."""

from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.mcp.audit import AGENT_TOOLS
from app.models import ActiveCuration, CurationNew, CurationStatus, UserNew
from tests.api.scopes.factories import make_member, make_user
from tests.api.test_mcp import call, pat, rpc, status_of

pytestmark = pytest.mark.unit

AGENT = {
    "model": "claude-opus-5-5",
    "agent": "Claude Code",
    "tools_used": ["genefoundry:clinvar_get_variant"],
}
SOURCE = {
    "kind": "clinvar",
    "id": "VCV000012345",
    "tool": "genefoundry:clinvar_get_variant",
    "retrieved_at": "2026-10-31T10:00:00Z",
}
ROW = {"id": "r1", "variant": "c.1A>G", "sources": [SOURCE], "direction": "supports"}


def _save(
    client: TestClient, token: str, c: CurationNew, db: Session, **kw: Any
) -> dict:
    db.refresh(c)
    return call(
        client,
        token,
        "save_draft_curations",
        curation_id=str(c.id),
        lock_version=c.lock_version,
        **kw,
    )


def _export(client: TestClient, db: Session, c: CurationNew, token: str) -> dict:
    db.add(
        ActiveCuration(
            gene_id=c.gene_id,
            scope_id=c.scope_id,
            curation_id=c.id,
            entity_key="",
            activated_at=datetime.now(UTC),
        )
    )
    c.status = CurationStatus.ACTIVE
    db.commit()
    r = client.get(
        "/api/v1/export/curations", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200, r.text
    [item] = r.json()["items"]
    return dict(item)


def test_agent_block_is_a_software_contribution_on_behalf_of_the_user(
    client: TestClient,
    db_session: Session,
    test_user_curator: UserNew,
    test_curation: CurationNew,
) -> None:
    token = pat(db_session, test_user_curator)
    result = _save(
        client,
        token,
        test_curation,
        db_session,
        evidence_data={"genetic": {"probands": [ROW]}},
        agent=AGENT,
    )
    assert status_of(result) == 200, result
    db_session.refresh(test_curation)
    assert test_curation.evidence_data == {"genetic": {"probands": [ROW]}}  # as sent
    added = test_curation.row_provenance["genetic.probands#r1"]["added_by"]
    assert added == {
        "id": str(test_user_curator.id),
        "name": "Curator User",
        "agent": AGENT,
    }

    item = _export(client, db_session, test_curation, token)
    [line] = item["evidence_lines"]
    assert (line["path"], line["row_id"]) == ("genetic.probands[0]", "r1")
    assert line["directionOfEvidenceProvided"] == "supports"
    assert line["sources"][0]["documentType"] == "clinvar"
    assert line["sources"][0]["tool"] == "genefoundry:clinvar_get_variant"
    person, software = line["contributions"]
    assert person["contributor"] == {
        "name": "Curator User",
        "agentType": "person",
        "id": None,
        "description": None,
        "extensions": None,
    }
    assert person["activityType"]["primaryCoding"]["code"] == "SEPIO:0000156"
    assert software["contributor"]["agentType"] == "software"
    assert software["contributor"]["name"] == "claude-opus-5-5"
    assert software["contributor"]["extensions"] == [
        {"name": "tools_used", "value": AGENT["tools_used"]}
    ]
    assert software["actedOnBehalfOf"]["name"] == "Curator User"
    roles = [
        (c["contributor"]["agentType"], c["activityType"]["name"])
        for c in item["contributions"]
    ]
    assert roles == [("person", "curator"), ("software", "curator")]


def test_without_an_agent_block_nothing_changes(
    client: TestClient,
    db_session: Session,
    test_user_curator: UserNew,
    test_curation: CurationNew,
) -> None:
    token = pat(db_session, test_user_curator)
    evidence = {"genetic": {"probands": [ROW]}}
    assert (
        status_of(
            _save(client, token, test_curation, db_session, evidence_data=evidence)
        )
        == 200
    )
    db_session.refresh(test_curation)
    stamp = test_curation.row_provenance["genetic.probands#r1"]
    assert "agent" not in stamp["added_by"]
    item = _export(client, db_session, test_curation, token)
    agents = {
        c["contributor"]["agentType"]
        for c in item["contributions"] + item["evidence_lines"][0]["contributions"]
    }
    assert agents == {"person"}


def test_an_ai_only_approval_is_impossible(
    client: TestClient,
    db_session: Session,
    test_scope: Any,
    test_precuration: Any,
) -> None:
    """Approvals take no agent block, and the token's person may not approve own work."""
    tools = rpc(
        client, pat(db_session, make_user(db_session, role="admin")), "tools/list", {}
    )
    with_agent = {
        t["name"]
        for t in tools.json()["result"]["tools"]
        if "agent" in t["inputSchema"]["properties"]
    }
    assert with_agent == AGENT_TOOLS
    assert (
        not {"approve_precuration", "submit_peer_review", "execute_workflow_transition"}
        & with_agent
    )

    user = make_user(db_session, role="admin")
    make_member(db_session, test_scope, user, "reviewer")
    test_precuration.created_by = user.id
    test_precuration.status = CurationStatus.SUBMITTED
    db_session.commit()
    token = pat(db_session, user)
    pid = str(test_precuration.id)
    refused = call(
        client, token, "approve_precuration", precuration_id=pid, agent=AGENT
    )
    assert refused["isError"] and "unknown agent" in refused["content"][0]["text"]
    assert (
        status_of(call(client, token, "approve_precuration", precuration_id=pid)) == 403
    )


def test_history_shows_the_agent_of_a_submission(
    client: TestClient,
    db_session: Session,
    test_user_curator: UserNew,
    test_curation: CurationNew,
) -> None:
    """The audit row of an MCP submit carries the agent (080); the trail shows it."""
    from app.models import AuditLogNew

    stamped = {**AGENT, "actedOnBehalfOf": str(test_user_curator.id)}
    db_session.add(
        AuditLogNew(
            id=1,
            entity_type="curations",
            entity_id=test_curation.id,
            scope_id=test_curation.scope_id,
            operation="UPDATE",
            user_id=test_user_curator.id,
            previous_status="draft",
            new_status="submitted",
            change_metadata={"channel": "mcp", "agent": stamped},
            timestamp=datetime.now(UTC),
        )
    )
    db_session.commit()
    token = pat(db_session, test_user_curator)
    result = call(
        client,
        token,
        "get_workflow_audit_trail",
        item_type="curation",
        item_id=str(test_curation.id),
    )
    assert status_of(result) == 200, result
    assert '"actedOnBehalfOf"' in result["content"][0]["text"]
    assert "claude-opus-5-5" in result["content"][0]["text"]
