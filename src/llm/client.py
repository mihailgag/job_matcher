import json
from typing import Any

from openai import OpenAI

from src.llm.models import LLMParsedResult, LLMResponseEnvelope, SalaryExtraction


class OpenAIClient:
    def __init__(self, api_key: str | None = None) -> None:
        self.client: OpenAI = OpenAI(api_key=api_key)

    def create_job_match_response(
        self,
        model_name: str,
        system_message: str,
        user_message: str,
        schema: dict[str, Any],
        temperature: float,
        max_output_tokens: int,
    ) -> LLMResponseEnvelope:
        response = self.client.responses.create(
            model=model_name,
            input=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": schema["name"],
                    "schema": schema["schema"],
                    "strict": True,
                }
            },
            max_output_tokens=max_output_tokens,
            temperature=temperature,
        )

        parsed_json = json.loads(response.output_text)

        usage = getattr(response, "usage", None)
        input_tokens = getattr(usage, "input_tokens", 0) if usage else 0
        output_tokens = getattr(usage, "output_tokens", 0) if usage else 0
        total_tokens = getattr(usage, "total_tokens", 0) if usage else 0

        cached_input_tokens = 0
        if usage and getattr(usage, "input_tokens_details", None):
            cached_input_tokens = getattr(
                usage.input_tokens_details,
                "cached_tokens",
                0,
            )

        parsed_result = LLMParsedResult(
            raw_job_ad_id=parsed_json["raw_job_ad_id"],
            fit_score=parsed_json["fit_score"],
            fit_label=parsed_json["fit_label"],
            recommended=parsed_json["recommended"],
            confidence=parsed_json["confidence"],
            summary=parsed_json["summary"],
            fit_reasons=parsed_json["fit_reasons"],
            salary=SalaryExtraction(
                salary_mentioned=parsed_json["salary"]["salary_mentioned"],
                min=parsed_json["salary"]["min"],
                max=parsed_json["salary"]["max"],
                currency=parsed_json["salary"]["currency"],
                period=parsed_json["salary"]["period"],
                raw_text=parsed_json["salary"]["raw_text"],
            ),
            remote_type=parsed_json["remote_type"],
            remote_scope=parsed_json["remote_scope"],
            remote_scope_details=parsed_json["remote_scope_details"],
            visa_sponsorship=parsed_json["visa_sponsorship"],
            visa_sponsorship_details=parsed_json["visa_sponsorship_details"],
            relocation_support=parsed_json["relocation_support"],
            relocation_support_details=parsed_json["relocation_support_details"],
            seniority=parsed_json["seniority"],
        )

        return LLMResponseEnvelope(
            parsed_result=parsed_result,
            provider_request_id=getattr(response, "id", None),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cached_input_tokens=cached_input_tokens,
            raw_response_json=response.model_dump() if hasattr(response, "model_dump") else None,
        )