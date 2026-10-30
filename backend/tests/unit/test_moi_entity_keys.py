"""#531: the XL and Undetermined MOI options get stable entity keys of their own."""

from sqlalchemy.orm import Session

from app.crud.precuration_entity import entity_key_of
from app.services.llm_runs import MOI_CODES


def test_xl_and_undetermined_keys_are_stable_and_distinct(db_session: Session) -> None:
    def key(moi: str) -> str:
        return entity_key_of(
            db_session, {"mondo_id": "MONDO:1", "mode_of_inheritance": moi}
        )

    assert key("XL") == key("HP:0001417") == "MONDO:1|XL"
    assert key("Undetermined") == "MONDO:1|UNDETERMINED"
    keys = {key(m) for m in ("XL", "XLD", "XLR", "Undetermined")}
    assert len(keys) == 4


def test_every_schema_moi_value_is_a_trusted_code() -> None:
    assert {
        "AD",
        "AR",
        "XL",
        "XLD",
        "XLR",
        "SD",
        "MT",
        "Undetermined",
        "Other",
    } <= MOI_CODES
