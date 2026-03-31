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
                    "enum": ["strong_fit", "medium_fit", "weak_fit", "not_fit"],
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
                            "enum": ["hour", "day", "month", "year", "unknown", None],
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
                    "enum": ["remote", "hybrid", "on_site", "unknown"],
                },
                "seniority": {
                    "type": "string",
                    "enum": [
                        "junior",
                        "mid",
                        "senior",
                        "lead",
                        "staff",
                        "principal",
                        "unknown",
                    ],
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
                "seniority",
            ],
        },
    }