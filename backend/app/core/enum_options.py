"""Labelled enum options for the generated JSON schema (#327)."""

import re
from typing import Any


def enum_option(option: Any) -> dict[str, Any]:
    """{value, label}: the definition's label, else a humanised lowercase value (as the UI did)."""
    if isinstance(option, dict):
        value = option["value"]
        label = option.get("label")
    else:
        value, label = option, None
    if not label:
        text = str(value)
        label = (
            text.replace("_", " ").capitalize()
            if re.fullmatch(r"[a-z0-9]+([_/ -][a-z0-9]+)*", text)
            else text
        )
    return {"value": value, "label": label}
