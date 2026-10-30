"""#534: llm_share schema diagnostics and the shared key set."""

import pytest

from app.llm.sharing import SHARED_EVIDENCE_KEYS, check_llm_share, shared_keys

pytestmark = pytest.mark.unit


def test_flagged_fields_join_the_seeded_keys_but_judgement_never_does() -> None:
    fields = {
        "sections": [
            {
                "id": "s",
                "fields": [{"id": "omim_id", "type": "text", "llm_share": True}],
            }
        ],
        "table": {
            "type": "evidence_table",
            "columns": [{"key": "c", "id": "col", "llm_share": True}],
            "items": {"properties": {"points": {"llm_share": True}}},
        },
    }
    keys = shared_keys(fields)
    assert {"omim_id", "col"} <= keys and keys >= SHARED_EVIDENCE_KEYS
    assert "points" not in keys and "table" not in keys
    assert shared_keys(None) == SHARED_EVIDENCE_KEYS


def test_judgement_flag_is_refused_and_unshared_fields_warned() -> None:
    fields = {
        "rationale": {"type": "text", "llm_share": True},
        "binning": {"type": "select"},
        "mechanism": {"type": "text", "llm_share": "yes"},
        "pmid": {"type": "text"},  # seeded evidence key: shared without a flag
        "kidney": {"type": "text", "llm_share": True},
    }
    assert check_llm_share(fields) == [
        (
            "error",
            "field_definitions.rationale.llm_share",
            "'rationale' is curator judgement and is never shared with LLM runs",
        ),
        (
            "error",
            "field_definitions.mechanism.llm_share",
            "llm_share must be true or false",
        ),
        (
            "warning",
            "field_definitions",
            "Not sent to LLM runs (set llm_share: true to send): binning",
        ),
    ]


def test_llm_share_false_withholds_a_seeded_evidence_key() -> None:
    keys = shared_keys({"description": {"type": "text", "llm_share": False}})
    assert "description" not in keys and "pmid" in keys


def test_one_key_name_shared_in_one_place_and_not_another_is_refused() -> None:
    fields = {
        "notes": {"type": "text", "llm_share": True},
        "group": {"type": "object", "properties": {"notes": {"type": "text"}}},
        "label": {"type": "text"},  # seeded: shared without a flag, here and below
        "table": {"type": "object", "properties": {"label": {"type": "text"}}},
    }
    errors = [d for d in check_llm_share(fields) if d[0] == "error"]
    assert errors == [
        (
            "error",
            "field_definitions.group.properties.notes.llm_share",
            "'notes' is shared with LLM runs in one place and not in another; sharing "
            "is by key name at every depth, so flag every 'notes' the same",
        )
    ]
    withheld = {
        "description": {"llm_share": False},
        "x": {"properties": {"description": {}}},
    }
    assert [d[1] for d in check_llm_share(withheld) if d[0] == "error"] == [
        "field_definitions.x.properties.description.llm_share"
    ]
