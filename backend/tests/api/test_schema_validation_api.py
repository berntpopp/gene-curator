"""API tests for the schema validation endpoints (/api/v1/validation/...).

Covers evidence and schema-definition validation, JSON Schema generation,
single-field validation, reference endpoints, and the admin-only test runner.
Engine failures are simulated by patching the validator; they must surface as 500.
"""

from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import CurationSchema

pytestmark = pytest.mark.unit

BASE = "/api/v1/validation"
VALIDATOR = "app.api.v1.endpoints.schema_validation.schema_validator"

FIELD_DEFS = {
    "gene_symbol": {"type": "text", "min_length": 2, "required": True},
    "score": {"type": "number", "min_value": 0, "max_value": 12},
    "pmid": {"type": "pmid"},
}


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def stored_schema(db_session: Session) -> CurationSchema:
    schema = CurationSchema(
        id=uuid4(),
        name="Stored",
        version="1.0",
        schema_type="curation",
        field_definitions=FIELD_DEFS,
        validation_rules={},
        workflow_states={"states": [], "transitions": {}},
        ui_configuration={"sections": []},
        is_active=True,
        schema_hash=uuid4().hex,
    )
    db_session.add(schema)
    db_session.commit()
    db_session.refresh(schema)
    return schema


# =============================================================================
# Evidence validation
# =============================================================================


class TestValidateEvidence:
    def test_inline_definition_valid(self, client: TestClient, viewer_token: str):
        response = client.post(
            f"{BASE}/validate-evidence",
            json={
                "evidence_data": {
                    "gene_symbol": "TP53",
                    "score": 4,
                    "pmid": "12345678",
                },
                "schema_definition": {"field_definitions": FIELD_DEFS},
            },
            headers=_auth(viewer_token),
        )

        assert response.status_code == 200
        body = response.json()
        assert body["is_valid"] is True
        assert body["errors"] == []
        assert body["completeness_score"] == pytest.approx(100.0)
        assert set(body) >= {
            "warnings",
            "field_validations",
            "business_rule_violations",
            "score_calculations",
            "required_fields_missing",
            "suggested_improvements",
        }

    def test_inline_definition_reports_field_errors(
        self, client: TestClient, viewer_token: str
    ):
        response = client.post(
            f"{BASE}/validate-evidence",
            json={
                "evidence_data": {"gene_symbol": "T", "score": 15},
                "schema_definition": {"field_definitions": FIELD_DEFS},
            },
            headers=_auth(viewer_token),
        )

        body = response.json()
        assert body["is_valid"] is False
        assert "gene_symbol" in body["field_validations"]
        assert "score" in body["field_validations"]
        assert body["required_fields_missing"] == []

    def test_missing_required_listed(self, client: TestClient, viewer_token: str):
        response = client.post(
            f"{BASE}/validate-evidence",
            json={
                "evidence_data": {},
                "schema_definition": {"field_definitions": FIELD_DEFS},
            },
            headers=_auth(viewer_token),
        )

        assert response.json()["required_fields_missing"] == ["gene_symbol"]

    def test_stored_schema_by_id(
        self, client: TestClient, stored_schema: CurationSchema, viewer_token: str
    ):
        response = client.post(
            f"{BASE}/validate-evidence",
            json={
                "evidence_data": {"gene_symbol": "BRCA1"},
                "schema_id": str(stored_schema.id),
            },
            headers=_auth(viewer_token),
        )

        assert response.status_code == 200
        assert response.json()["is_valid"] is True

    def test_unknown_schema_id_is_404(self, client: TestClient, viewer_token: str):
        response = client.post(
            f"{BASE}/validate-evidence",
            json={"evidence_data": {}, "schema_id": str(uuid4())},
            headers=_auth(viewer_token),
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Schema not found"

    def test_neither_schema_nor_definition_is_400(
        self, client: TestClient, viewer_token: str
    ):
        response = client.post(
            f"{BASE}/validate-evidence",
            json={"evidence_data": {}},
            headers=_auth(viewer_token),
        )

        assert response.status_code == 400
        assert "must be provided" in response.json()["detail"]

    def test_engine_exception_becomes_500(self, client: TestClient, viewer_token: str):
        with patch(VALIDATOR) as mocked:
            mocked.validate_evidence_data.side_effect = RuntimeError("boom")
            response = client.post(
                f"{BASE}/validate-evidence",
                json={
                    "evidence_data": {},
                    "schema_definition": {"field_definitions": {}},
                },
                headers=_auth(viewer_token),
            )

        assert response.status_code == 500
        assert response.json()["detail"] == "Validation error: boom"


# =============================================================================
# Schema definition validation
# =============================================================================


class TestValidateSchemaDefinition:
    def test_empty_definition_reports_missing_keys(
        self, client: TestClient, viewer_token: str
    ):
        response = client.post(
            f"{BASE}/validate-schema",
            json={"schema_definition": {}},
            headers=_auth(viewer_token),
        )

        assert response.status_code == 200
        body = response.json()
        assert body["is_valid"] is False
        assert len(body["errors"]) == 2

    def test_complete_definition_valid(self, client: TestClient, viewer_token: str):
        response = client.post(
            f"{BASE}/validate-schema",
            json={
                "schema_definition": {
                    "field_definitions": {"a": {"type": "text", "label": "A"}},
                    "workflow_states": ["draft", "submitted"],
                    "ui_configuration": {"sections": []},
                    "scoring_configuration": {"engine": "clingen"},
                }
            },
            headers=_auth(viewer_token),
        )

        assert response.json()["is_valid"] is True

    def test_engine_exception_becomes_500(self, client: TestClient, viewer_token: str):
        with patch(VALIDATOR) as mocked:
            mocked.validate_schema_definition.side_effect = ValueError("bad")
            response = client.post(
                f"{BASE}/validate-schema",
                json={"schema_definition": {}},
                headers=_auth(viewer_token),
            )

        assert response.status_code == 500
        assert response.json()["detail"] == "Schema validation error: bad"


# =============================================================================
# JSON Schema generation
# =============================================================================


class TestJsonSchema:
    def test_generate_reports_counts(self, client: TestClient, viewer_token: str):
        response = client.post(
            f"{BASE}/generate-json-schema",
            json={
                "schema_definition": {
                    "field_definitions": FIELD_DEFS,
                    "validation_rules": {"r": {}},
                }
            },
            headers=_auth(viewer_token),
        )

        assert response.status_code == 200
        body = response.json()
        assert body["field_count"] == 3
        assert body["validation_rules_count"] == 1
        assert body["json_schema"]["required"] == ["gene_symbol"]
        assert body["json_schema"]["properties"]["score"]["maximum"] == 12

    def test_generate_engine_exception_becomes_500(
        self, client: TestClient, viewer_token: str
    ):
        with patch(VALIDATOR) as mocked:
            mocked.generate_json_schema.side_effect = KeyError("x")
            response = client.post(
                f"{BASE}/generate-json-schema",
                json={"schema_definition": {}},
                headers=_auth(viewer_token),
            )

        assert response.status_code == 500
        assert "JSON Schema generation error" in response.json()["detail"]

    def test_stored_schema_json_schema(
        self, client: TestClient, stored_schema: CurationSchema, viewer_token: str
    ):
        response = client.get(
            f"{BASE}/schema/{stored_schema.id}/json-schema",
            headers=_auth(viewer_token),
        )

        assert response.status_code == 200
        body = response.json()
        assert body["field_count"] == 3
        assert "gene_symbol" in body["json_schema"]["properties"]

    def test_stored_schema_unknown_is_404(self, client: TestClient, viewer_token: str):
        response = client.get(
            f"{BASE}/schema/{uuid4()}/json-schema", headers=_auth(viewer_token)
        )

        assert response.status_code == 404


# =============================================================================
# Single field validation
# =============================================================================


class TestValidateField:
    def test_valid_field(self, client: TestClient, viewer_token: str):
        response = client.post(
            f"{BASE}/validate-field",
            json={
                "field_name": "pmid",
                "field_value": "12345678",
                "field_config": {"type": "pmid"},
            },
            headers=_auth(viewer_token),
        )

        body = response.json()
        assert response.status_code == 200
        assert body == {
            "field_name": "pmid",
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "suggestions": body["suggestions"],
        }

    def test_invalid_field_reports_errors(self, client: TestClient, viewer_token: str):
        response = client.post(
            f"{BASE}/validate-field",
            json={
                "field_name": "pmid",
                "field_value": "abc",
                "field_config": {"type": "pmid"},
            },
            headers=_auth(viewer_token),
        )

        body = response.json()
        assert body["is_valid"] is False
        assert body["errors"][0]["message"] == "PMID must contain only digits"

    def test_field_exception_becomes_500(self, client: TestClient, viewer_token: str):
        with patch(VALIDATOR) as mocked:
            mocked.validate_evidence_data.side_effect = RuntimeError("nope")
            response = client.post(
                f"{BASE}/validate-field",
                json={"field_name": "f", "field_value": 1, "field_config": {}},
                headers=_auth(viewer_token),
            )

        assert response.status_code == 500
        assert "Field validation error" in response.json()["detail"]


# =============================================================================
# Reference endpoints
# =============================================================================


class TestReferenceEndpoints:
    def test_supported_field_types(self, client: TestClient, viewer_token: str):
        response = client.get(
            f"{BASE}/supported-field-types", headers=_auth(viewer_token)
        )

        body = response.json()
        assert response.status_code == 200
        assert body["total_supported_types"] == len(body["field_types"]) == 13
        assert "pmid" in body["field_types"]
        assert body["field_types"]["select"]["supported_config"] == [
            "options",
            "required",
        ]

    def test_business_rules_catalogue(self, client: TestClient, viewer_token: str):
        response = client.get(f"{BASE}/business-rules", headers=_auth(viewer_token))

        body = response.json()
        assert body["total_rules"] == len(body["business_rules"]) == 5
        assert "clingen_genetic_evidence" in body["business_rules"]

    def test_reference_endpoints_require_auth(self, client: TestClient):
        assert client.get(f"{BASE}/supported-field-types").status_code in (401, 403)
        assert client.get(f"{BASE}/business-rules").status_code in (401, 403)


# =============================================================================
# Admin-only validation test runner
# =============================================================================


class TestValidationSmokeRunner:
    def test_curator_forbidden(self, client: TestClient, curator_token: str):
        response = client.post(f"{BASE}/test-validation", headers=_auth(curator_token))

        assert response.status_code == 403
        assert response.json()["detail"] == "Admin privileges required"

    def test_admin_runs_examples(self, client: TestClient, admin_token: str):
        response = client.post(f"{BASE}/test-validation", headers=_auth(admin_token))

        assert response.status_code == 200
        body = response.json()
        assert body["validation_system_status"] == "operational"
        results = body["test_results"]
        assert len(results) == 4
        assert all("error" not in r for r in results.values())
        assert all(
            {"is_valid", "error_count", "warning_count"} <= set(r)
            for r in results.values()
        )


SECTIONED = {
    "sections": [
        {
            "id": "disease",
            "fields": [
                {"id": "mondo_id", "type": "text", "required": True},
                {"id": "score", "type": "number", "min_value": 0, "max_value": 3},
            ],
        }
    ]
}


class TestSectionedSchemas:
    def test_validate_evidence_handles_sectioned_definitions(
        self, client: TestClient, viewer_token: str
    ):
        """Seeded precuration schemas use `sections`; the validator used to 500."""
        r = client.post(
            f"{BASE}/validate-evidence",
            json={
                "evidence_data": {"score": 9},
                "schema_definition": {"field_definitions": SECTIONED},
            },
            headers=_auth(viewer_token),
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["is_valid"] is False
        assert body["required_fields_missing"] == ["mondo_id"]
        assert "score" in body["field_validations"]
