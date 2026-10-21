"""Structured per-item diff of two evidence_data snapshots (#279)."""

from app.services.evidence_diff import diff_evidence


def _by_path(items: list[dict]) -> dict[str, dict]:
    return {i["path"]: i for i in items}


def test_identical_documents_have_no_changes() -> None:
    doc = {"a": 1, "b": {"c": [1, 2]}}
    assert diff_evidence(doc, doc) == []


def test_changed_added_and_removed_scalars_use_dotted_paths() -> None:
    before = {"genetic": {"score": 1, "note": "x"}, "gone": True}
    after = {"genetic": {"score": 2, "extra": "y"}, "other": 1}
    got = _by_path(diff_evidence(before, after))
    assert got["genetic.score"] == {
        "path": "genetic.score",
        "change": "changed",
        "before": 1,
        "after": 2,
    }
    assert got["genetic.note"]["change"] == "removed"
    assert got["genetic.note"]["before"] == "x"
    assert got["genetic.extra"]["change"] == "added"
    assert got["genetic.extra"]["after"] == "y"
    assert got["gone"]["change"] == "removed"
    assert got["other"]["change"] == "added"


def test_added_subtree_is_one_item_not_one_per_leaf() -> None:
    got = diff_evidence({}, {"case_level": {"a": 1, "b": {"c": 2}}})
    assert got == [
        {
            "path": "case_level",
            "change": "added",
            "before": None,
            "after": {"a": 1, "b": {"c": 2}},
        }
    ]


def test_lists_of_records_are_matched_by_id_not_position() -> None:
    before = {"cases": [{"id": "a", "score": 1}, {"id": "b", "score": 2}]}
    after = {
        "cases": [
            {"id": "c", "score": 3},
            {"id": "a", "score": 1},
            {"id": "b", "score": 5},
        ]
    }
    got = _by_path(diff_evidence(before, after))
    assert set(got) == {"cases[c]", "cases[b].score"}
    assert got["cases[c]"]["change"] == "added"
    assert got["cases[b].score"]["after"] == 5


def test_plain_lists_compare_by_position_and_type_changes_are_whole_item_changes() -> (
    None
):
    got = _by_path(
        diff_evidence({"l": [1, 2], "t": {"a": 1}}, {"l": [1, 3, 4], "t": [1]})
    )
    assert got["l[1]"]["change"] == "changed"
    assert got["l[2]"]["change"] == "added"
    assert got["t"]["change"] == "changed"
    assert got["t"]["before"] == {"a": 1}


def test_removed_list_item_is_reported() -> None:
    got = _by_path(diff_evidence({"l": [1, 2, 3]}, {"l": [1]}))
    assert got["l[1]"]["change"] == "removed"
    assert got["l[2]"]["change"] == "removed"
