from typing import Any
from src.llm.models import FitLabel, RemoteScope, RemoteType, YesNoUnknown, Seniority, SalaryPeriod
def build_job_match_schema(schema_version: str) -> dict[str, Any]:
    if schema_version != "job_match_result_v1":
        raise ValueError(f"Unsupported schema version: {schema_version}")

    return {
        "name": "job_match_result",
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "raw_job_ad_id": {"type": "integer"},
                "fit_score": {"type": "integer", "minimum": 0, "maximum": 100},
                "fit_label": {
                    "type": "string",
                    "enum": FitLabel.values(),
                },
                "recommended": {"type": "boolean"},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "summary": {"type": "string"},
                "fit_reasons": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "salary": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "salary_mentioned": {"type": "boolean"},
                        "min": {"type": ["number", "null"]},
                        "max": {"type": ["number", "null"]},
                        "currency": {"type": ["string", "null"]},
                        "period": {
                            "type": ["string", "null"],
                            "enum": [*SalaryPeriod.values(), None],
                        },
                        "raw_text": {"type": ["string", "null"]},
                    },
                    "required": [
                        "salary_mentioned",
                        "min",
                        "max",
                        "currency",
                        "period",
                        "raw_text",
                    ],
                },
                "remote_type": {
                    "type": "string",
                    "enum": RemoteType.values(),
                },
                "remote_scope": {
                    "type": "string",
                    "enum": RemoteScope.values(),
                },
                "remote_scope_details": {
                    "type": ["string", "null"],
                },
                "visa_sponsorship": {
                    "type": "string",
                    "enum": YesNoUnknown.values(),
                },
                "visa_sponsorship_details": {
                    "type": ["string", "null"],
                },
                "relocation_support": {
                    "type": "string",
                    "enum": YesNoUnknown.values(),
                },
                "relocation_support_details": {
                    "type": ["string", "null"],
                },
                "seniority": {
                    "type": "string",
                    "enum": Seniority.values(),
                },
            },
            "required": [
                "raw_job_ad_id",
                "fit_score",
                "fit_label",
                "recommended",
                "confidence",
                "summary",
                "fit_reasons",
                "salary",
                "remote_type",
                "remote_scope",
                "remote_scope_details",
                "visa_sponsorship",
                "visa_sponsorship_details",
                "relocation_support",
                "relocation_support_details",
                "seniority",
            ],
        },
    }
