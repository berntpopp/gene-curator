"""422 messages state the limit and the received size or value, never a long input."""

from app.core.validation_messages import explain


def test_explain_sizes_values_and_drops_long_inputs() -> None:
    errors = [
        {
            "type": "string_too_short",
            "loc": ("body", "name"),
            "msg": "m",
            "input": "",
            "ctx": {"min_length": 1},
        },
        {
            "type": "too_long",
            "loc": ("body", "pmids"),
            "msg": "m",
            "input": list(range(60)),
            "ctx": {"max_length": 50},
        },
        {
            "type": "literal_error",
            "loc": ("query", "sort"),
            "msg": "Input should be 'a'",
            "input": "b",
        },
        {"type": "missing", "loc": ("body", "x"), "msg": "Field required"},
    ]
    out = explain(errors)
    assert [e["msg"] for e in out] == [
        "0 characters, min 1; add more",
        "60 items, max 50; shorten it",
        "Input should be 'a' (got 'b')",
        "Field required",
    ]
    assert "input" not in out[1] and out[2]["input"] == "b"
