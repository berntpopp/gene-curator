"""Structured output validation: model output is untrusted until Pydantic accepts it."""

from typing import TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


class InvalidLLMOutputError(ValueError):
    """Output failed validation. Carries error locations only, never the output text."""


def parse_structured_output(text: str, model: type[T]) -> T:
    """Validate the whole output or raise; there is no partial result."""
    stripped = text.strip()
    if stripped.startswith("```"):  # tolerate a fenced ```json block
        stripped = stripped.split("\n", 1)[-1].rsplit("```", 1)[0]
    try:
        return model.model_validate_json(stripped)
    except ValidationError as exc:
        # str(exc) echoes input values, so only locations leave this function.
        locations = sorted(
            {".".join(str(p) for p in e["loc"]) or "<root>" for e in exc.errors()}
        )
        raise InvalidLLMOutputError(
            f"LLM output failed validation at: {locations}"
        ) from None
