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
