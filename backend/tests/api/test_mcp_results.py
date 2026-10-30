"""MCP-only result shaping (MCP study round 7, finding 2: token cost)."""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.mcp.results import pick, shape, word_diff
from app.models import CurationNew, PrecurationNew, UserNew
from tests.api.test_mcp import call, pat

pytestmark = pytest.mark.unit

SUMMARY = " ".join(f"w{i}" for i in range(60))


def test_get_curation_is_concise_on_mcp_and_fields_picks_paths(
    client: TestClient,
    db_session: Session,
    test_user_curator: UserNew,
    test_curation: CurationNew,
) -> None:
    test_curation.evidence_data = {"genetic_evidence": {"segregation": [{"pmid": "1"}]}}
    db_session.commit()
    token, cid = pat(db_session, test_user_curator), str(test_curation.id)

    def read(path: str, **args: object) -> dict:
        result = call(client, token, "get_curation", path=path, curation_id=cid, **args)
        assert not result.get("isError"), result
        return json.loads(result["content"][0]["text"])

    concise = read("/mcp")
    assert "evidence_data" not in concise and "fields=" in concise["omitted"]
    assert concise["lock_version"] == test_curation.lock_version
    assert "evidence_data" in read("/mcp/full")  # parity: full by default
    picked = read("/mcp", fields=["evidence_data.genetic_evidence", "status", "nope"])
    assert picked == {
        "id": cid,
        "lock_version": test_curation.lock_version,
        "evidence_data": {"genetic_evidence": {"segregation": [{"pmid": "1"}]}},
        "status": concise["status"],
        "unknown_fields": ["nope"],
    }
    refused = call(client, token, "get_curation", curation_id=cid, fields="x")
    assert refused["content"][0]["text"].startswith("invalid_input: get_curation")


def test_precuration_writes_do_not_echo_the_evidence(
    client: TestClient,
    db_session: Session,
    test_user_curator: UserNew,
    test_precuration: PrecurationNew,
) -> None:
    token, pid = pat(db_session, test_user_curator), str(test_precuration.id)
    args = {"precuration_id": pid, "evidence_data": {"notes": SUMMARY}}
    args["lock_version"] = test_precuration.lock_version
    core = call(client, token, "save_draft_precurations", path="/mcp", **args)
    saved = json.loads(core["content"][0]["text"])
    assert "evidence_data" not in saved and saved["lock_version"] > args["lock_version"]
    read = call(client, token, "get_precuration", path="/mcp", precuration_id=pid)
    assert json.loads(read["content"][0]["text"])["evidence_data"]["notes"] == SUMMARY


def test_long_text_changes_become_a_word_diff() -> None:
    after = SUMMARY.replace("w30", "w30 new words")
    diff = {"items": [
        {"path": "evidence_summary", "change": "changed", "before": SUMMARY, "after": after},
        {"path": "x.points", "change": "changed", "before": 1, "after": 2},
    ]}  # fmt: skip
    out = shape("curation_diff", diff, lean=True, args={})
    assert out["items"][0] == {
        "path": "evidence_summary",
        "change": "changed",
        "word_diff": "... w23 w24 w25 w26 w27 w28 w29 w30 {+new words+} w31 w32 w33 "
        "w34 w35 w36 w37 w38 ...",
    }
    assert out["items"][1]["before"] == 1  # short values stay as they are
    assert word_diff("a  b", "a b") == "(whitespace changed only)"
    assert word_diff("a b c", "a x c") == "a [-b-] {+x+} c"
    full = {"items": [{"before": SUMMARY, "after": after}]}
    assert shape("curation_diff", full, lean=False, args={}) == full  # /mcp/full


def test_blocked_reasons_are_listed_once() -> None:
    def state() -> dict:
        return {
            "blocked": [
                {"stage": "active", "reason": "not a reviewer"},
                {"stage": "curation", "reason": "not a reviewer"},
                {"stage": "entry", "reason": "other"},
            ]
        }

    grouped = [
        {"stages": ["active", "curation"], "reason": "not a reviewer"},
        {"stages": ["entry"], "reason": "other"},
    ]
    assert (
        shape("get_workflow_state", state(), lean=True, args={})["blocked"] == grouped
    )
    review = {"workflow": state(), "diff": None}
    out = shape("read_curation_for_review", review, lean=True, args={})
    assert out["workflow"]["blocked"] == grouped
    assert shape("get_workflow_state", {"blocked": []}, lean=True, args={}) == {
        "blocked": []
    }


def test_unknown_pmids_say_the_next_step() -> None:
    found = {"pmid": "1", "is_valid": True, "status": "found"}
    missing = {"pmid": "9", "is_valid": False, "status": "not_found"}
    out = shape("validate_pmids", {"results": [found, missing]}, lean=True, args={})
    assert "next" not in out["results"][0]
    assert out["results"][1]["next"].startswith("fix or remove the PMID")
    assert "submit refuses it" in out["results"][1]["next"]
    assert shape("validate_pmids", [1], lean=True, args={}) == [1]  # not an object


def test_pick_keeps_id_and_lock_version() -> None:
    data = {"id": "c", "lock_version": 2, "a": {"b": 1}, "s": "x"}
    assert pick(data, ["a.b", "s.t"]) == {
        "id": "c",
        "lock_version": 2,
        "a": {"b": 1},
        "unknown_fields": ["s.t"],
    }
